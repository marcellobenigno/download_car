import os
import subprocess

from decouple import config


def load_sql_data(state, sql_path):
    HOST = config("DB_HOST")
    USER = config("DB_USER")
    DATABASE = config("DB_NAME")
    DB_PASSWORD = config("DB_PASSWORD")  # A senha do banco de dados

    try:
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_PASSWORD

        # Comando DELETE
        sql_query = f"DELETE FROM maps_car WHERE cod_estado = '{state}' AND cod_imovel LIKE '{state}-%'"
        delete_command = [
            'psql',
            '-h', HOST,
            '-U', USER,
            '-d', DATABASE,
            '-c', sql_query
        ]
        # Passa o dicionário 'env' para o subprocess.run()
        print(f"Executando DELETE para o estado {state}...")
        subprocess.run(delete_command, check=True, env=env)
        print(f"✅ Registros antigos de {state} excluídos com sucesso (ou nenhum encontrado para a condição).")

        # Comando de inserção (LOAD)
        command = [
            "psql",
            "-h", HOST,  # HOST como item separado
            "-U", USER,  # USER como item separado
            "-d", DATABASE,  # DATABASE como item separado
            "-f",
            sql_path
        ]
        # Passa o dicionário 'env' para o subprocess.run()
        print(f"Inserindo dados via psql para o estado: {state} a partir de {sql_path}")
        subprocess.run(command, check=True, env=env)

        print(f"✅ Dados inseridos via psql para o estado: {state}")

    except subprocess.CalledProcessError as e:
        # Captura erros específicos do subprocess.run, incluindo a saída do psql
        print(f"❌ Erro de comando ao inserir/deletar dados para o estado {state}: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout.decode().strip()}")
        if e.stderr:
            print(f"Stderr: {e.stderr.decode().strip()}")
    except FileNotFoundError:
        print(
            "❌ Erro: O comando 'psql' não foi encontrado. Certifique-se de que o PostgreSQL está instalado e no seu PATH.")
    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado ao inserir dados via psql para o estado {state}: {e}")
