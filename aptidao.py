"""
Script para processar dados de aptidão agrícola
Realiza clip de geometrias com grade, análise espacial e exportação de dados
"""

import argparse
import gc  # Importa o módulo garbage collector para gerenciamento de memória
import os
import re

import geopandas as gpd
from decouple import config
from sqlalchemy import create_engine

IBGE_CODE_RE = re.compile(r"^\d{7}$")


def _validate_cod_ibge_m(cod_ibge_m):
    """Valida o código IBGE de município antes de usá-lo em SQL (evita SQL injection)."""
    if not IBGE_CODE_RE.match(str(cod_ibge_m)):
        raise ValueError(f"Código IBGE de município inválido: {cod_ibge_m}")

# =============================================================================
# CONFIGURAÇÕES E CONEXÃO COM BANCO DE DADOS
# =============================================================================

def setup_database_connection():
    """
    Configura e retorna a conexão com o banco de dados.
    """
    # É fundamental que a variável de ambiente 'DB_CONNECTION_URL' 
    # esteja configurada no seu ambiente (.env file ou similar).
    DATABASE_URL = config('DB_CONNECTION_URL') 
    return create_engine(DATABASE_URL)


# =============================================================================
# FUNÇÕES DE CONSULTA AO BANCO
# =============================================================================

def get_aptidao_data(engine, cod_ibge_m):
    """
    Busca dados de aptidão agrícola para um município específico.
    
    Args:
        engine: Conexão SQLAlchemy com o banco.
        cod_ibge_m: Código IBGE do município.
    
    Returns:
        GeoDataFrame com dados de aptidão.
    """
    _validate_cod_ibge_m(cod_ibge_m)
    sql_aptidao = f"""
        SELECT descricao, val, cor, 
               cod_ibge_m, cod_ibge_e, ano, 
               ST_MakeValid(geom) AS geom 
        FROM maps_aptidao 
        WHERE cod_ibge_m = '{cod_ibge_m}'
    """
    return gpd.read_postgis(sql_aptidao, engine, geom_col='geom')


def get_grade_data(engine, cod_ibge_m):
    """
    Busca dados da grade 10000 que intersectam com a área de aptidão.
    
    Args:
        engine: Conexão SQLAlchemy com o banco.
        cod_ibge_m: Código IBGE do município.
    
    Returns:
        GeoDataFrame com dados da grade.
    """
    _validate_cod_ibge_m(cod_ibge_m)
    sql_grade = f"""
        SELECT DISTINCT id AS grade_id, geom 
        FROM maps_grade10000
        WHERE geom && (
            SELECT ST_Extent(geom)::geometry 
            FROM maps_aptidao 
            WHERE cod_ibge_m = '{cod_ibge_m}'
        )
    """
    return gpd.read_postgis(sql_grade, engine, geom_col='geom')


# =============================================================================
# FUNÇÕES DE PROCESSAMENTO ESPACIAL
# =============================================================================

def clip_aptidao_with_grade(aptidao_df, grade_df):
    """
    Realiza o clip (intersecção) entre aptidão e grade.
    
    Args:
        aptidao_df: GeoDataFrame com dados de aptidão.
        grade_df: GeoDataFrame com dados da grade.
    
    Returns:
        GeoDataFrame com resultado do clip.
    """
    return aptidao_df.overlay(grade_df, how='intersection', keep_geom_type=False)


# =============================================================================
# FUNÇÕES DE EXPORTAÇÃO
# =============================================================================

def export_to_shapefile(gdf, output_path, filename):
    """
    Exporta GeoDataFrame para formato Shapefile.
    
    Args:
        gdf: GeoDataFrame a ser exportado.
        output_path: Diretório de destino.
        filename: Nome do arquivo (sem extensão).
    """
    # Cria o diretório de saída se ele não existir
    os.makedirs(output_path, exist_ok=True)
    filepath = os.path.join(output_path, f"{filename}.shp")
    gdf.to_file(filepath, driver='ESRI Shapefile', encoding='utf-8')
    print(f"✓ Shapefile exportado: {filepath}")


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def process_municipality(cod_ibge_m, output_base_path):
    """
    Processa todos os dados de aptidão para um município específico.
    
    Args:
        cod_ibge_m: Código IBGE do município.
        output_base_path: Diretório base para exportação.
    """
    aptidao_clip = None # Inicializa a variável para garantir que exista no bloco finally
    
    try:
        print(f"\n{'='*60}")
        print(f"Processando dados de aptidão para o município: {cod_ibge_m}")
        print(f"{'='*60}\n")
        
        # 1. Conecta ao banco de dados
        print("1. Conectando ao banco de dados...")
        engine = setup_database_connection()
        
        # 2. Carrega dados de aptidão
        print("2. Carregando dados de aptidão...")
        aptidao_df = get_aptidao_data(engine, cod_ibge_m)
        print(f"    → {len(aptidao_df)} registros de aptidão carregados")

        if aptidao_df.empty:
            print(f"!!! Atenção: Não foram encontrados dados de aptidão para {cod_ibge_m}. Pulando...")
            return None # Retorna antes de carregar o resto
        
        # 3. Carrega dados da grade
        print("3. Carregando dados da grade (10000m)...")
        grade_df = get_grade_data(engine, cod_ibge_m)
        print(f"    → {len(grade_df)} grades carregadas")

        if grade_df.empty:
            print(f"!!! Atenção: Não foram encontradas grades para a extensão de {cod_ibge_m}. Pulando...")
            # Limpa o que foi carregado antes de retornar
            del aptidao_df 
            gc.collect()
            return None
        
        # 4. Realiza clip (intersecção) de aptidão com grade
        print("4. Realizando clip de aptidão com grade...")
        aptidao_clip = clip_aptidao_with_grade(aptidao_df, grade_df)
        print(f"    → {len(aptidao_clip)} polígonos resultantes do clip")
        
        # 5. Exporta resultados
        print("\n5. Exportando resultados...")
        
        # Exporta aptidão clipped
        export_to_shapefile(
            aptidao_clip, 
            output_base_path, 
            f'maps_aptidao_clip_{cod_ibge_m}'
        )
        
        print(f"\n{'='*60}")
        print(f"✓ Processamento para {cod_ibge_m} concluído com sucesso!")
        print(f"{'='*60}\n")
        
        # O retorno é mantido apenas por convenção, mas o foco principal é a exportação
        return {'aptidao_clip': aptidao_clip}

    except Exception as e:
        print(f"\n!!! ERRO FATAL ao processar {cod_ibge_m}: {e}")
        print(f"{'='*60}\n")
        return None
        
    finally:
        # 6. Limpeza de memória (para liberar recursos para o próximo município)
        print("6. Liberando memória...")
        try:
            # Remove os grandes GeoDataFrames que não serão mais usados
            del aptidao_df
        except NameError:
            pass # Ignora se a variável não foi definida devido a erro ou pulo
        
        try:
            del grade_df
        except NameError:
            pass
            
        if aptidao_clip is not None:
             del aptidao_clip # O resultado final também pode ser grande
        
        try:
            del engine # Remove a referência à conexão
        except NameError:
            pass
            
        # Força o coletor de lixo a rodar e liberar a memória
        gc.collect() 
        print("    → Memória liberada.")





# =============================================================================
# EXECUÇÃO DO SCRIPT PARA A LISTA DE MUNICÍPIOS
# =============================================================================

def load_municipality_codes(path):
    """Lê códigos IBGE de município de um arquivo texto, um código por linha."""
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Processa dados de aptidão agrícola (clip com grade) para uma lista de municípios."
    )
    parser.add_argument(
        "--codigos", "-c",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "municipios_aptidao.txt"),
        help="Arquivo com códigos IBGE de municípios, um por linha (padrão: municipios_aptidao.txt)."
    )
    parser.add_argument(
        "--saida", "-o",
        default=os.path.join(os.getcwd(), "temp", "aptidao"),
        help="Diretório de saída para os Shapefiles gerados (padrão: ./temp/aptidao)."
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    cod_ibge_m_list = load_municipality_codes(args.codigos)
    OUTPUT_PATH = args.saida

    # Loop de processamento
    for cod_ibge in cod_ibge_m_list:
        process_municipality(cod_ibge, OUTPUT_PATH)

    print("\n\n#####################################################")
    print(f"Processamento em lote finalizado para {len(cod_ibge_m_list)} municípios.")
    print(f"Verifique os Shapefiles em: {OUTPUT_PATH}")
    print("#####################################################")