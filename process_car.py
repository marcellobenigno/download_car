import re

import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon


# Funções de extração de códigos
def extract_cod_ibge_m(cod_imovel):
    """Extrai o código IBGE do município do código do imóvel."""
    match = re.search(r"-(\d{7})-", cod_imovel)
    return match.group(1) if match else None


def extract_cod_ibge_e(cod_ibge_m):
    """Extrai o código IBGE do estado do código IBGE do município."""
    return cod_ibge_m[:2] if cod_ibge_m else None


# Funções de limpeza e correção de geometria
def clean_geometry(geom):
    """Limpa e simplifica a geometria."""
    if geom.is_empty or not geom.is_valid:
        return None  # Remove geometrias inválidas
    return geom.simplify(0.00001)  # Suaviza a geometria


def ensure_polygon(geom):
    """Garante que a geometria seja um polígono ou multipolígono."""
    if geom.geom_type == "LineString":
        return Polygon(geom)  # Converte LineString para Polygon
    elif geom.geom_type == "MultiLineString":
        return MultiPolygon([Polygon(line) for line in geom.geoms])  # MultiLineString -> MultiPolygon
    return geom  # Mantém Polygon e MultiPolygon inalterados


# Mapeamento de nomes de colunas
COLUMN_RENAME = {
    "cod_imovel": "cod_imovel",
    "num_area": "num_area",
    "cod_estado": "cod_estado",
    "municipio": "nom_munici",
    "mod_fiscal": "num_modulo",
    "ind_tipo": "tipo_imove",
    "ind_status": "situacao",
    "des_condic": "condicao_i",
    "geometry": "geom"
}


def process_shapefile(zip_file, output_file, output_crs=4326):
    """Processa um shapefile, realizando limpeza, correção e conversão de dados."""
    try:
        # Carrega o arquivo shapefile e define o CRS
        print(f"🔄 Lendo o arquivo: {zip_file}")
        car = gpd.read_file(f"zip://{zip_file}")
        car = car.to_crs(output_crs)

        # Seleciona e renomeia as colunas
        valid_columns = [col for col in COLUMN_RENAME.keys() if col in car.columns]
        car = car[valid_columns].rename(columns=COLUMN_RENAME)

        # Extrai códigos IBGE
        car["cod_ibge_m"] = car["cod_imovel"].apply(extract_cod_ibge_m)
        car["cod_ibge_e"] = car["cod_ibge_m"].apply(extract_cod_ibge_e)

        # Limpeza e correção de geometrias
        car["geom"] = car["geom"].apply(clean_geometry)
        car["geom"] = car["geom"].apply(ensure_polygon)

        # Remove duplicatas
        car = car.drop_duplicates(subset=["cod_imovel"], keep="first")

        # Salva o arquivo modificado
        print(f"💾 Salvando Shapefile em: {output_file}")
        car.to_file(output_file, driver="ESRI Shapefile")

    except Exception as e:
        print(f"❌ Erro ao processar o shapefile: {e}")
