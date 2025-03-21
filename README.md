# Download CAR

## Descrição

Este projeto automatiza o download, processamento e exportação de dados do **SICAR**
(Sistema Nacional de Cadastro Ambiental Rural). Ele baixa arquivos no formato Shapefile,
realiza limpeza e conversão dos dados e os exporta em formato SQL para posterior inserção
no bancos de dados PostgreSQL/PostGIS do **SIG-ITR**.

## Estrutura do Projeto

```
download_car
├── LICENSE
├── README.md
├── __init__.py
├── download_car.py
├── env-sample
├── export_sql.py
├── load_sql_data.py
├── process_car.py
└── requirements.txt
```

## Funcionalidades

- Download automático de arquivos SICAR.
- Processamento e limpeza de arquivos Shapefile.
- Conversão para SQL com suporte ao PostgreSQL/PostGIS.
- Organização automática dos arquivos processados.

## Instalação

### Pré-requisitos

Certifique-se de ter instalado:

- Python >= 3.10.0
- PostgreSQL com PostGIS
- `shp2pgsql` instalado e configurado

### Dependências

Instale as dependências do projeto com:

```sh
pip install -r requirements.txt
```

## Instalação e Uso

* Crie um virtualenv com Python > 3.10.0;
* Ative o virtualenv;
* Instale as dependências do ambiente de desenvolvimento;

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

* Renomeie o arquivo `env-sample` para `.env`:

```
mv env-sample .env
```

Altere este arquivo, com as credenciais do Banco de Dados

### Executando o Script Principal

Para rodar o pipeline completo de download, processamento e exportação:

```sh
python __init__.py
```

## Configuração e Execução

O script segue as seguintes etapas:

1. **Criação dos diretórios**: `sql/` e `shapefile/`.
2. **Obtenção das datas de liberação dos dados**.
3. **Download do Shapefile**.
4. **Processamento e limpeza do Shapefile**.
5. **Exportação dos dados para um arquivo SQL**.
6. **Inserção dos dados no Banco SIG-ITR**

## Estrutura do Código

### `main()`

Função principal do pipeline que realiza:

- Download dos arquivos SICAR
- Processamento dos dados
- Exportação dos arquivos SQL
- Remoção dos dados antidos no Banco
- Inserção dos novos dados

### `download_car(state)`

Função para realização do download da base do CAR. Faz uso da biblioteca: 

[https://github.com/urbanogilson/SICAR](https://github.com/urbanogilson/SICAR)


### `process_shapefile(zip_file, output_path)`

Função para processamento do arquivo Shapefile, garantindo a limpeza dos dados.

### `export_sql(shapefile, output_sql)`

Converte o Shapefile para um script SQL usando `shp2pgsql`.

### `load_sql_data(state)`

Insere os dados do arquivo .sql gerado, removendo os antigos do banco usando `pgsql`.

## Exemplo de Saída

```
📥 Baixando dados para: (AC)
Downloading polygon 'AREA_IMOVEL' for state 'AC': 100%|██████████| 14.4M/14.4M [00:02<00:00, 5.17MiB/s]
Download executado com sucesso para: State.AC
🛠 Processando shapefile para: AC
🔄 Lendo o arquivo: temp/AC_AREA_IMOVEL.zip
💾 Salvando Shapefile em: /Users/marcellodebarrosfilho/code/download_car/shapefile/AC.shp
📤 Exportando para SQL: AC
Field num_area is an FTDouble with width 24 and precision 15
Field num_modulo is an FTDouble with width 24 and precision 15
Shapefile type: Polygon
Postgis type: MULTIPOLYGON[2]
Arquivo SQL gerado: /Users/marcellodebarrosfilho/code/download_car/sql/AC.sql ✅
✅ Processamento concluído com sucesso para AC!

🛠 Inserindo no banco os dados do estado: AC
 ️❌ Dados antigos removidos para o estado: AC. Registros removidos: 167565
✅ Inserção concluída para o estado: AC
```

## Contribuição

Sinta-se à vontade para abrir issues e enviar pull requests!

## Licença

Este projeto está sob a licença MIT.

