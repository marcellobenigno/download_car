import os
import time
import zipfile
from urllib.parse import quote

import httpx

# O INCRA só disponibiliza shapefiles estáticos por UF, sem filtro por município no servidor.
INCRA_BASE_URL = "https://certificacao.incra.gov.br/csv_shp/zip/"
INCRA_FILENAME = {
    "sigef": "Sigef Brasil_{uf}.zip",
    "snci": "Imóvel certificado SNCI Brasil_{uf}.zip",
}

# certificacao.incra.gov.br responde com cadeia de certificados incompleta nos truststores usuais;
# o dado é público e o HTTPS ainda criptografa o tráfego, então seguimos sem verificar o certificado.
VERIFY_SSL = False
USER_AGENT = "Mozilla/5.0 (compatible; download-car/1.0)"
CONNECT_TIMEOUT = 20  # falha rápido se não conseguir nem abrir a conexão
TIMEOUT = 600  # tempo para baixar o corpo, uma vez conectado (arquivos de até ~700 MB por UF)
MAX_TENTATIVAS_DOWNLOAD = 3
ESPERA_ENTRE_TENTATIVAS = 20

# Os arquivos de UF inteira são reaproveitados por alguns dias em vez de baixados a cada execução.
CACHE_VALIDADE_SEGUNDOS = 2 * 24 * 60 * 60


def get_incra_zip_path(fonte, uf, zip_dir):
    return os.path.join(zip_dir, f"{fonte.upper()}_{uf}.zip")


def download_incra(fonte, uf, zip_dir):
    """Baixa o shapefile da UF (SIGEF ou SNCI) do INCRA, reaproveitando o cache se tiver até 2 dias."""
    zip_path = get_incra_zip_path(fonte, uf, zip_dir)

    if os.path.exists(zip_path):
        idade = time.time() - os.path.getmtime(zip_path)
        if idade <= CACHE_VALIDADE_SEGUNDOS and zipfile.is_zipfile(zip_path):
            print(f"✅ Arquivo já existe: {zip_path} (baixado há {int(idade // 3600)}h, validade de 2 dias)")
            return zip_path
        print(f"⚠️ Arquivo em cache desatualizado ou corrompido, baixando novamente: {zip_path}")

    url = INCRA_BASE_URL + quote(INCRA_FILENAME[fonte].format(uf=uf))
    tmp_path = zip_path + ".tmp"
    timeout = httpx.Timeout(TIMEOUT, connect=CONNECT_TIMEOUT)

    print(f"📥 Baixando {fonte.upper()} de {uf}: {url}")
    for tentativa in range(1, MAX_TENTATIVAS_DOWNLOAD + 1):
        try:
            with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, verify=VERIFY_SSL,
                              timeout=timeout, follow_redirects=True) as resp:
                if resp.status_code == 404:
                    print(f"❌ Arquivo não encontrado no INCRA: {url}")
                    return None
                resp.raise_for_status()
                with open(tmp_path, "wb") as tmp:
                    for chunk in resp.iter_bytes(chunk_size=256 * 1024):
                        tmp.write(chunk)

            if not zipfile.is_zipfile(tmp_path):
                raise httpx.HTTPError("arquivo baixado não é um zip válido")
            os.replace(tmp_path, zip_path)
            print(f"⬇️ Download concluído: {zip_path}")
            return zip_path
        except httpx.HTTPError as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if tentativa < MAX_TENTATIVAS_DOWNLOAD:
                print(f"⚠️ Falha ao baixar do INCRA (tentativa {tentativa}/{MAX_TENTATIVAS_DOWNLOAD}): {e}. "
                      f"Tentando de novo em {ESPERA_ENTRE_TENTATIVAS}s...")
                time.sleep(ESPERA_ENTRE_TENTATIVAS)
            else:
                print(f"❌ Não foi possível baixar {url} após {MAX_TENTATIVAS_DOWNLOAD} tentativas: {e}. "
                      "O servidor certificacao.incra.gov.br costuma ficar instável/fora do ar.")
    return None
