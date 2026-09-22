"""
Teste de integração com um PostgreSQL/PostGIS real: exporta um shapefile com shp2pgsql e carrega com psql,
verificando a transação única, datas e timestamps. Cria e remove um banco temporário.

Opcional: só roda com TEST_POSTGIS=1 e as credenciais DB_HOST/DB_USER/DB_PASSWORD (ou .env) de um usuário
que possa criar bancos. Ex: TEST_POSTGIS=1 pytest tests/test_integration_postgis.py
"""
import os
import shutil
import subprocess
import uuid

import geopandas as gpd
import pandas as pd
import pytest
from decouple import config
from shapely.geometry import box

pytestmark = pytest.mark.skipif(
    os.environ.get("TEST_POSTGIS") != "1" or not (shutil.which("psql") and shutil.which("shp2pgsql")),
    reason="defina TEST_POSTGIS=1 e tenha psql/shp2pgsql no PATH para rodar a integração com PostGIS",
)

SNCI_DDL = """
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE TABLE maps_incrasnci (
        id bigserial PRIMARY KEY,
        num_proces varchar(70), sr varchar(10), num_certif varchar(20), data_certi date,
        qtd_area_p varchar(50), cod_profis varchar(30), cod_imovel varchar(30),
        nome_imove varchar(255), uf_municip varchar(2), municipio integer,
        geom geometry(MultiPolygon, 4326), criado timestamptz, modificado timestamptz
    );
    INSERT INTO maps_incrasnci (num_proces, municipio, geom, criado, modificado) VALUES
        ('antigo-1', 2500001, ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326)), now() - interval '1 year', now()),
        ('antigo-2', 2500001, ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326)), now() - interval '1 year', now()),
        ('outro-municipio', 2500002, ST_Multi(ST_MakeEnvelope(1, 0, 2, 1, 4326)), now() - interval '1 year', now());
"""


def psql(dbname, sql):
    env = {**os.environ, "PGPASSWORD": config("DB_PASSWORD")}
    command = ["psql", "-h", config("DB_HOST"), "-p", config("DB_PORT", default="5432"), "-U", config("DB_USER"), "-d", dbname,
               "-At", "-v", "ON_ERROR_STOP=1", "-c", sql]
    return subprocess.run(command, check=True, env=env, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def test_db(monkeypatch):
    dbname = f"download_car_pytest_{uuid.uuid4().hex[:8]}"
    psql("postgres", f"CREATE DATABASE {dbname}")
    try:
        psql(dbname, SNCI_DDL)
        monkeypatch.setenv("DB_NAME", dbname)
        yield dbname
    finally:
        psql("postgres", f"DROP DATABASE IF EXISTS {dbname}")


@pytest.fixture
def snci_sql(tmp_path):
    from export_sql import export_sql
    from process_incra import save_shapefile

    gdf = gpd.GeoDataFrame({
        "num_proces": ["novo-1", "novo-2", "novo-3"],
        "nome_imove": ["FAZENDA BABILÔNIA", "SÍTIO SUAÉZINHO", None],
        "data_certi": [pd.Timestamp("2026-02-06"), pd.Timestamp("2012-08-02"), pd.NaT],
        "municipio": [2500001, 2500001, 2500001],
    }, geometry=[box(0, 0, 0.5, 0.5), box(0.5, 0.5, 1, 1), box(0.2, 0.2, 0.3, 0.3)], crs=4326)
    save_shapefile(gdf, str(tmp_path / "SNCI_PB.shp"))

    sql_path = tmp_path / "SNCI_PB.sql"
    assert export_sql(str(tmp_path / "SNCI_PB.shp"), str(sql_path), table="maps_incrasnci")
    return sql_path


def test_replaces_only_given_municipality(test_db, snci_sql):
    from load_sql_data import load_sql_data

    assert load_sql_data("PB", str(snci_sql), ["2500001"], table="maps_incrasnci", column="municipio",
                         timestamps=True)

    rows = psql(test_db, "SELECT num_proces, municipio, data_certi, nome_imove, criado IS NOT NULL, "
                         "criado > now() - interval '1 hour', GeometryType(geom) "
                         "FROM maps_incrasnci ORDER BY num_proces")
    assert rows.splitlines() == [
        "novo-1|2500001|2026-02-06|FAZENDA BABILÔNIA|t|t|MULTIPOLYGON",
        "novo-2|2500001|2012-08-02|SÍTIO SUAÉZINHO|t|t|MULTIPOLYGON",
        "novo-3|2500001|||t|t|MULTIPOLYGON",
        # o outro município não é apagado nem tem o criado alterado
        "outro-municipio|2500002|||t|f|MULTIPOLYGON",
    ]


def test_failure_rolls_back_the_delete(test_db, tmp_path):
    from load_sql_data import load_sql_data

    bad_sql = tmp_path / "ruim.sql"
    bad_sql.write_text("INSERT INTO maps_incrasnci (municipio) VALUES ('nao-e-numero');\n")

    assert not load_sql_data("PB", str(bad_sql), ["2500001"], table="maps_incrasnci", column="municipio",
                             timestamps=True)
    assert psql(test_db, "SELECT count(*) FROM maps_incrasnci WHERE municipio = 2500001") == "2"
