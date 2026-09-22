import os
import re
import subprocess

from decouple import config

VALID_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

IBGE_CODE_RE = re.compile(r"^\d{7}$")
TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DB_TABLE = config("DB_TABLE", default="maps_car")


def _codes_sql(municipios):
    """Monta a lista 'cod1', 'cod2', ... validando os códigos contra SQL injection."""
    invalid = [cod for cod in municipios if not IBGE_CODE_RE.match(str(cod))]
    if invalid:
        raise ValueError(f"Código(s) IBGE de município inválido(s): {', '.join(map(str, invalid))}")
    return ", ".join(f"'{cod}'" for cod in municipios)


def _validate_identifier(name):
    if not TABLE_NAME_RE.match(name):
        raise ValueError(f"Nome de tabela/coluna inválido: {name}")


def build_delete_query(municipios, table=DB_TABLE, column="cod_ibge_m"):
    """Monta o DELETE dos registros dos municípios informados."""
    _validate_identifier(table)
    _validate_identifier(column)
    return f"DELETE FROM {table} WHERE {column} IN ({_codes_sql(municipios)})"


def build_timestamps_query(municipios, table, column):
    """Preenche criado/modificado dos registros recém-inseridos (as tabelas do INCRA exigem esses campos)."""
    _validate_identifier(table)
    _validate_identifier(column)
    return (f"UPDATE {table} SET criado = now(), modificado = now() "
            f"WHERE {column} IN ({_codes_sql(municipios)}) AND criado IS NULL")


def load_sql_data(state, sql_path, municipios, table=DB_TABLE, column="cod_ibge_m", timestamps=False):
    """
    Substitui os registros dos municípios informados pelos do arquivo SQL, numa única transação:
    se qualquer comando falhar, nada é alterado. Com sql_path=None, apenas remove os registros.
    """
    state = state.upper()
    if state not in VALID_UFS:
        print(f"❌ Sigla de estado inválida: {state}")
        return False
    if not municipios:
        print(f"❌ Nenhum município informado para o estado {state}")
        return False
    try:
        delete_query = build_delete_query(municipios, table, column)
        timestamps_query = build_timestamps_query(municipios, table, column) if timestamps else None
    except ValueError as e:
        print(f"❌ {e}")
        return False

    env = os.environ.copy()
    env['PGPASSWORD'] = config("DB_PASSWORD")

    command = [
        "psql",
        "-h", config("DB_HOST"),
        "-p", config("DB_PORT", default="5432"),
        "-U", config("DB_USER"),
        "-d", config("DB_NAME"),
        "--single-transaction",
        "-v", "ON_ERROR_STOP=1",  # sem isso o psql retorna sucesso mesmo com comandos falhando
        "-q",
        "-c", delete_query,
    ]
    if sql_path:
        command += ["-f", sql_path]
    if timestamps_query and sql_path:
        command += ["-c", timestamps_query]

    try:
        print(f"Substituindo registros de {len(municipios)} município(s) de {state} em {table}"
              + (f" a partir de {sql_path}" if sql_path else " (somente exclusão)") + "...")
        subprocess.run(command, check=True, env=env)
        print(f"✅ Dados de {state} atualizados em {table}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao atualizar {table} para o estado {state} (nenhuma alteração gravada): {e}")
        return False
    except FileNotFoundError:
        print(
            "❌ Erro: O comando 'psql' não foi encontrado. Certifique-se de que o PostgreSQL está instalado e no seu PATH.")
        return False
