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
