import os
import time
import zipfile

from SICAR import Sicar, Polygon


def create_directories(base_path):
    sql_dir = os.path.join(base_path, "sql")
    shapefile_dir = os.path.join(base_path, "shapefile")
    zip_dir = os.path.join(base_path, "zip")

    for directory in [sql_dir, shapefile_dir, zip_dir]:
        os.makedirs(directory, exist_ok=True)

    return sql_dir, shapefile_dir, zip_dir


# Os arquivos de UF inteira são reaproveitados por alguns dias em vez de baixados a cada execução.
CACHE_VALIDADE_SEGUNDOS = 2 * 24 * 60 * 60


def get_car_zip_path(state, temp_path):
    return os.path.join(temp_path, f"{state}_AREA_IMOVEL.zip")


def download_car(state, zip_path):
    if os.path.exists(zip_path):
        idade = time.time() - os.path.getmtime(zip_path)
        if idade <= CACHE_VALIDADE_SEGUNDOS and zipfile.is_zipfile(zip_path):
            print(f"✅ Arquivo já existe: {zip_path} (baixado há {int(idade // 3600)}h, validade de 2 dias)")
            return zip_path
        print(f"⚠️ Arquivo em cache desatualizado ou corrompido, baixando novamente: {zip_path}")
        os.remove(zip_path)

    car = Sicar()
    try:
        downloaded_file = car.download_state(state, Polygon.AREA_PROPERTY)
        if not zipfile.is_zipfile(downloaded_file):
            print(f"❌ Download corrompido para o estado {state}")
            os.remove(downloaded_file)
            return None
        os.replace(downloaded_file, zip_path)
        print(f"⬇️ Download executado e renomeado para: {zip_path}")
        return zip_path
    except Exception as e:
        print(f"❌ Erro no download do arquivo: {e}")
        return None
