import subprocess

import pytest

import load_sql_data
from load_sql_data import build_delete_query, build_timestamps_query


class TestBuildDeleteQuery:
    def test_deletes_only_given_municipalities(self):
        query = build_delete_query(["5100201", "5100250"])
        assert query == "DELETE FROM maps_car WHERE cod_ibge_m IN ('5100201', '5100250')"

    def test_uses_given_table_and_column(self):
        query = build_delete_query(["5100201"], table="maps_incrasigef", column="municipio")
        assert query == "DELETE FROM maps_incrasigef WHERE municipio IN ('5100201')"

    @pytest.mark.parametrize("code", ["1'; DROP TABLE maps_car; --", "510020", "51002011", "", None])
    def test_rejects_invalid_code(self, code):
        with pytest.raises(ValueError):
            build_delete_query(["5100201", code])

    @pytest.mark.parametrize("table, column", [
        ("maps_car; DROP TABLE x", "cod_ibge_m"),
        ("maps_car", "cod_ibge_m = cod_ibge_m OR 1=1 --"),
        ("1tabela", "cod_ibge_m"),
    ])
    def test_rejects_invalid_identifiers(self, table, column):
        with pytest.raises(ValueError):
            build_delete_query(["5100201"], table=table, column=column)


class TestBuildTimestampsQuery:
    def test_only_touches_new_rows_of_given_municipalities(self):
        query = build_timestamps_query(["5100201"], "maps_incrasnci", "municipio")
        assert query == ("UPDATE maps_incrasnci SET criado = now(), modificado = now() "
                         "WHERE municipio IN ('5100201') AND criado IS NULL")


@pytest.fixture
def run_calls(monkeypatch, db_env):
    """Substitui subprocess.run e registra os comandos executados."""
    calls = []

    def fake_run(command, **kwargs):
        calls.append({"command": command, **kwargs})

    monkeypatch.setattr(load_sql_data.subprocess, "run", fake_run)
    return calls


class TestLoadSqlData:
    def test_runs_delete_insert_and_timestamps_in_a_single_transaction(self, run_calls):
        ok = load_sql_data.load_sql_data("pb", "/tmp/SNCI_PB.sql", ["2513703"],
                                         table="maps_incrasnci", column="municipio", timestamps=True)

        assert ok is True
        assert len(run_calls) == 1  # uma única chamada ao psql = uma única transação
        call = run_calls[0]
        command = call["command"]
        assert "--single-transaction" in command
        assert command[command.index("-v") + 1] == "ON_ERROR_STOP=1"
        assert command[command.index("-h") + 1] == "db.test"
        assert call["env"]["PGPASSWORD"] == "secret"
        assert call["check"] is True

        # ordem: DELETE -> arquivo SQL -> UPDATE dos timestamps
        steps = [(flag, value) for flag, value in zip(command, command[1:]) if flag in ("-c", "-f")]
        assert steps == [
            ("-c", "DELETE FROM maps_incrasnci WHERE municipio IN ('2513703')"),
            ("-f", "/tmp/SNCI_PB.sql"),
            ("-c", build_timestamps_query(["2513703"], "maps_incrasnci", "municipio")),
        ]

    def test_car_does_not_touch_timestamps(self, run_calls):
        assert load_sql_data.load_sql_data("PB", "/tmp/PB.sql", ["2513703"]) is True
        command = run_calls[0]["command"]
        assert not any("UPDATE" in part for part in command)

    def test_without_sql_file_only_deletes(self, run_calls):
        ok = load_sql_data.load_sql_data("PB", None, ["2513703"],
                                         table="maps_incrasigef", column="municipio", timestamps=True)
        assert ok is True
        command = run_calls[0]["command"]
        assert "-f" not in command
        assert [part for part in command if part.startswith(("DELETE", "UPDATE"))] == [
            "DELETE FROM maps_incrasigef WHERE municipio IN ('2513703')"
        ]

    @pytest.mark.parametrize("state, municipios", [
        ("XX", ["2513703"]),
        ("PB", []),
        ("PB", ["abc"]),
    ])
    def test_invalid_input_never_calls_psql(self, run_calls, state, municipios):
        assert load_sql_data.load_sql_data(state, "/tmp/x.sql", municipios) is False
        assert run_calls == []

    def test_returns_false_when_psql_fails(self, monkeypatch, db_env):
        def failing_run(command, **kwargs):
            raise subprocess.CalledProcessError(3, command)

        monkeypatch.setattr(load_sql_data.subprocess, "run", failing_run)
        assert load_sql_data.load_sql_data("PB", "/tmp/PB.sql", ["2513703"]) is False

    def test_returns_false_when_psql_is_missing(self, monkeypatch, db_env):
        def missing_run(command, **kwargs):
            raise FileNotFoundError("psql")

        monkeypatch.setattr(load_sql_data.subprocess, "run", missing_run)
        assert load_sql_data.load_sql_data("PB", "/tmp/PB.sql", ["2513703"]) is False
