import subprocess


def export_sql(shapefile, output_sql):
    """
    Converte um arquivo Shapefile para um script SQL usando shp2pgsql.

    Parâmetros:
        shapefile (str): Caminho do arquivo Shapefile de entrada (.shp).
        output_sql (str): Caminho do arquivo SQL de saída (.sql).

    Requisitos:
        - O utilitário `shp2pgsql` deve estar instalado e acessível no PATH.
        - A extensão PostGIS já deve estar ativada no banco de dados.

    Exemplo de uso:
        export_sql("data/area_imovel.shp", "sql/area_imovel.sql")
    """
    command = [
        "shp2pgsql",
        "-a",  # Append mode (ou use -c para create table)
        "-s", "4326",  # SRID
        "-t", "2D",  # Tipo de geometria 2D
        shapefile,
        "maps_car"  # Nome da tabela destino no banco
    ]

    try:
        with open(output_sql, "w") as sql_file:
            subprocess.run(command, stdout=sql_file, check=True)
        print(f"✅ Arquivo SQL gerado com sucesso: {output_sql}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar shp2pgsql: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
