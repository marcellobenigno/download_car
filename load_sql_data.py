import logging

import psycopg2
from decouple import config
from sqlalchemy import create_engine, text


def load_sql_data(state):
    """
    Remove dados desatualizados do banco e insere novos dados a partir dos arquivos SQL.

    Parâmetros:
        state (str): Código do estado cujos dados serão atualizados.
    """
    # Configuração do banco de dados
    DATABASE_URL = config("DB_CONNECTION_URL")
    engine = create_engine(DATABASE_URL)

    # Removendo dados desatualizados
    delete_sql = text(f"DELETE FROM maps_car WHERE cod_ibge_e = '{state}' AND cod_imovel LIKE '{state}-%'")

    try:
        with engine.connect() as connection:
            connection.execute(delete_sql)
            print(f"️❌ Dados antigos removidos para o estado: {state}")
    except Exception as e:
        logging.error(f"❌ Erro ao remover dados do estado {state}: {e}")
        return

    # Inserindo novos dados
    logging.info(f" Inserindo novos dados para o estado: {state}")
    PASS = config("DB_PASSWORD")
    HOST = config("DB_HOST")
    USER = config("DB_USER")
    DATABASE = config("DB_NAME")

    try:
        conn = psycopg2.connect(host=HOST, database=DATABASE, user=USER, password=PASS)
        cur = conn.cursor()
        with open(f"sql/{state}.sql", "r") as f:
            cur.execute(f.read())
        conn.commit()
        print(f"✅ Inserção concluída para o estado: {state}")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"❌ Erro ao inserir dados para o estado {state}: {error}")
    finally:
        if conn is not None:
            cur.close()
            conn.close()
