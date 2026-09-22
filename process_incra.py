import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import MultiPolygon

# Campos do shapefile do INCRA mantidos na tabela de destino, com o tamanho máximo das colunas texto
# (None = coluna que não é texto). O código do município não vem do shapefile: é atribuído por interseção.
INCRA_FIELDS = {
    "sigef": {
        "parcela_co": 64,
        "rt": 10,
        "art": 100,
        "situacao_i": 25,
        "codigo_imo": 13,
        "data_submi": None,
        "data_aprov": None,
        "status": 32,
        "nome_area": 254,
        "registro_m": 254,
        "registro_d": None,
        "uf_id": None,
    },
    "snci": {
        "num_proces": 70,
        "sr": 10,
        "num_certif": 20,
        "data_certi": None,
        "qtd_area_p": 50,
        "cod_profis": 30,
        "cod_imovel": 30,
        "nome_imove": 255,
        "uf_municip": 2,
    },
}

INCRA_DATE_FIELDS = {"data_submi", "data_aprov", "registro_d", "data_certi"}

# Margem (em graus) do recorte de leitura, para não perder imóveis na borda por diferença SIRGAS 2000 x WGS 84
BBOX_MARGIN = 0.01


def fix_geometry(geom):
    """Converte a geometria para MultiPolygon 2D válido, ou None se não for possível."""
    if geom is None or geom.is_empty:
        return None
    geom = shapely.force_2d(geom)
    if not geom.is_valid:
        # alguns registros do INCRA vêm com geometria topologicamente inválida
        geom = geom.buffer(0)
    if geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    return None


def truncate(value, max_length):
    if pd.isna(value):
        return None
    return str(value).strip()[:max_length] or None


def normalize_fields(gdf, fonte):
    """Mantém apenas os campos da tabela de destino, truncando textos e convertendo datas."""
    fields = INCRA_FIELDS[fonte]
    missing = [field for field in fields if field not in gdf.columns]
    if missing:
        print(f"⚠️ Atenção: colunas ausentes: {', '.join(missing)}")

    data = {}
    for field, max_length in fields.items():
        if field not in gdf.columns:
            continue
        values = gdf[field]
        if field in INCRA_DATE_FIELDS:
            values = pd.to_datetime(values, errors="coerce")  # já vêm como Date no DBF
        elif max_length:
            values = values.map(lambda v: truncate(v, max_length))
        data[field] = values
    return gpd.GeoDataFrame(data, geometry=gdf.geometry, crs=gdf.crs)


def process_incra_shapefile(zip_path, fonte, municipios_gdf):
    """
    Lê o shapefile da UF e mantém apenas os registros cuja geometria intersecta algum dos municípios
    informados. Um imóvel que intersecta mais de um município é gravado uma vez para cada um deles.
    Retorna um GeoDataFrame (EPSG:4326) com a coluna `municipio` (código IBGE), ou None em caso de erro.
    """
    try:
        # Lê apenas o retângulo que envolve os municípios, não a UF inteira
        minx, miny, maxx, maxy = municipios_gdf.total_bounds
        bbox = (minx - BBOX_MARGIN, miny - BBOX_MARGIN, maxx + BBOX_MARGIN, maxy + BBOX_MARGIN)
        print(f"🔄 Lendo o arquivo: {zip_path}")
        gdf = gpd.read_file(zip_path, bbox=bbox)
        print(f"   {len(gdf)} registro(s) na área dos municípios selecionados")

        if gdf.crs is None:
            gdf = gdf.set_crs(4674)  # SIRGAS 2000, padrão dos arquivos do INCRA
        gdf = gdf.to_crs(4326)

        gdf = normalize_fields(gdf, fonte)
        gdf["geometry"] = gdf.geometry.apply(fix_geometry)
        invalid = int(gdf.geometry.isna().sum())
        if invalid:
            print(f"⚠️ {invalid} registro(s) com geometria inválida foram ignorados")
        gdf = gdf[gdf.geometry.notna()]

        joined = gpd.sjoin(gdf, municipios_gdf[["cod_ibge_m", "geometry"]], how="inner", predicate="intersects")
        joined = joined.drop(columns="index_right").rename(columns={"cod_ibge_m": "municipio"})
        print(f"🔎 {len(joined)} registro(s) intersectam os {len(municipios_gdf)} município(s) selecionado(s)")
        return joined.reset_index(drop=True)

    except Exception as e:
        print(f"❌ Erro ao processar o shapefile: {e}")
        return None


def save_shapefile(gdf, output_file):
    print(f"💾 Salvando Shapefile em: {output_file}")
    gdf.to_file(output_file, driver="ESRI Shapefile", encoding="utf-8")
