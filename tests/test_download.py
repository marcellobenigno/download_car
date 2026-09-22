import io
import os
import time
import zipfile

import httpx
import pytest

import download_car
import download_incra

TRES_DIAS = 3 * 24 * 60 * 60


def zip_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("dados.shp", b"conteudo")
    return buffer.getvalue()


def write_zip(path, age_seconds=0):
    path.write_bytes(zip_bytes())
    mtime = time.time() - age_seconds
    os.utime(path, (mtime, mtime))


# ------------------------------------------------------------------ CAR / SICAR

class FakeSicar:
    """Imita a biblioteca SICAR: grava o zip num arquivo temporário e devolve o caminho."""
    calls = []
    content = zip_bytes()
    error = None

    def download_state(self, state, polygon):
        FakeSicar.calls.append(state)
        if FakeSicar.error:
            raise FakeSicar.error
        path = os.path.join(FakeSicar.tmp_dir, f"sicar_{state}.zip")
        with open(path, "wb") as f:
            f.write(FakeSicar.content)
        return path


@pytest.fixture
def fake_sicar(monkeypatch, tmp_path):
    FakeSicar.calls = []
    FakeSicar.content = zip_bytes()
    FakeSicar.error = None
    FakeSicar.tmp_dir = str(tmp_path)
    monkeypatch.setattr(download_car, "Sicar", FakeSicar)
    return FakeSicar


class TestDownloadCar:
    def test_reuses_cached_zip_younger_than_two_days(self, fake_sicar, tmp_path):
        zip_path = tmp_path / "PB_AREA_IMOVEL.zip"
        write_zip(zip_path, age_seconds=60 * 60)

        assert download_car.download_car("PB", str(zip_path)) == str(zip_path)
        assert fake_sicar.calls == []

    def test_downloads_again_when_cache_is_older_than_two_days(self, fake_sicar, tmp_path):
        zip_path = tmp_path / "PB_AREA_IMOVEL.zip"
        write_zip(zip_path, age_seconds=TRES_DIAS)

        assert download_car.download_car("PB", str(zip_path)) == str(zip_path)
        assert fake_sicar.calls == ["PB"]
        assert time.time() - os.path.getmtime(zip_path) < 60

    def test_downloads_again_when_cache_is_corrupted(self, fake_sicar, tmp_path):
        zip_path = tmp_path / "PB_AREA_IMOVEL.zip"
        zip_path.write_bytes(b"corrompido")

        assert download_car.download_car("PB", str(zip_path)) == str(zip_path)
        assert fake_sicar.calls == ["PB"]
        assert zipfile.is_zipfile(zip_path)

    def test_rejects_corrupted_download(self, fake_sicar, tmp_path):
        fake_sicar.content = b"html de erro"
        zip_path = tmp_path / "PB_AREA_IMOVEL.zip"

        assert download_car.download_car("PB", str(zip_path)) is None
        assert not zip_path.exists()
        assert not (tmp_path / "sicar_PB.zip").exists()

    def test_returns_none_when_download_fails(self, fake_sicar, tmp_path):
        fake_sicar.error = RuntimeError("captcha")
        assert download_car.download_car("PB", str(tmp_path / "PB_AREA_IMOVEL.zip")) is None

    def test_zip_path_has_no_date_so_cache_survives_across_days(self, tmp_path):
        assert download_car.get_car_zip_path("PB", str(tmp_path)) == str(tmp_path / "PB_AREA_IMOVEL.zip")


# ----------------------------------------------------------------- INCRA

class FakeResponse:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erro", request=None, response=None)

    def iter_bytes(self, chunk_size):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_http(monkeypatch):
    """Substitui httpx.stream por uma fila de respostas (ou exceções) e registra as URLs pedidas."""
    state = {"responses": [], "urls": [], "sleeps": []}

    def fake_stream(method, url, **kwargs):
        state["urls"].append(url)
        response = state["responses"].pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(download_incra.httpx, "stream", fake_stream)
    monkeypatch.setattr(download_incra.time, "sleep", lambda seconds: state["sleeps"].append(seconds))
    return state


class TestDownloadIncra:
    def test_reuses_cached_zip_younger_than_two_days(self, fake_http, tmp_path):
        write_zip(tmp_path / "SIGEF_PB.zip", age_seconds=60 * 60)

        assert download_incra.download_incra("sigef", "PB", str(tmp_path)) == str(tmp_path / "SIGEF_PB.zip")
        assert fake_http["urls"] == []

    def test_downloads_again_when_cache_is_older_than_two_days(self, fake_http, tmp_path):
        write_zip(tmp_path / "SIGEF_PB.zip", age_seconds=TRES_DIAS)
        fake_http["responses"] = [FakeResponse(content=zip_bytes())]

        assert download_incra.download_incra("sigef", "PB", str(tmp_path)) == str(tmp_path / "SIGEF_PB.zip")
        assert len(fake_http["urls"]) == 1

    @pytest.mark.parametrize("fonte, expected_url", [
        ("sigef", "https://certificacao.incra.gov.br/csv_shp/zip/Sigef%20Brasil_RO.zip"),
        ("snci", "https://certificacao.incra.gov.br/csv_shp/zip/Im%C3%B3vel%20certificado%20SNCI%20Brasil_RO.zip"),
    ])
    def test_builds_incra_url(self, fake_http, tmp_path, fonte, expected_url):
        fake_http["responses"] = [FakeResponse(content=zip_bytes())]
        download_incra.download_incra(fonte, "RO", str(tmp_path))
        assert fake_http["urls"] == [expected_url]

    def test_retries_after_network_error(self, fake_http, tmp_path):
        fake_http["responses"] = [httpx.ConnectTimeout("timeout"), FakeResponse(content=zip_bytes())]

        assert download_incra.download_incra("snci", "PB", str(tmp_path)) == str(tmp_path / "SNCI_PB.zip")
        assert fake_http["sleeps"] == [download_incra.ESPERA_ENTRE_TENTATIVAS]

    def test_gives_up_after_max_attempts(self, fake_http, tmp_path):
        fake_http["responses"] = [httpx.ConnectError("fora do ar")] * download_incra.MAX_TENTATIVAS_DOWNLOAD

        assert download_incra.download_incra("sigef", "PB", str(tmp_path)) is None
        assert len(fake_http["urls"]) == download_incra.MAX_TENTATIVAS_DOWNLOAD
        assert os.listdir(tmp_path) == []  # nenhum .tmp esquecido

    def test_does_not_retry_on_404(self, fake_http, tmp_path):
        fake_http["responses"] = [FakeResponse(status_code=404)]

        assert download_incra.download_incra("sigef", "XX", str(tmp_path)) is None
        assert len(fake_http["urls"]) == 1

    def test_retries_when_body_is_not_a_zip(self, fake_http, tmp_path):
        fake_http["responses"] = [FakeResponse(content=b"<html>manutencao</html>"), FakeResponse(content=zip_bytes())]

        assert download_incra.download_incra("sigef", "PB", str(tmp_path)) == str(tmp_path / "SIGEF_PB.zip")
        assert zipfile.is_zipfile(tmp_path / "SIGEF_PB.zip")
        assert sorted(os.listdir(tmp_path)) == ["SIGEF_PB.zip"]
