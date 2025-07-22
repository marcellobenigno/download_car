import subprocess


def export_sql(shapefile, output_sql):
    command = [
        "shp2pgsql",
        "-a",
        "-s", "4326",
        "-t", "2D",
        shapefile,
        "maps_car"
    ]

    try:
        with open(output_sql, "w") as sql_file:
            subprocess.run(command, stdout=sql_file, check=True)
        print(f"✅ Arquivo SQL gerado com sucesso: {output_sql}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar shp2pgsql: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
