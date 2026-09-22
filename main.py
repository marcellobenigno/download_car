import argparse
import os
import sys
import zipfile

from decouple import config

from download_car import download_car, create_directories, get_car_zip_path
from download_incra import download_incra
from export_sql import export_sql
from load_sql_data import load_sql_data
from municipios import (
    count_records_by_municipality,
    get_active_municipalities,
    get_active_municipality_geometries,
)
from process_car import read_car_shapefile, save_shapefile as save_car_shapefile
from process_incra import process_incra_shapefile, save_shapefile as save_incra_shapefile

FONTES = ["car", "sigef", "snci"]

CAR_TABLE = config("DB_TABLE", default="maps_car")

INCRA_TABLES = {
    "sigef": config("DB_TABLE_SIGEF", default="maps_incrasigef"),
    "snci": config("DB_TABLE_SNCI", default="maps_incrasnci"),
}


def safe_extract(zip_ref, target_dir):
    """Extrai um ZipFile validando que nenhuma entrada escapa de target_dir (zip slip)."""
    target_dir = os.path.realpath(target_dir)
    for member in zip_ref.namelist():
        member_path = os.path.realpath(os.path.join(target_dir, member))
        if member_path != target_dir and not member_path.startswith(target_dir + os.sep):
            raise ValueError(f"Entrada de zip inválida (path traversal): {member}")
    zip_ref.extractall(target_dir)


def select_outdated(gdf, municipios, table, column):
    """
    Compara, por município, a quantidade de registros baixados com a quantidade já existente na base.
    Retorna (gdf apenas com os municípios a atualizar, lista desses municípios), ou None em caso de erro.
    Municípios com a mesma quantidade na fonte e na base são considerados atualizados.
    """
    counts_db = count_records_by_municipality(table, column, municipios)
    if counts_db is None:
        print(f"❌ Não foi possível contar os registros atuais de {table}.")
        return None
    counts_source = gdf[column].astype(str).value_counts().to_dict()

    to_update = []
    for cod in municipios:
        source, current = counts_source.get(cod, 0), counts_db[cod]
        if source == current:
            print(f"   {cod}: {current} imóvel(is), mesma quantidade da fonte. Nenhuma atualização necessária.")
        else:
            print(f"   {cod}: {current} imóvel(is) na base, {source} na fonte. Será atualizado.")
            to_update.append(cod)

    return gdf[gdf[column].astype(str).isin(to_update)].copy(), to_update


def update_car(state, municipios, dirs):
    sql_path, shapefile_path, zip_path, unzip_root = dirs

    downloaded_file = download_car(state, get_car_zip_path(state, zip_path))
    if not downloaded_file:
        print(f"Não foi possível baixar o arquivo para o estado {state}.")
        return

    print(f"Arquivo baixado e salvo em: {downloaded_file}")

    unzip_path = os.path.join(unzip_root, state)
    os.makedirs(unzip_path, exist_ok=True)

    try:
        with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
            safe_extract(zip_ref, unzip_path)
    except (zipfile.BadZipFile, ValueError) as e:
        print(f"❌ Erro ao descompactar o arquivo para {state}: {e}")
        return
    print(f"Arquivo descompactado em: {unzip_path}")

    shp_file = None
    for root, dirs, files in os.walk(unzip_path):
        for file in files:
            if file.endswith(".shp"):
                shp_file = os.path.join(root, file)
                break
        if shp_file:
            break

    if not shp_file:
        print(f"❌ Nenhum arquivo .shp encontrado em {unzip_path}")
        return

    car = read_car_shapefile(shp_file, municipios=municipios)
    if car is None:
        print(f"❌ Processamento do shapefile falhou para {state}, pulando exportação/carregamento.")
        return

    selected = select_outdated(car, municipios, CAR_TABLE, "cod_ibge_m")
    if selected is None:
        return
    car, to_update = selected
    if not to_update:
        print(f"✅ CAR de {state} já está atualizado.")
        return

    output_sql = None
    if not car.empty:
        output_shapefile = os.path.join(shapefile_path, f"{state}.shp")
        output_sql = os.path.join(sql_path, f"{state}.sql")
        try:
            save_car_shapefile(car, output_shapefile)
        except Exception as e:
            print(f"❌ Erro ao salvar o shapefile de {state}: {e}")
            return
        if not export_sql(output_shapefile, output_sql, table=CAR_TABLE):
            print(f"❌ Exportação para SQL falhou para {state}, pulando carregamento no banco.")
            return

    if not load_sql_data(state, output_sql, to_update, table=CAR_TABLE, column="cod_ibge_m"):
        print(f"❌ Carregamento no banco de dados falhou para {state}.")


def update_incra(fonte, state, municipios_gdf, dirs):
    """
    Atualiza SIGEF ou SNCI dos municípios informados. O INCRA só publica o shapefile da UF inteira:
    ele é baixado uma vez e cada imóvel é atribuído aos municípios cuja geometria ele intersecta.
    Municípios cuja quantidade de imóveis na base já é igual à da fonte são considerados atualizados.
    """
    sql_path, shapefile_path, zip_path, _ = dirs
    table = INCRA_TABLES[fonte]
    municipios = list(municipios_gdf["cod_ibge_m"])

    downloaded_file = download_incra(fonte, state, zip_path)
    if not downloaded_file:
        print(f"Não foi possível baixar o {fonte.upper()} para o estado {state}.")
        return

    gdf = process_incra_shapefile(downloaded_file, fonte, municipios_gdf)
    if gdf is None:
        print(f"❌ Processamento do shapefile falhou para {state}, pulando exportação/carregamento.")
        return

    selected = select_outdated(gdf, municipios, table, "municipio")
    if selected is None:
        return
    gdf, to_update = selected
    if not to_update:
        print(f"✅ {fonte.upper()} de {state} já está atualizado.")
        return

    gdf["municipio"] = gdf["municipio"].astype(int)

    output_sql = None
    if not gdf.empty:
        output_shapefile = os.path.join(shapefile_path, f"{fonte.upper()}_{state}.shp")
        output_sql = os.path.join(sql_path, f"{fonte.upper()}_{state}.sql")
        try:
            save_incra_shapefile(gdf, output_shapefile)
        except Exception as e:
            print(f"❌ Erro ao salvar o shapefile de {state}: {e}")
            return
        if not export_sql(output_shapefile, output_sql, table=table):
            print(f"❌ Exportação para SQL falhou para {state}, pulando carregamento no banco.")
            return

    if not load_sql_data(state, output_sql, to_update, table=table, column="municipio", timestamps=True):
        print(f"❌ Carregamento no banco de dados falhou para {state}.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Atualiza CAR, SIGEF e SNCI dos municípios com prefeitura ativa."
    )
    parser.add_argument(
        "estados", nargs="?", default=None,
        help="Siglas dos estados separadas por vírgula (ex: MT,SP). Padrão: todos com prefeitura ativa.",
    )
    parser.add_argument(
        "--fonte", nargs="+", default=["car"],
        help="Bases a atualizar: car, sigef, snci (padrão: car). Ex: --fonte car,sigef,snci ou --fonte car sigef snci",
    )
    args = parser.parse_args()

    # Aceita as bases separadas por espaço e/ou vírgula, como os estados
    args.fonte = [f.strip().lower() for value in args.fonte for f in value.split(",") if f.strip()]
    invalid = [f for f in args.fonte if f not in FONTES]
    if invalid or not args.fonte:
        parser.error(f"fonte(s) inválida(s): {', '.join(invalid) or '(vazio)'} (use: {', '.join(FONTES)})")
    return args


def main():
    args = parse_args()

    # Lista inicial: municípios com prefeitura ativa, agrupados por UF
    municipios_por_uf = get_active_municipalities()
    if municipios_por_uf is None:
        sys.exit(1)
    if not municipios_por_uf:
        print("Nenhum município com prefeitura ativa encontrado.")
        return

    total = sum(len(codes) for codes in municipios_por_uf.values())
    print(f"{total} município(s) com prefeitura ativa em {len(municipios_por_uf)} estado(s): "
          f"{', '.join(municipios_por_uf)}")

    states = list(municipios_por_uf)
    if args.estados:
        # Argumento opcional restringe a atualização a alguns estados
        requested = [s.strip().upper() for s in args.estados.split(",") if s.strip()]
        print(f"Estados recebidos via linha de comando: {', '.join(requested)}")
        for state in requested:
            if state not in municipios_por_uf:
                print(f"⚠️ {state} não possui municípios com prefeitura ativa, ignorando.")
        states = [s for s in requested if s in municipios_por_uf]

    fontes = [f for f in FONTES if f in args.fonte]

    geometrias = None
    if any(f in INCRA_TABLES for f in fontes):
        # SIGEF/SNCI são filtrados por interseção com a geometria do município
        geometrias = get_active_municipality_geometries()
        if geometrias is None:
            sys.exit(1)
        sem_geometria = sorted(
            cod for state in states for cod in municipios_por_uf[state]
            if cod not in set(geometrias["cod_ibge_m"])
        )
        if sem_geometria:
            print(f"⚠️ Município(s) sem geometria cadastrada, ignorados no SIGEF/SNCI: {', '.join(sem_geometria)}")

    base_path = os.path.join(os.getcwd(), "temp")
    sql_path, shapefile_path, zip_path = create_directories(base_path)

    unzip_root = os.path.join(base_path, "unzipped")
    os.makedirs(unzip_root, exist_ok=True)
    dirs = (sql_path, shapefile_path, zip_path, unzip_root)

    for fonte in fontes:
        for state in states:
            municipios = municipios_por_uf[state]
            print(f"\n>>> {fonte.upper()} - estado: {state} ({len(municipios)} município(s) com prefeitura ativa)")

            if fonte == "car":
                update_car(state, municipios, dirs)
                continue

            municipios_gdf = geometrias[geometrias["sigla_uf"] == state]
            if municipios_gdf.empty:
                print(f"⚠️ Nenhum município de {state} possui geometria cadastrada, pulando.")
                continue
            update_incra(fonte, state, municipios_gdf, dirs)


if __name__ == "__main__":
    main()
