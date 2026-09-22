import zipfile

import geopandas as gpd
import pytest
from shapely.geometry import box

import main


class TestParseArgs:
    @pytest.mark.parametrize("argv, expected", [
        ([], ["car"]),
        (["--fonte", "sigef"], ["sigef"]),
        (["--fonte", "car", "sigef", "snci"], ["car", "sigef", "snci"]),
        (["--fonte", "car,sigef,snci"], ["car", "sigef", "snci"]),
        (["--fonte", "car", "sigef,", "snci"], ["car", "sigef", "snci"]),  # como digitado pelo usuário
        (["--fonte", "SIGEF , Snci"], ["sigef", "snci"]),
    ])
    def test_accepts_sources_separated_by_space_or_comma(self, monkeypatch, argv, expected):
        monkeypatch.setattr("sys.argv", ["main.py", "PB,CE", *argv])
        args = main.parse_args()
        assert args.fonte == expected
        assert args.estados == "PB,CE"

    @pytest.mark.parametrize("argv", [["--fonte", "car,xpto"], ["--fonte", ","]])
    def test_rejects_unknown_source(self, monkeypatch, argv):
        monkeypatch.setattr("sys.argv", ["main.py", *argv])
        with pytest.raises(SystemExit):
            main.parse_args()

    def test_states_are_optional(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["main.py"])
        assert main.parse_args().estados is None


class TestSafeExtract:
    def test_extracts_regular_zip(self, tmp_path):
        zip_path = tmp_path / "ok.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("pasta/dados.shp", b"x")
        with zipfile.ZipFile(zip_path) as zf:
            main.safe_extract(zf, tmp_path / "out")
        assert (tmp_path / "out" / "pasta" / "dados.shp").exists()

    def test_blocks_path_traversal(self, tmp_path):
        zip_path = tmp_path / "malicioso.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../fora.txt", b"x")
        with zipfile.ZipFile(zip_path) as zf, pytest.raises(ValueError):
            main.safe_extract(zf, tmp_path / "out")
        assert not (tmp_path / "fora.txt").exists()


def records(counts, column="municipio"):
    """GeoDataFrame com `n` registros para cada código em `counts`."""
    codes = [cod for cod, n in counts.items() for _ in range(n)]
    return gpd.GeoDataFrame({column: codes}, geometry=[box(i, 0, i + 1, 1) for i in range(len(codes))], crs=4326)


@pytest.fixture
def db_counts(monkeypatch):
    """Quantidade atual de registros por município na base (simulada)."""
    counts = {}

    def fake_count(table, column, municipios):
        return {cod: counts.get(cod, 0) for cod in municipios}

    monkeypatch.setattr(main, "count_records_by_municipality", fake_count)
    return counts


class TestSelectOutdated:
    def test_same_count_is_skipped_different_count_is_updated(self, db_counts):
        db_counts.update({"2500001": 2, "2500002": 5})
        gdf = records({"2500001": 2, "2500002": 3})

        selected, to_update = main.select_outdated(gdf, ["2500001", "2500002"], "maps_incrasigef", "municipio")

        assert to_update == ["2500002"]
        assert list(selected["municipio"]) == ["2500002"] * 3

    def test_municipality_missing_from_source_is_updated_to_empty(self, db_counts):
        db_counts.update({"2500001": 4})
        selected, to_update = main.select_outdated(records({}), ["2500001"], "maps_incrasnci", "municipio")
        assert to_update == ["2500001"]
        assert selected.empty

    def test_municipality_empty_in_both_is_skipped(self, db_counts):
        _, to_update = main.select_outdated(records({}), ["2500001"], "maps_incrasnci", "municipio")
        assert to_update == []

    def test_compares_integer_codes_as_text(self, db_counts):
        db_counts.update({"2500001": 1})
        gdf = records({2500001: 1})
        _, to_update = main.select_outdated(gdf, ["2500001"], "maps_incrasigef", "municipio")
        assert to_update == []

    def test_returns_none_when_count_fails(self, monkeypatch):
        monkeypatch.setattr(main, "count_records_by_municipality", lambda *a: None)
        assert main.select_outdated(records({"2500001": 1}), ["2500001"], "maps_car", "municipio") is None


@pytest.fixture
def incra_pipeline(monkeypatch, tmp_path, db_counts):
    """Simula download/processamento do INCRA e registra o que seria exportado e carregado no banco."""
    calls = {"exported": [], "loaded": [], "source": records({})}

    monkeypatch.setattr(main, "download_incra", lambda fonte, uf, zip_dir: str(tmp_path / f"{fonte}_{uf}.zip"))
    monkeypatch.setattr(main, "process_incra_shapefile", lambda zip_path, fonte, gdf: calls["source"].copy())

    def fake_save(gdf, path):
        calls["saved"] = gdf

    def fake_export(shapefile, output_sql, table):
        calls["exported"].append((shapefile, output_sql, table))
        return True

    def fake_load(state, sql_path, municipios, **kwargs):
        calls["loaded"].append({"state": state, "sql_path": sql_path, "municipios": municipios, **kwargs})
        return True

    monkeypatch.setattr(main, "save_incra_shapefile", fake_save)
    monkeypatch.setattr(main, "export_sql", fake_export)
    monkeypatch.setattr(main, "load_sql_data", fake_load)
    calls["dirs"] = (str(tmp_path / "sql"), str(tmp_path / "shp"), str(tmp_path / "zip"), str(tmp_path / "unzip"))
    return calls


@pytest.fixture
def municipios_pb():
    return gpd.GeoDataFrame(
        {"sigla_uf": ["PB", "PB"], "cod_ibge_m": ["2500001", "2500002"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs=4326,
    )


class TestUpdateIncra:
    def test_nothing_is_written_when_all_counts_match(self, incra_pipeline, db_counts, municipios_pb):
        db_counts.update({"2500001": 2, "2500002": 1})
        incra_pipeline["source"] = records({"2500001": 2, "2500002": 1})

        main.update_incra("sigef", "PB", municipios_pb, incra_pipeline["dirs"])

        assert incra_pipeline["exported"] == []
        assert incra_pipeline["loaded"] == []

    def test_only_outdated_municipalities_are_replaced(self, incra_pipeline, db_counts, municipios_pb):
        db_counts.update({"2500001": 2, "2500002": 9})
        incra_pipeline["source"] = records({"2500001": 2, "2500002": 3})

        main.update_incra("snci", "PB", municipios_pb, incra_pipeline["dirs"])

        saved = incra_pipeline["saved"]
        assert list(saved["municipio"]) == [2500002] * 3  # gravado como inteiro, como a coluna da tabela
        [(_, output_sql, table)] = incra_pipeline["exported"]
        assert table == "maps_incrasnci"
        assert incra_pipeline["loaded"] == [{
            "state": "PB", "sql_path": output_sql, "municipios": ["2500002"],
            "table": "maps_incrasnci", "column": "municipio", "timestamps": True,
        }]

    def test_municipality_that_disappeared_from_source_is_only_deleted(self, incra_pipeline, db_counts, municipios_pb):
        db_counts.update({"2500001": 4})

        main.update_incra("sigef", "PB", municipios_pb.iloc[[0]], incra_pipeline["dirs"])

        assert incra_pipeline["exported"] == []
        [load] = incra_pipeline["loaded"]
        assert load["sql_path"] is None
        assert load["municipios"] == ["2500001"]

    def test_stops_when_download_fails(self, incra_pipeline, monkeypatch, municipios_pb):
        monkeypatch.setattr(main, "download_incra", lambda *a: None)
        main.update_incra("sigef", "PB", municipios_pb, incra_pipeline["dirs"])
        assert incra_pipeline["loaded"] == []

    def test_stops_when_export_fails(self, incra_pipeline, db_counts, monkeypatch, municipios_pb):
        incra_pipeline["source"] = records({"2500001": 1})
        monkeypatch.setattr(main, "export_sql", lambda *a, **k: False)
        main.update_incra("sigef", "PB", municipios_pb, incra_pipeline["dirs"])
        assert incra_pipeline["loaded"] == []


class TestMain:
    @pytest.fixture
    def run_main(self, monkeypatch, tmp_path, municipios_pb):
        """Executa main() com o banco simulado e registra os estados atualizados por fonte."""
        calls = []
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main, "get_active_municipalities",
                            lambda: {"PB": ["2500001", "2500002", "2500003"], "RO": ["1100304"]})
        monkeypatch.setattr(main, "get_active_municipality_geometries", lambda: municipios_pb)
        monkeypatch.setattr(main, "update_car", lambda state, municipios, dirs: calls.append(("car", state, municipios)))
        monkeypatch.setattr(main, "update_incra", lambda fonte, state, gdf, dirs:
                            calls.append((fonte, state, list(gdf["cod_ibge_m"]))))

        def _run(*argv):
            monkeypatch.setattr("sys.argv", ["main.py", *argv])
            main.main()
            return calls

        return _run

    def test_defaults_to_car_for_every_state_with_active_prefeitura(self, run_main):
        assert run_main() == [
            ("car", "PB", ["2500001", "2500002", "2500003"]),
            ("car", "RO", ["1100304"]),
        ]

    def test_ignores_states_without_active_prefeitura(self, run_main, capsys):
        assert run_main("PB,CE") == [("car", "PB", ["2500001", "2500002", "2500003"])]
        assert "CE não possui municípios com prefeitura ativa" in capsys.readouterr().out

    def test_incra_skips_municipalities_and_states_without_geometry(self, run_main, capsys):
        calls = run_main("--fonte", "car,sigef")

        assert ("sigef", "PB", ["2500001", "2500002"]) in calls  # 2500003 não tem geometria
        assert not any(fonte == "sigef" and state == "RO" for fonte, state, _ in calls)
        out = capsys.readouterr().out
        assert "sem geometria cadastrada, ignorados no SIGEF/SNCI: 1100304, 2500003" in out

    def test_exits_when_database_is_unavailable(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["main.py"])
        monkeypatch.setattr(main, "get_active_municipalities", lambda: None)
        with pytest.raises(SystemExit):
            main.main()


@pytest.fixture
def car_pipeline(monkeypatch, tmp_path, db_counts):
    """Simula o download do SICAR (um zip real com um .shp) e registra o que seria carregado no banco."""
    calls = {"exported": [], "loaded": [], "source": records({}, column="cod_ibge_m")}

    def fake_download(state, zip_path):
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("AREA_IMOVEL_1.shp", b"x")
        return zip_path

    monkeypatch.setattr(main, "download_car", fake_download)
    monkeypatch.setattr(main, "read_car_shapefile",
                        lambda shp, municipios: calls.update(read=shp) or calls["source"].copy())
    monkeypatch.setattr(main, "save_car_shapefile", lambda gdf, path: calls.update(saved=gdf))
    monkeypatch.setattr(main, "export_sql",
                        lambda shp, sql, table: calls["exported"].append((shp, sql, table)) or True)
    monkeypatch.setattr(main, "load_sql_data",
                        lambda state, sql_path, municipios, **kw: calls["loaded"].append(
                            {"state": state, "sql_path": sql_path, "municipios": municipios, **kw}) or True)

    dirs = [tmp_path / name for name in ("sql", "shp", "zip", "unzip")]
    for d in dirs:
        d.mkdir()
    calls["dirs"] = tuple(str(d) for d in dirs)
    return calls


class TestUpdateCar:
    def test_nothing_is_written_when_all_counts_match(self, car_pipeline, db_counts):
        db_counts.update({"2500001": 2})
        car_pipeline["source"] = records({"2500001": 2}, column="cod_ibge_m")

        main.update_car("PB", ["2500001"], car_pipeline["dirs"])

        assert car_pipeline["read"].endswith("AREA_IMOVEL_1.shp")
        assert car_pipeline["exported"] == []
        assert car_pipeline["loaded"] == []

    def test_only_outdated_municipalities_are_replaced(self, car_pipeline, db_counts):
        db_counts.update({"2500001": 2, "2500002": 1})
        car_pipeline["source"] = records({"2500001": 2, "2500002": 4}, column="cod_ibge_m")

        main.update_car("PB", ["2500001", "2500002"], car_pipeline["dirs"])

        assert list(car_pipeline["saved"]["cod_ibge_m"]) == ["2500002"] * 4
        [(_, output_sql, table)] = car_pipeline["exported"]
        assert table == "maps_car"
        assert car_pipeline["loaded"] == [{
            "state": "PB", "sql_path": output_sql, "municipios": ["2500002"],
            "table": "maps_car", "column": "cod_ibge_m",
        }]

    def test_stops_when_zip_has_no_shapefile(self, car_pipeline, monkeypatch):
        def zip_without_shp(state, zip_path):
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("leiame.txt", b"x")
            return zip_path

        monkeypatch.setattr(main, "download_car", zip_without_shp)
        main.update_car("PB", ["2500001"], car_pipeline["dirs"])
        assert "read" not in car_pipeline
        assert car_pipeline["loaded"] == []

    def test_stops_when_download_fails(self, car_pipeline, monkeypatch):
        monkeypatch.setattr(main, "download_car", lambda *a: None)
        main.update_car("PB", ["2500001"], car_pipeline["dirs"])
        assert car_pipeline["loaded"] == []
