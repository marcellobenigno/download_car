import os

from SICAR import Sicar, Polygon


def create_directories(base_path):
    """
    Cria os diretórios 'sql' e 'shapefile' dentro do base_path, se não existirem.

    :param base_path: Caminho base onde os diretórios serão criados.
    """
    sql_dir = os.path.join(base_path, "sql")
    shapefile_dir = os.path.join(base_path, "shapefile")

    for directory in [sql_dir, shapefile_dir]:
        os.makedirs(directory, exist_ok=True)

    return sql_dir, shapefile_dir


def download_car(state):
    result = None
    car = Sicar()
    try:
        file = car.download_state(state, Polygon.AREA_PROPERTY)
        print(f'Download executado com sucesso para: {state}')
        result = file
    except Exception as e:
        print(f'Erro no download do arquivo {e}')

    return result
