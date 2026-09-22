import pytest

from load_sql_data import build_delete_query
from municipios import parse_municipality_rows


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


class TestBuildDeleteQuery:
    def test_deletes_only_given_municipalities(self):
        query = build_delete_query(["5100201", "5100250"])
        assert query.endswith("WHERE cod_ibge_m IN ('5100201', '5100250')")

    def test_rejects_invalid_code(self):
        with pytest.raises(ValueError):
            build_delete_query(["5100201", "1'; DROP TABLE maps_car; --"])


class TestBuildDeleteQueryTable:
    def test_uses_given_table_and_column(self):
        query = build_delete_query(["5100201"], table="maps_incrasigef", column="municipio")
        assert query == "DELETE FROM maps_incrasigef WHERE municipio IN ('5100201')"

    def test_rejects_invalid_table(self):
        with pytest.raises(ValueError):
            build_delete_query(["5100201"], table="maps_car; DROP TABLE x")
