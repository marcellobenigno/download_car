import os
from datetime import datetime

from SICAR import Sicar, Polygon


def create_directories(base_path):
    sql_dir = os.path.join(base_path, "sql")
    shapefile_dir = os.path.join(base_path, "shapefile")
    zip_dir = os.path.join(base_path, "zip")

    for directory in [sql_dir, shapefile_dir, zip_dir]:
        os.makedirs(directory, exist_ok=True)

    return sql_dir, shapefile_dir, zip_dir


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
