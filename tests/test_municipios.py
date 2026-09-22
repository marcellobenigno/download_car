import pytest
from shapely.geometry import MultiPolygon, Polygon

import municipios
from municipios import parse_municipality_rows


@pytest.fixture
def fake_query(monkeypatch):
    """Substitui run_query: devolve a resposta configurada e registra o SQL recebido."""
    state = {"output": "", "queries": []}

    def fake_run_query(sql):
        state["queries"].append(sql)
        return state["output"]

    monkeypatch.setattr(municipios, "run_query", fake_run_query)
    return state


class TestParseMunicipalityRows:
    def test_groups_codes_by_uf(self):
        output = "MT|5100201\nMT|5100250\nSP|3500105\n"
        assert parse_municipality_rows(output) == {
            "MT": ["5100201", "5100250"],
            "SP": ["3500105"],
        }

    def test_skips_invalid_rows(self):
        output = "MT|5100201\n|3500105\nSP|abc\n\n"
        assert parse_municipality_rows(output) == {"MT": ["5100201"]}

    def test_normalizes_uf_and_whitespace(self):
        assert parse_municipality_rows(" mt | 5100201 \n") == {"MT": ["5100201"]}


class TestGetActiveMunicipalities:
    def test_filters_by_active_prefeitura(self, fake_query):
        fake_query["output"] = "PB|2513703\n"
        assert municipios.get_active_municipalities() == {"PB": ["2513703"]}
        sql = " ".join(fake_query["queries"][0].split())
        assert "INNER JOIN prefeitura_prefeitura p ON p.municipio_id = m.id" in sql
        assert "WHERE p.ativo = TRUE" in sql

    def test_returns_none_on_database_error(self, fake_query):
        fake_query["output"] = None
        assert municipios.get_active_municipalities() is None


class TestGetActiveMunicipalityGeometries:
    def test_decodes_hex_wkb_into_geodataframe(self, fake_query):
        geom = MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
        fake_query["output"] = f"pb|2513703|{geom.wkb_hex}\nPB|invalido|{geom.wkb_hex}\n"

        gdf = municipios.get_active_municipality_geometries()

        assert list(gdf["sigla_uf"]) == ["PB"]
        assert list(gdf["cod_ibge_m"]) == ["2513703"]
        assert gdf.crs.to_epsg() == 4326
        assert gdf.geometry.iloc[0].equals(geom)

    def test_empty_result_keeps_columns(self, fake_query):
        gdf = municipios.get_active_municipality_geometries()
        assert gdf.empty
        assert list(gdf.columns) == ["sigla_uf", "cod_ibge_m", "geometry"]

    def test_returns_none_on_database_error(self, fake_query):
        fake_query["output"] = None
        assert municipios.get_active_municipality_geometries() is None


class TestCountRecordsByMunicipality:
    def test_fills_missing_municipalities_with_zero(self, fake_query):
        fake_query["output"] = "2513703|7\n"
        counts = municipios.count_records_by_municipality("maps_incrasnci", "municipio", ["2513703", "2501104"])
        assert counts == {"2513703": 7, "2501104": 0}
        assert fake_query["queries"] == [
            "SELECT municipio, count(*) FROM maps_incrasnci WHERE municipio IN ('2513703', '2501104') "
            "GROUP BY municipio"
        ]

    def test_returns_none_on_database_error(self, fake_query):
        fake_query["output"] = None
        assert municipios.count_records_by_municipality("maps_car", "cod_ibge_m", ["2513703"]) is None

    @pytest.mark.parametrize("table, column, codes", [
        ("maps_car; DROP TABLE x", "cod_ibge_m", ["2513703"]),
        ("maps_car", "cod_ibge_m", ["2513703' OR '1'='1"]),
    ])
    def test_rejects_unsafe_input_before_querying(self, fake_query, table, column, codes):
        with pytest.raises(ValueError):
            municipios.count_records_by_municipality(table, column, codes)
        assert fake_query["queries"] == []
