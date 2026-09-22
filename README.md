# Download CAR

## Descrição do Projeto

Este projeto Python foi desenvolvido para automatizar o processo de download, processamento e exportação de dados do
Sistema Nacional de Cadastro Ambiental Rural (SICAR). Ele é capaz de baixar arquivos Shapefile por estado, realizar a
limpeza e conversão dos dados geográficos e atributos, e exportá-los em formato SQL otimizado para inserção em bancos de
dados PostgreSQL/PostGIS, especificamente para o Sistema de Informações Geográficas do Imposto Territorial Rural (
SIG-ITR).

## Estrutura do Projeto

```
. (raiz do projeto)
├── LICENSE
├── README.md
├── main.py                 # Ponto de entrada principal do pipeline
├── download_car.py         # Lógica para download de dados do SICAR
├── export_sql.py           # Lógica para exportar Shapefiles para SQL
├── load_sql_data.py        # Lógica para carregar dados SQL no PostgreSQL/PostGIS
├── process_car.py          # Lógica para processamento e limpeza de Shapefiles
├── aptidao.py               # Script para processamento de dados de aptidão agrícola por município
├── municipios_aptidao.txt   # Lista de códigos IBGE de município usada por aptidao.py
├── tests/                   # Testes unitários (pytest)
├── requirements.txt        # Dependências do Python
├── .env-sample             # Exemplo de arquivo de variáveis de ambiente
└── temp/
    ├── sql/                # Diretório para arquivos SQL gerados
    ├── shapefile/          # Diretório para Shapefiles processados
    └── zip/                # Diretório para arquivos ZIP baixados
```

## Funcionalidades Principais

- **Download Automatizado**: Baixa arquivos SICAR (Shapefiles) por estado, utilizando a biblioteca `SICAR`.
- **Processamento de Shapefiles**: Realiza a limpeza e padronização de dados geográficos e atributos, incluindo a
  correção de geometrias inválidas e a extração de códigos IBGE.
- **Filtragem de Dados**: Suporta filtragem opcional por código de município durante o processamento.
- **Exportação para SQL**: Converte os Shapefiles processados para o formato SQL, utilizando `shp2pgsql`, com suporte a
  PostgreSQL/PostGIS.
- **Gerenciamento de Banco de Dados**: Insere os dados SQL no banco de dados de destino, com funcionalidade para remover
  registros antigos antes da inserção de novos dados, garantindo a atualização contínua.
- **Estrutura Modular**: Código organizado em módulos para facilitar a manutenção e escalabilidade.

## Instalação e Configuração

### Pré-requisitos

Certifique-se de ter os seguintes softwares instalados e configurados em seu ambiente:

- **Python**: Versão 3.10.0 ou superior.
- **PostgreSQL com PostGIS**: Um servidor PostgreSQL com a extensão PostGIS instalada e configurada para lidar com dados
  geoespaciais.
- **`shp2pgsql`**: Ferramenta de linha de comando que geralmente acompanha a instalação do PostGIS, utilizada para
  converter Shapefiles em comandos SQL para PostgreSQL.
- **`psql`**: Cliente de linha de comando do PostgreSQL, utilizado para interagir com o banco de dados.

### Configuração do Ambiente

1. **Clone o Repositório** (se aplicável):
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd download_car
   ```

2. **Crie e Ative um Ambiente Virtual**:
   É altamente recomendável usar um ambiente virtual para gerenciar as dependências do projeto.
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # No Linux/macOS
   # .venv\Scripts\activate   # No Windows (CMD)
   # .venv\Scripts\Activate.ps1 # No Windows (PowerShell)
   ```

3. **Instale as Dependências Python**:
   Instale todas as bibliotecas Python necessárias listadas no arquivo `requirements.txt`.
   ```bash
   pip install -r requirements.txt
   ```
   Além disso, este projeto utiliza uma biblioteca específica do SICAR que pode precisar ser instalada diretamente do
   GitHub:
   ```bash
   pip install git+https://github.com/urbanogilson/SICAR
   ```

4. **Configure as Variáveis de Ambiente**:
   Renomeie o arquivo `.env-sample` para `.env` e preencha as credenciais do seu banco de dados.
   ```bash
   mv .env-sample .env
   ```
   Edite o arquivo `.env` com as seguintes informações:
   ```ini
   DB_HOST=seu_host_do_banco
   DB_USER=seu_usuario_do_banco
   DB_NAME=seu_nome_do_banco
   DB_PASSWORD=sua_senha_do_banco
   DB_TABLE=maps_car
   ```
   Certifique-se de que o usuário do banco de dados tem permissões adequadas para criar tabelas e inserir/deletar dados
   na base de dados especificada. `DB_TABLE` é opcional (padrão: `maps_car`) e define a tabela de destino usada por
   `export_sql.py` e `load_sql_data.py`.

## Como Usar

O projeto pode ser executado de duas formas principais: interativamente ou via linha de comando, permitindo o download e
processamento de dados para um ou múltiplos estados.

### Execução Interativa (para um ou múltiplos estados)

Para iniciar o pipeline completo de download, processamento e exportação de forma interativa, execute o
script `main.py`:

```bash
python main.py
```

O script solicitará que você digite as siglas dos estados desejados, separadas por vírgula (ex: `AC, SP, MG`).

```
Digite a sigla dos estados separados por vírgula (ex: AC, SP, MG): AC, SP
```

### Execução via Linha de Comando (para um ou múltiplos estados)

Você pode passar as siglas dos estados diretamente como um argumento para o script `main.py`:

```bash
python main.py AC,SP,RJ
```

Neste exemplo, o script processará os dados para os estados do Acre (AC), São Paulo (SP) e Rio de Janeiro (RJ)
sequencialmente.

### Fluxo de Execução do Pipeline

Ao executar `main.py`, o script seguirá as seguintes etapas para cada estado especificado:

1. **Criação de Diretórios**: Garante que os diretórios `temp/sql/`, `temp/shapefile/` e `temp/zip/` existam para
   armazenar os arquivos intermediários.
2. **Download do Shapefile**: Baixa o arquivo ZIP do SICAR para o estado atual, salvando-o em `temp/zip/`.
3. **Descompactação**: O arquivo ZIP é descompactado em um diretório temporário dentro de `temp/unzipped/`.
4. **Processamento do Shapefile**: O arquivo `.shp` descompactado é lido, limpo (geometrias inválidas são corrigidas,
   colunas são padronizadas) e salvo em `temp/shapefile/`.
5. **Exportação para SQL**: O Shapefile processado é convertido para um arquivo `.sql` usando `shp2pgsql`, que é salvo
   em `temp/sql/`.
6. **Carregamento no Banco de Dados**: Os dados do arquivo `.sql` são carregados no banco de dados PostgreSQL/PostGIS.
   Antes da inserção, os registros antigos correspondentes ao estado são removidos para evitar duplicidade e garantir a
   atualização dos dados.

## Estrutura do Código e Módulos

O projeto é modularizado para facilitar a compreensão e manutenção:

- `main.py`: O script principal que orquestra o fluxo de trabalho, chamando as funções dos outros módulos em sequência.
- `download_car.py`: Contém funções para criar a estrutura de diretórios necessária e realizar o download dos Shapefiles
  do SICAR. Utiliza a biblioteca `SICAR` para interagir com a API do SICAR.
    - `create_directories(base_path)`: Cria os diretórios `sql`, `shapefile` e `zip`.
    - `get_dated_filename(state, temp_path)`: Gera um nome de arquivo único com base na data para o ZIP baixado.
    - `download_car(state, dated_zip_path)`: Realiza o download do Shapefile para o estado especificado.
- `process_car.py`: Responsável pelo processamento e limpeza dos dados do Shapefile.
    - `extract_cod_ibge_m(cod_imovel)`: Extrai o código IBGE do município.
    - `extract_cod_ibge_e(cod_ibge_m)`: Extrai o código IBGE do estado.
    - `clean_geometry(geom)`: Limpa e valida geometrias.
    - `ensure_polygon(geom)`: Garante que a geometria seja um polígono.
    - `process_shapefile(zip_file, output_file, output_crs=4326)`: Função principal de processamento, lendo, limpando e
      salvando o Shapefile.
- `export_sql.py`: Lida com a conversão do Shapefile processado para um arquivo SQL.
    - `export_sql(shapefile, output_sql)`: Executa o comando `shp2pgsql` para gerar o arquivo SQL.
- `load_sql_data.py`: Gerencia a inserção dos dados SQL no banco de dados PostgreSQL/PostGIS.
    - `load_sql_data(state, sql_path)`: Conecta-se ao banco de dados e executa comandos `DELETE` (para registros
      antigos) e `INSERT` (para novos dados) usando `psql`.

## Exemplos de Saída

### Execução para Múltiplos Estados

```
Digite a sigla dos estados separados por vírgula (ex: AC, SP, MG): AC, SP

>>> Processando estado: AC
✅ Arquivo já existe: temp/zip/AC_AREA_IMOVEL_22072025.zip
Arquivo baixado e salvo em: temp/zip/AC_AREA_IMOVEL_22072025.zip
Arquivo descompactado em: temp/unzipped/AC
🔄 Lendo o arquivo: temp/unzipped/AC/CAR_AC.shp
💾 Salvando Shapefile em: temp/shapefile/AC.shp
✅ Processamento concluído com sucesso para temp/shapefile/AC.shp!
✅ Arquivo SQL gerado com sucesso: temp/sql/AC.sql
Executando DELETE para o estado AC...
✅ Registros antigos de AC excluídos com sucesso (ou nenhum encontrado para a condição).
Inserindo dados via psql para o estado: AC a partir de temp/sql/AC.sql
✅ Dados inseridos via psql para o estado: AC

>>> Processando estado: SP
📥 Baixando dados para: SP
Downloading polygon 'AREA_IMOVEL' for state 'SP': 100%|██████████| 14.4M/14.4M [00:02<00:00, 5.17MiB/s]
⬇️ Download executado e renomeado para: temp/zip/SP_AREA_IMOVEL_22072025.zip
Arquivo baixado e salvo em: temp/zip/SP_AREA_IMOVEL_22072025.zip
Arquivo descompactado em: temp/unzipped/SP
🔄 Lendo o arquivo: temp/unzipped/SP/CAR_SP.shp
💾 Salvando Shapefile em: temp/shapefile/SP.shp
✅ Processamento concluído com sucesso para temp/shapefile/SP.shp!
✅ Arquivo SQL gerado com sucesso: temp/sql/SP.sql
Executando DELETE para o estado SP...
✅ Registros antigos de SP excluídos com sucesso (ou nenhum encontrado para a condição).
Inserindo dados via psql para o estado: SP a partir de temp/sql/SP.sql
✅ Dados inseridos via psql para o estado: SP
```

## Testes

O projeto possui testes unitários (pytest) para as funções puras de processamento em `process_car.py`. Para
executá-los:

```bash
pip install pytest  # já incluído em requirements.txt
pytest tests/ -v
```

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir *issues* para relatar bugs ou sugerir melhorias, e enviar
*pull requests* com novas funcionalidades ou correções.

## Licença

Este projeto está licenciado sob a Licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.

