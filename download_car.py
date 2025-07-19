import os
import zipfile
from datetime import datetime

from SICAR import Sicar, Polygon

from export_sql import export_sql
from load_sql_data import load_sql_data
from process_car import process_shapefile


def create_directories(base_path):
    sql_dir = os.path.join(base_path, "sql")
    shapefile_dir = os.path.join(base_path, "shapefile")
    temp_dir = os.path.join(base_path, "temp")

    for directory in [sql_dir, shapefile_dir, temp_dir]:
        os.makedirs(directory, exist_ok=True)

    return sql_dir, shapefile_dir, temp_dir


def get_dated_filename(state, temp_path):
    today = datetime.today().strftime("%d%m%Y")
    filename = f"{state}_AREA_IMOVEL_{today}.zip"
    return os.path.join(temp_path, filename)


def download_car(state, dated_zip_path):
    if os.path.exists(dated_zip_path):
        print(f"✅ Arquivo já existe: {dated_zip_path}")
        return dated_zip_path

    car = Sicar()
    try:
        downloaded_file = car.download_state(state, Polygon.AREA_PROPERTY)
        os.rename(downloaded_file, dated_zip_path)
        print(f"⬇️ Download executado e renomeado para: {dated_zip_path}")
        return dated_zip_path
    except Exception as e:
        print(f"❌ Erro no download do arquivo: {e}")
        return None


if __name__ == '__main__':
    # Solicita múltiplos estados separados por vírgula
    states_input = input("Digite a sigla dos estados separados por vírgula (ex: AC, SP, MG): ")

    # Limpa e separa as siglas em uma lista
    states = [s.strip().upper() for s in states_input.split(",") if s.strip()]

    # Solicita o código do município (opcional, único para todos os estados)
    municipality_code_input = input("Digite o código do município (opcional, ex: 1200708): ")
    if not municipality_code_input:
        municipality_code_input = None

    # Define o caminho base para salvar os arquivos
    base_path = os.path.join(os.getcwd(), "data")

    # Cria os diretórios necessários
    sql_path, shapefile_path, temp_path = create_directories(base_path)

    for state_input in states:
        print(f"\n>>> Processando estado: {state_input}")

        dated_zip_path = get_dated_filename(state_input, temp_path)
        downloaded_file = download_car(state_input, dated_zip_path)

        if downloaded_file:
            print(f"Arquivo baixado e salvo em: {downloaded_file}")

            unzip_path = os.path.join(temp_path, state_input)
            with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
                zip_ref.extractall(unzip_path)
            print(f"Arquivo descompactado em: {unzip_path}")

            shp_file = None
            for root, dirs, files in os.walk(unzip_path):
                for file in files:
                    if file.endswith(".shp"):
                        shp_file = os.path.join(root, file)
                        break
                if shp_file:
                    break

            if shp_file:
                output_shapefile = os.path.join(shapefile_path, f"{state_input}.shp")
                process_shapefile(shp_file, output_shapefile, municipality_code=municipality_code_input)
                output_sql = os.path.join(sql_path, f"{state_input}.sql")
                export_sql(output_shapefile, output_sql)
                load_sql_data(state_input)  # assume função aceita só a sigla
            else:
                print(f"❌ Nenhum arquivo .shp encontrado em {unzip_path}")
        else:
            print(f"Não foi possível baixar o arquivo para o estado {state_input}.")
