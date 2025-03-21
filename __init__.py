import os

from SICAR import Sicar

from download_car import download_car, create_directories
from export_sql import export_sql
from load_sql_data import load_sql_data
from process_car import process_shapefile


def main():
    """
    Fluxo principal do script:
    - Cria diretórios necessários.
    - Obtém as datas de liberação do SICAR.
    - Faz o download, processamento e exportação de arquivos.
    """
    state_code = None
    base_path = os.getcwd()
    sql_dir, shapefile_dir = create_directories(base_path)

    car = Sicar()
    state_dates = car.get_release_dates()

    for key, val in state_dates.items():
        try:
            state_code = key.split('.')[-1]  # Obtém o código do estado
            shapefile_output = os.path.join(shapefile_dir, f"{state_code}.shp")
            sql_output = os.path.join(sql_dir, f"{state_code}.sql")

            print(f"📥 Baixando dados para: ({state_code})")
            zip_file = download_car(key)

            print(f"🛠 Processando shapefile para: {state_code}")
            process_shapefile(zip_file, shapefile_output)

            print(f"📤 Exportando para SQL: {state_code}")
            export_sql(shapefile_output, sql_output)

            print(f"✅ Processamento concluído com sucesso para {state_code}!\n")

            print(f"🛠 Inserindo no banco os dados do estado: {state_code}")
            load_sql_data(state_code)

        except Exception as e:
            print(f"❌ Erro ao processar {val} ({state_code}): {e}")


if __name__ == "__main__":
    main()
