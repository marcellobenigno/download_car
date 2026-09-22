import os
import re
import subprocess
from collections import defaultdict

import geopandas as gpd
from decouple import config
from shapely import wkb

IBGE_CODE_RE = re.compile(r"^\d{7}$")
TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

ACTIVE_MUNICIPALITIES_QUERY = """
    SELECT m.sigla_uf, m.cod_ibge_m
    FROM maps_municipio m
    INNER JOIN prefeitura_prefeitura p ON p.municipio_id = m.id
    WHERE p.ativo = TRUE
    ORDER BY m.sigla_uf, m.cod_ibge_m
"""

ACTIVE_MUNICIPALITY_GEOMETRIES_QUERY = """
    SELECT m.sigla_uf, m.cod_ibge_m, ST_AsHEXEWKB(ST_Transform(g.geom, 4326))
    FROM maps_municipio m
    INNER JOIN prefeitura_prefeitura p ON p.municipio_id = m.id
    INNER JOIN maps_geometriamunicipio g ON g.municipio_id = m.id
    WHERE p.ativo = TRUE
    ORDER BY m.sigla_uf, m.cod_ibge_m
"""


def run_query(sql):
    """Executa uma consulta via psql e retorna a saída no formato 'col1|col2|...', ou None em caso de erro."""
    env = os.environ.copy()
    env['PGPASSWORD'] = config("DB_PASSWORD")

    command = [
        "psql",
        "-h", config("DB_HOST"),
        "-p", config("DB_PORT", default="5432"),
        "-U", config("DB_USER"),
        "-d", config("DB_NAME"),
        "-At",  # saída sem cabeçalho/alinhamento: 'col1|col2|...'
        "-v", "ON_ERROR_STOP=1",
        "-c", sql,
    ]

    try:
        result = subprocess.run(command, check=True, env=env, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar consulta no banco: {e.stderr.strip()}")
        return None
    except FileNotFoundError:
        print("❌ Erro: O comando 'psql' não foi encontrado. Certifique-se de que o PostgreSQL está instalado e no seu PATH.")
        return None
    return result.stdout


def parse_municipality_rows(output):
    """Converte a saída do psql (linhas 'UF|cod_ibge_m') em {UF: [cod_ibge_m, ...]}."""
    municipios = defaultdict(list)
    for line in output.splitlines():
        if not line.strip():
            continue
        uf, cod_ibge_m = (value.strip() for value in line.split("|", 1))
        if not uf or not IBGE_CODE_RE.match(cod_ibge_m):
            print(f"⚠️ Município ignorado (UF/código IBGE inválido): {line}")
            continue
        municipios[uf.upper()].append(cod_ibge_m)
    return dict(municipios)


def get_active_municipalities():
    """Retorna os municípios com prefeitura ativa agrupados por UF, ou None em caso de erro."""
    output = run_query(ACTIVE_MUNICIPALITIES_QUERY)
    if output is None:
        print("❌ Não foi possível consultar os municípios com prefeitura ativa.")
        return None
    return parse_municipality_rows(output)


def get_active_municipality_geometries():
    """
    Retorna um GeoDataFrame (EPSG:4326) com sigla_uf, cod_ibge_m e a geometria dos municípios
    com prefeitura ativa, ou None em caso de erro. Municípios sem geometria cadastrada não aparecem.
    """
    output = run_query(ACTIVE_MUNICIPALITY_GEOMETRIES_QUERY)
    if output is None:
        print("❌ Não foi possível consultar as geometrias dos municípios com prefeitura ativa.")
        return None

    rows = []
    for line in output.splitlines():
        if not line.strip():
            continue
        uf, cod_ibge_m, geom_hex = line.split("|", 2)
        if not IBGE_CODE_RE.match(cod_ibge_m.strip()):
            print(f"⚠️ Município ignorado (código IBGE inválido): {cod_ibge_m}")
            continue
        rows.append({
            "sigla_uf": uf.strip().upper(),
            "cod_ibge_m": cod_ibge_m.strip(),
            "geometry": wkb.loads(geom_hex.strip(), hex=True),
        })
    return gpd.GeoDataFrame(rows, columns=["sigla_uf", "cod_ibge_m", "geometry"], geometry="geometry", crs=4326)


def count_records_by_municipality(table, column, municipios):
    """Retorna {cod_ibge_m: quantidade de registros} na tabela de destino, ou None em caso de erro."""
    if not TABLE_NAME_RE.match(table) or not TABLE_NAME_RE.match(column):
        raise ValueError(f"Nome de tabela/coluna inválido: {table}.{column}")
    invalid = [cod for cod in municipios if not IBGE_CODE_RE.match(str(cod))]
    if invalid:
        raise ValueError(f"Código(s) IBGE de município inválido(s): {', '.join(map(str, invalid))}")

    codes = ", ".join(f"'{cod}'" for cod in municipios)
    output = run_query(f"SELECT {column}, count(*) FROM {table} WHERE {column} IN ({codes}) GROUP BY {column}")
    if output is None:
        return None

    counts = {str(cod): 0 for cod in municipios}
    for line in output.splitlines():
        if line.strip():
            cod, total = line.split("|", 1)
            counts[cod.strip()] = int(total)
    return counts
