import subprocess


def export_sql(shapefile, output_sql):
    """
        Converte um arquivo Shapefile para um script SQL usando shp2pgsql.

        Esta função executa o comando `shp2pgsql` para converter um arquivo `.shp`
        em um script SQL compatível com o PostgreSQL/PostGIS.

        Parâmetros:
            shapefile (str): Caminho do arquivo Shapefile de entrada (.shp).
            output_sql (str): Caminho do arquivo SQL de saída (.sql).

        Exemplo de uso:
            generate_sql("data/area_imovel.shp", "sql/area_imovel.sql")

        Observação:
            - O comando `shp2pgsql` precisa estar instalado e disponível no PATH do sistema.
            - A função assume que o banco de dados já possui a extensão PostGIS ativada.

    """
    command = [
        "shp2pgsql",
        "-a",  # Append
        "-s", "4326",
        "-t", "2D",
        shapefile,
        "maps_car",
        ">",  # Redirecionando a saída
        output_sql
    ]

    # Redireciona a saída para um arquivo SQL
    try:
        with open(output_sql, "w") as sql_file:
            subprocess.run(command, stdout=sql_file)
            print(f"Arquivo SQL gerado: {output_sql} ✅")
    except Exception as e:
        print(f'Erro na conversão do SHP para SQL: {e}')
