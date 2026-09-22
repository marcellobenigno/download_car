import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box

from process_incra import fix_geometry, normalize_fields, process_incra_shapefile


def square(x0, y0, size=0.1, z=None):
    coords = [(x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size)]
    if z is not None:
        coords = [(x, y, z) for x, y in coords]
    return Polygon(coords)


class TestFixGeometry:
    def test_converts_polygon_z_to_2d_multipolygon(self):
        result = fix_geometry(square(0, 0, z=5))
        assert result.geom_type == "MultiPolygon"
        assert not result.has_z

    def test_keeps_valid_multipolygon(self):
        multi = MultiPolygon([square(0, 0), square(1, 1)])
        assert fix_geometry(multi).equals(multi)

    def test_repairs_invalid_polygon(self):
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
        result = fix_geometry(bowtie)
        assert result is not None
        assert result.is_valid

    @pytest.mark.parametrize("geom", [
        None,
        Polygon(),
        LineString([(0, 0), (1, 1)]),
        Point(0, 0),
        Polygon([(0, 0), (1, 1), (2, 2), (0, 0)]),  # sem área: vazio após buffer(0)
    ])
    def test_rejects_unusable_geometries(self, geom):
        assert fix_geometry(geom) is None


class TestNormalizeFields:
    def test_keeps_target_fields_truncates_text_and_parses_dates(self):
        gdf = gpd.GeoDataFrame({
            "num_proces": ["x" * 100],
            "data_certi": [pd.Timestamp("2026-02-06")],
            "uf_municip": ["  PB  "],
            "campo_extra": ["descartado"],
        }, geometry=[square(0, 0)], crs=4326)

        result = normalize_fields(gdf, "snci")

        assert "campo_extra" not in result.columns
        assert len(result.loc[0, "num_proces"]) == 70
        assert result.loc[0, "uf_municip"] == "PB"
        # 6 de fevereiro, não 2 de junho (o comando do sigitr trocava dia e mês)
        assert result.loc[0, "data_certi"] == pd.Timestamp("2026-02-06")

    def test_blank_and_missing_text_become_null(self):
        gdf = gpd.GeoDataFrame({"sr": ["   ", None]}, geometry=[square(0, 0), square(1, 1)], crs=4326)
        result = normalize_fields(gdf, "snci")
        assert result["sr"].isna().all()

    def test_unparseable_date_becomes_null(self):
        gdf = gpd.GeoDataFrame({"data_certi": ["não é data"]}, geometry=[square(0, 0)], crs=4326)
        assert pd.isna(normalize_fields(gdf, "snci").loc[0, "data_certi"])

    def test_keeps_non_text_fields_untouched(self):
        gdf = gpd.GeoDataFrame({"uf_id": [25]}, geometry=[square(0, 0)], crs=4326)
        assert normalize_fields(gdf, "sigef").loc[0, "uf_id"] == 25


@pytest.fixture
def municipios_gdf():
    # dois municípios vizinhos: A = [0,1]x[0,1] e B = [1,2]x[0,1]
    return gpd.GeoDataFrame(
        {"sigla_uf": ["PB", "PB"], "cod_ibge_m": ["2500001", "2500002"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs=4326,
    )


@pytest.fixture
def sigef_zip(zip_shapefile):
    """Shapefile no formato do SIGEF: Polygon Z em SIRGAS 2000 (EPSG:4674)."""
    rows = [
        ("dentro-de-A", square(0.2, 0.2, z=0)),
        ("divisa-A-B", square(0.95, 0.5, z=0)),
        ("dentro-de-B", square(1.5, 0.5, z=0)),
        ("invalido-em-A", Polygon([(0.5, 0.5, 0), (0.6, 0.6, 0), (0.6, 0.5, 0), (0.5, 0.6, 0)])),
        ("longe", square(5, 5, z=0)),
    ]
    gdf = gpd.GeoDataFrame({
        "parcela_co": [name for name, _ in rows],
        "status": ["REGISTRADA"] * len(rows),
        "data_submi": [pd.Timestamp("2026-02-06")] * len(rows),
        "municipio_": [9999999] * len(rows),  # código do INCRA é ignorado: vale a interseção
    }, geometry=[geom for _, geom in rows], crs=4674)
    return zip_shapefile(gdf, "Sigef Brasil_PB")


class TestProcessIncraShapefile:
    def test_assigns_each_parcel_to_every_municipality_it_intersects(self, sigef_zip, municipios_gdf):
        result = process_incra_shapefile(sigef_zip, "sigef", municipios_gdf)

        pairs = sorted(zip(result["parcela_co"], result["municipio"]))
        assert pairs == [
            ("dentro-de-A", "2500001"),
            ("dentro-de-B", "2500002"),
            ("divisa-A-B", "2500001"),
            ("divisa-A-B", "2500002"),  # imóvel na divisa aparece nos dois municípios
            ("invalido-em-A", "2500001"),  # geometria inválida é reparada, não descartada
        ]

    def test_output_is_clean_2d_multipolygon_in_wgs84(self, sigef_zip, municipios_gdf):
        result = process_incra_shapefile(sigef_zip, "sigef", municipios_gdf)

        assert result.crs.to_epsg() == 4326
        assert (result.geom_type == "MultiPolygon").all()
        assert not result.has_z.any()
        assert result.is_valid.all()

    def test_keeps_only_target_columns(self, sigef_zip, municipios_gdf):
        result = process_incra_shapefile(sigef_zip, "sigef", municipios_gdf)

        assert set(result.columns) == {"parcela_co", "status", "data_submi", "geometry", "municipio"}
        assert (result["data_submi"] == pd.Timestamp("2026-02-06")).all()

    def test_only_selected_municipalities(self, sigef_zip, municipios_gdf):
        result = process_incra_shapefile(sigef_zip, "sigef", municipios_gdf.iloc[[1]])
        assert sorted(result["parcela_co"]) == ["dentro-de-B", "divisa-A-B"]
        assert set(result["municipio"]) == {"2500002"}

    def test_returns_none_for_unreadable_file(self, tmp_path, municipios_gdf):
        broken = tmp_path / "quebrado.zip"
        broken.write_bytes(b"isto nao e um zip")
        assert process_incra_shapefile(str(broken), "sigef", municipios_gdf) is None
