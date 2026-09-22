# Download CAR

## Descrição do Projeto

Este projeto Python foi desenvolvido para automatizar o processo de download, processamento e exportação de dados do
Sistema Nacional de Cadastro Ambiental Rural (SICAR) e das bases de certificação de imóveis do INCRA (SIGEF e SNCI). Ele é capaz de baixar arquivos Shapefile por estado, realizar a
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
├── download_incra.py       # Download dos shapefiles SIGEF/SNCI do INCRA por UF
├── process_incra.py        # Processamento dos shapefiles SIGEF/SNCI (interseção com municípios)
├── municipios.py           # Consulta os municípios com prefeitura ativa, suas geometrias e contagens
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
   DB_TABLE_SIGEF=maps_incrasigef
   DB_TABLE_SNCI=maps_incrasnci
   ```
   Certifique-se de que o usuário do banco de dados tem permissões adequadas para criar tabelas e inserir/deletar dados
   na base de dados especificada. `DB_TABLE`, `DB_TABLE_SIGEF` e `DB_TABLE_SNCI` são opcionais e definem as tabelas de
   destino (padrões: `maps_car`, `maps_incrasigef` e `maps_incrasnci`).

## Como Usar

A atualização é feita apenas nos **municípios com prefeitura ativa**, obtidos do próprio banco de destino:

```sql
SELECT m.*
FROM maps_municipio m
INNER JOIN prefeitura_prefeitura p ON p.municipio_id = m.id
WHERE p.ativo = TRUE;
```

Os estados processados são os que possuem ao menos um desses municípios. Os demais municípios não são alterados nas
tabelas de destino.

### Bases disponíveis

| Fonte   | Origem                                          | Tabela (variável / padrão)                 | Como o município é identificado              |
|---------|-------------------------------------------------|--------------------------------------------|----------------------------------------------|
| `car`   | SICAR (biblioteca `SICAR`)                      | `DB_TABLE` / `maps_car`                    | código IBGE extraído de `cod_imovel`         |
| `sigef` | `certificacao.incra.gov.br/csv_shp/zip/`        | `DB_TABLE_SIGEF` / `maps_incrasigef`       | interseção com `maps_geometriamunicipio`     |
| `snci`  | `certificacao.incra.gov.br/csv_shp/zip/`        | `DB_TABLE_SNCI` / `maps_incrasnci`         | interseção com `maps_geometriamunicipio`     |

O INCRA só publica o shapefile da UF inteira, sem código de município confiável. Por isso, cada imóvel do SIGEF/SNCI é
gravado para cada município com prefeitura ativa cuja geometria ele intersecta (um imóvel na divisa aparece nos dois
municípios). Municípios com prefeitura ativa sem geometria cadastrada são ignorados no SIGEF/SNCI.

### Exemplos

```bash
python main.py                              # CAR de todos os estados com prefeitura ativa
python main.py --fonte car,sigef,snci       # as três bases (também aceita separadas por espaço)
python main.py MT,SP --fonte sigef snci     # SIGEF e SNCI apenas de MT e SP
```

Sem `--fonte`, apenas o CAR é atualizado. O argumento de estados é opcional (estados sem prefeitura ativa são ignorados).

### Fluxo de Execução do Pipeline

Ao executar `main.py`, o script consulta os municípios com prefeitura ativa e segue as seguintes etapas para cada fonte
e estado:

1. **Download**: Baixa o ZIP da UF para `temp/zip/`. O arquivo é reaproveitado por até **2 dias**; depois disso (ou se
   estiver corrompido) é baixado novamente. Downloads do INCRA são tentados até 3 vezes.
2. **Processamento**: O shapefile é lido, reprojetado para EPSG:4326, as geometrias são corrigidas (2D, inválidas
   reparadas com `buffer(0)`, convertidas para MultiPolygon) e os registros são filtrados para os municípios com
   prefeitura ativa.
3. **Comparação**: Para cada município, a quantidade de registros baixados é comparada com a quantidade já existente na
   tabela. **Se forem iguais, o município é considerado atualizado e não é regravado.** Se todos os municípios da UF
   estiverem atualizados, as etapas seguintes são puladas.
4. **Exportação para SQL**: Os registros dos municípios a atualizar são salvos em `temp/shapefile/` e convertidos para
   `temp/sql/` com `shp2pgsql`.
5. **Carregamento no Banco de Dados**: Numa **única transação**, os registros antigos desses municípios são removidos e
   os novos inseridos (no SIGEF/SNCI, `criado`/`modificado` são preenchidos). Se qualquer comando falhar, nada é
   alterado.

## Estrutura do Código e Módulos

O projeto é modularizado para facilitar a compreensão e manutenção:

- `main.py`: Orquestra o fluxo: consulta os municípios com prefeitura ativa e, para cada fonte e estado, chama
  `update_car` ou `update_incra`. `select_outdated` compara as contagens da fonte e da base por município.
- `download_car.py`: Cria a estrutura de diretórios e baixa os Shapefiles do SICAR (biblioteca `SICAR`).
    - `create_directories(base_path)`: Cria os diretórios `sql`, `shapefile` e `zip`.
    - `get_car_zip_path(state, temp_path)`: Caminho do ZIP da UF em cache.
    - `download_car(state, zip_path)`: Baixa o Shapefile da UF, reaproveitando o cache de até 2 dias.
- `download_incra.py`: Baixa os Shapefiles SIGEF/SNCI da UF do INCRA.
    - `download_incra(fonte, uf, zip_dir)`: Baixa o ZIP (com cache de 2 dias e até 3 tentativas).
- `process_car.py`: Processamento e limpeza do Shapefile do CAR.
    - `extract_cod_ibge_m(cod_imovel)` / `extract_cod_ibge_e(cod_ibge_m)`: Extraem os códigos IBGE.
    - `clean_geometry(geom)` / `ensure_polygon(geom)`: Limpam e validam geometrias.
    - `read_car_shapefile(zip_file, output_crs=4326, municipios=None)`: Lê, filtra pelos municípios e limpa o Shapefile.
    - `save_shapefile(car, output_file)`: Salva o resultado.
- `process_incra.py`: Processamento dos Shapefiles SIGEF/SNCI.
    - `process_incra_shapefile(zip_path, fonte, municipios_gdf)`: Lê a área dos municípios, corrige geometrias,
      normaliza os campos e atribui cada imóvel aos municípios que ele intersecta.
- `export_sql.py`: `export_sql(shapefile, output_sql, table)` executa o `shp2pgsql` para gerar o arquivo SQL.
- `load_sql_data.py`: `load_sql_data(state, sql_path, municipios, table, column, timestamps)` remove os registros dos
  municípios informados e insere os novos numa única transação, usando `psql`.
- `municipios.py`: Consultas ao banco de destino.
    - `get_active_municipalities()`: Códigos IBGE dos municípios com prefeitura ativa, agrupados por UF.
    - `get_active_municipality_geometries()`: Geometrias desses municípios (`maps_geometriamunicipio`).
    - `count_records_by_municipality(table, column, municipios)`: Quantidade atual de registros por município.

## Exemplos de Saída

```
$ python main.py PB,RO --fonte car sigef
4 município(s) com prefeitura ativa em 2 estado(s): PB, RO

>>> CAR - estado: PB (3 município(s) com prefeitura ativa)
✅ Arquivo já existe: temp/zip/PB_AREA_IMOVEL.zip (baixado há 0h, validade de 2 dias)
Arquivo descompactado em: temp/unzipped/PB
🔄 Lendo o arquivo: temp/unzipped/PB/AREA_IMOVEL_1.shp
🔎 2803 registro(s) pertencem aos 3 município(s) selecionado(s)
   2501104: 1525 imóvel(is), mesma quantidade da fonte. Nenhuma atualização necessária.
   2507507: 240 imóvel(is), mesma quantidade da fonte. Nenhuma atualização necessária.
   2513703: 1038 imóvel(is), mesma quantidade da fonte. Nenhuma atualização necessária.
✅ CAR de PB já está atualizado.

>>> SIGEF - estado: RO (1 município(s) com prefeitura ativa)
📥 Baixando SIGEF de RO: https://certificacao.incra.gov.br/csv_shp/zip/Sigef%20Brasil_RO.zip
⬇️ Download concluído: temp/zip/SIGEF_RO.zip
🔄 Lendo o arquivo: temp/zip/SIGEF_RO.zip
   4056 registro(s) na área dos municípios selecionados
🔎 1345 registro(s) intersectam os 1 município(s) selecionado(s)
   1100304: 1335 imóvel(is) na base, 1345 na fonte. Será atualizado.
💾 Salvando Shapefile em: temp/shapefile/SIGEF_RO.shp
✅ Arquivo SQL gerado com sucesso: temp/sql/SIGEF_RO.sql
Substituindo registros de 1 município(s) de RO em maps_incrasigef a partir de temp/sql/SIGEF_RO.sql...
✅ Dados de RO atualizados em maps_incrasigef
```

## Testes

Os testes (pytest) cobrem o processamento dos shapefiles (com arquivos sintéticos), o cache e as novas tentativas dos
downloads, a comparação de contagens por município, a montagem dos comandos `psql` e a orquestração de `main.py`. A
rede e o banco são simulados, então rodam sem acesso ao SICAR, ao INCRA ou ao PostgreSQL:

```bash
pytest tests/ -v
```

O teste de integração `tests/test_integration_postgis.py` usa um PostgreSQL/PostGIS real: cria um banco temporário,
exporta com `shp2pgsql`, carrega com `psql` e verifica datas, `criado`/`modificado` e o rollback em caso de erro. Ele é
ignorado por padrão; para rodar, use credenciais (`.env`) de um usuário que possa criar bancos:

```bash
TEST_POSTGIS=1 pytest tests/test_integration_postgis.py -v
```

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir *issues* para relatar bugs ou sugerir melhorias, e enviar
*pull requests* com novas funcionalidades ou correções.

## Licença

Este projeto está licenciado sob a Licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.

