import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_env(monkeypatch):
    """Credenciais fictícias do banco (variáveis de ambiente têm precedência sobre o .env)."""
    for name, value in {
        "DB_HOST": "db.test",
        "DB_PORT": "54329",
        "DB_USER": "tester",
        "DB_NAME": "testdb",
        "DB_PASSWORD": "secret",
    }.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def zip_shapefile(tmp_path):
    """Grava um GeoDataFrame como shapefile compactado em .zip, como os arquivos do INCRA/SICAR."""
    def _make(gdf, name="dados"):
        shp_dir = tmp_path / f"{name}_shp"
        shp_dir.mkdir()
        gdf.to_file(shp_dir / f"{name}.shp", driver="ESRI Shapefile", encoding="utf-8")

        zip_path = tmp_path / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for file in shp_dir.iterdir():
                zf.write(file, file.name)
        return str(zip_path)

    return _make
