import os
import sys  # Importa o módulo sys para acessar argumentos da linha de comando
import zipfile

from download_car import download_car, create_directories, get_dated_filename
from export_sql import export_sql
from load_sql_data import load_sql_data
from process_car import process_shapefile


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

        if downloaded_file:
            print(f"Arquivo baixado e salvo em: {downloaded_file}")

            unzip_path = os.path.join(unzip_root, state_input)
            os.makedirs(unzip_path, exist_ok=True)

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
                output_sql = os.path.join(sql_path, f"{state_input}.sql")

                process_shapefile(shp_file, output_shapefile)
                export_sql(output_shapefile, output_sql)
                load_sql_data(state_input, output_sql)
            else:
                print(f"❌ Nenhum arquivo .shp encontrado em {unzip_path}")
        else:
            print(f"Não foi possível baixar o arquivo para o estado {state_input}.")


if __name__ == "__main__":
    main()
