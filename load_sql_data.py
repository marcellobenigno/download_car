import os
import subprocess

from decouple import config


def load_sql_data(state):
    PASS = config("DB_PASSWORD")
    HOST = config("DB_HOST")
    USER = config("DB_USER")
    DATABASE = config("DB_NAME")

    sql_path = os.path.join("data", "sql", f"{state}.sql")

    try:
        # Remove dados antigos via engine SQLAlchemy (pode manter)
        # Depois chama o psql para importar o arquivo inteiro
        delete_sql = f"DELETE FROM maps_car WHERE cod_ibge_e = '{state}' AND cod_imovel LIKE '{state}-%'"
        # Supondo engine criado antes
        # engine.execute(delete_sql)

        # Comando psql para importar arquivo SQL grande
        command = [
            "psql",
            f"-h{HOST}",
            f"-U{USER}",
            f"-d{DATABASE}",
            "-f",
            sql_path
        ]

        # Configure variável de ambiente PGPASSWORD para não pedir senha
        env = os.environ.copy()
        env["PGPASSWORD"] = PASS

        subprocess.run(command, check=True, env=env)
        print(f"✅ Dados inseridos via psql para o estado: {state}")

    except Exception as e:
        print(f"❌ Erro ao inserir dados via psql para o estado {state}: {e}")
