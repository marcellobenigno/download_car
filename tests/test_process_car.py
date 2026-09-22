import pytest
from shapely.geometry import LineString, MultiLineString, Polygon

from process_car import (
    clean_geometry,
    ensure_polygon,
    extract_cod_ibge_e,
    extract_cod_ibge_m,
)


class TestExtractCodIbgeM:
    def test_extracts_seven_digit_code(self):
        assert extract_cod_ibge_m("SP-3550308-abc123") == "3550308"

    def test_returns_none_when_no_match(self):
        assert extract_cod_ibge_m("codigo-invalido") is None


class TestExtractCodIbgeE:
    def test_extracts_state_prefix(self):
        assert extract_cod_ibge_e("3550308") == "35"

    def test_returns_none_for_none_input(self):
        assert extract_cod_ibge_e(None) is None


class TestCleanGeometry:
    def test_returns_none_for_empty_geometry(self):
        assert clean_geometry(Polygon()) is None

    def test_returns_valid_geometry_for_valid_polygon(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        result = clean_geometry(poly)
        assert result is not None
        assert result.is_valid


class TestEnsurePolygon:
    def test_returns_none_for_none_input(self):
        assert ensure_polygon(None) is None

    def test_converts_linestring_to_polygon(self):
        line = LineString([(0, 0), (1, 0), (1, 1), (0, 0)])
        result = ensure_polygon(line)
        assert result.geom_type == "Polygon"

    def test_converts_multilinestring_to_multipolygon(self):
        lines = MultiLineString([
            [(0, 0), (1, 0), (1, 1), (0, 0)],
            [(2, 2), (3, 2), (3, 3), (2, 2)],
        ])
        result = ensure_polygon(lines)
        assert result.geom_type == "MultiPolygon"

    def test_leaves_polygon_unchanged(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        result = ensure_polygon(poly)
        assert result.geom_type == "Polygon"


import geopandas as gpd  # noqa: E402
from shapely.geometry import box  # noqa: E402

from process_car import read_car_shapefile  # noqa: E402


class TestReadCarShapefile:
    @pytest.fixture
    def car_zip(self, zip_shapefile):
        gdf = gpd.GeoDataFrame({
            "cod_imovel": [
                "PB-2513703-AAA",
                "PB-2513703-AAA",  # duplicado
                "PB-2501104-BBB",
                "PB-2599999-CCC",  # município fora da lista
                "SEM-CODIGO",
            ],
            "municipio": ["Sousa", "Sousa", "Areia", "Outro", "?"],
            "ind_status": ["AT"] * 5,
        }, geometry=[box(i, 0, i + 1, 1) for i in range(5)], crs=4674)
        return zip_shapefile(gdf, "AREA_IMOVEL_1")

    def test_filters_municipalities_renames_and_deduplicates(self, car_zip):
        result = read_car_shapefile(car_zip, municipios=["2513703", "2501104"])

        assert sorted(result["cod_imovel"]) == ["PB-2501104-BBB", "PB-2513703-AAA"]
        assert set(result["cod_ibge_e"]) == {"25"}
        assert {"nom_munici", "situacao"} <= set(result.columns)
        assert result.crs.to_epsg() == 4326

    def test_without_filter_keeps_all_municipalities(self, car_zip):
        result = read_car_shapefile(car_zip)
        assert len(result) == 4  # 5 registros menos 1 duplicado

    def test_returns_none_for_unreadable_file(self, tmp_path):
        broken = tmp_path / "quebrado.zip"
        broken.write_bytes(b"isto nao e um zip")
        assert read_car_shapefile(str(broken)) is None

    def test_saved_shapefile_keeps_geometry_and_attributes(self, car_zip, tmp_path):
        from process_car import save_shapefile

        result = read_car_shapefile(car_zip, municipios=["2513703"])
        output = tmp_path / "PB.shp"
        save_shapefile(result, str(output))

        saved = gpd.read_file(output)
        assert list(saved["cod_imovel"]) == ["PB-2513703-AAA"]
        assert saved.geometry.iloc[0].equals(result.geometry.iloc[0])
