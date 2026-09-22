import subprocess

from decouple import config

DB_TABLE = config("DB_TABLE", default="maps_car")


def export_sql(shapefile, output_sql, table=DB_TABLE):
    command = [
        "shp2pgsql",
        "-a",
        "-e",  # sem BEGIN/COMMIT próprios: load_sql_data executa DELETE + INSERT numa única transação
        "-s", "4326",
        "-t", "2D",
        shapefile,
        table
    ]

    try:
        with open(output_sql, "w") as sql_file:
            subprocess.run(command, stdout=sql_file, check=True)
        print(f"✅ Arquivo SQL gerado com sucesso: {output_sql}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar shp2pgsql: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False
