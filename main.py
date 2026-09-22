import os
import sys  # Importa o módulo sys para acessar argumentos da linha de comando
import zipfile

from download_car import download_car, create_directories, get_dated_filename
from export_sql import export_sql
from load_sql_data import load_sql_data
from process_car import process_shapefile


def safe_extract(zip_ref, target_dir):
    """Extrai um ZipFile validando que nenhuma entrada escapa de target_dir (zip slip)."""
    target_dir = os.path.realpath(target_dir)
    for member in zip_ref.namelist():
        member_path = os.path.realpath(os.path.join(target_dir, member))
        if member_path != target_dir and not member_path.startswith(target_dir + os.sep):
            raise ValueError(f"Entrada de zip inválida (path traversal): {member}")
    zip_ref.extractall(target_dir)


def main():
    if len(sys.argv) > 1:
        states_input = sys.argv[1]  # Pega o primeiro argumento como a string de estados
        print(f"Estados recebidos via linha de comando: {states_input}")
    else:
        # Se nenhum argumento for fornecido, solicita o input interativamente
        states_input = input("Digite a sigla dos estados separados por vírgula (ex: AC, SP, MG): ")

    states = [s.strip().upper() for s in states_input.split(",") if s.strip()]

    base_path = os.path.join(os.getcwd(), "temp")
    sql_path, shapefile_path, zip_path = create_directories(base_path)

    unzip_root = os.path.join(base_path, "unzipped")
    os.makedirs(unzip_root, exist_ok=True)

    for state_input in states:
        print(f"\n>>> Processando estado: {state_input}")

        dated_zip_path = get_dated_filename(state_input, zip_path)
        downloaded_file = download_car(state_input, dated_zip_path)

        if not downloaded_file:
            print(f"Não foi possível baixar o arquivo para o estado {state_input}.")
            continue

        print(f"Arquivo baixado e salvo em: {downloaded_file}")

        unzip_path = os.path.join(unzip_root, state_input)
        os.makedirs(unzip_path, exist_ok=True)

        try:
            with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                safe_extract(zip_ref, unzip_path)
        except (zipfile.BadZipFile, ValueError) as e:
            print(f"❌ Erro ao descompactar o arquivo para {state_input}: {e}")
            continue
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
            continue

        output_shapefile = os.path.join(shapefile_path, f"{state_input}.shp")
        output_sql = os.path.join(sql_path, f"{state_input}.sql")

        if not process_shapefile(shp_file, output_shapefile):
            print(f"❌ Processamento do shapefile falhou para {state_input}, pulando exportação/carregamento.")
            continue

        if not export_sql(output_shapefile, output_sql):
            print(f"❌ Exportação para SQL falhou para {state_input}, pulando carregamento no banco.")
            continue

        if not load_sql_data(state_input, output_sql):
            print(f"❌ Carregamento no banco de dados falhou para {state_input}.")
            continue


if __name__ == "__main__":
    main()
