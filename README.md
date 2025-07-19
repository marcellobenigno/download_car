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

- Download automático de arquivos SICAR por estado ou município.
- Processamento e limpeza de arquivos Shapefile.
- Filtragem de dados por código de município.
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
pip install git+https://github.com/urbanogilson/SICAR
```

## Instalação e Uso

* Crie um virtualenv com Python > 3.10.0;
* Ative o virtualenv;
* Instale as dependências do ambiente de desenvolvimento;

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install git+https://github.com/urbanogilson/SICAR
```

* Renomeie o arquivo `env-sample` para `.env`:

```
mv env-sample .env
```

Altere este arquivo, com as credenciais do Banco de Dados

## Como Usar

### Download por Estado

Para baixar dados de um estado específico, execute:

```sh
python download_car.py
```

O script irá solicitar:

1. **Sigla do estado** (ex: AC, SP, RJ)
2. **Código do município** (opcional)

Exemplo de execução:

```
Digite a sigla do estado (ex: AC, SP): AC
Digite o código do município (opcional, ex: 1200708): 
```

### Download por Município

Para baixar dados de um município específico, execute o mesmo comando e forneça o código do município:

```sh
python download_car.py
```

Exemplo de execução:

```
Digite a sigla do estado (ex: AC, SP): AC
Digite o código do município (opcional, ex: 1200708): 1200708
```

### Como obter o código do município

O código do município pode ser extraído do `cod_imovel` do CAR. Por exemplo:

- `cod_imovel`: AC-1200708-B71B52CEE3BB4E4E8AB40CDB6195DDC8
- `código do município`: 1200708

### Executando o Script Principal (Pipeline Completo)

Para rodar o pipeline completo de download, processamento e exportação:

```sh
python __init__.py
```

## Configuração e Execução

O script segue as seguintes etapas:

1. **Criação dos diretórios**: `sql/` e `shapefile/`.
2. **Solicitação do estado e município** (via prompt).
3. **Download do Shapefile** para o estado especificado.
4. **Processamento e limpeza do Shapefile**.
5. **Filtragem por município** (se código fornecido).
6. **Exportação dos dados para um arquivo SQL**.
7. **Inserção dos dados no Banco SIG-ITR**

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

### `process_shapefile(zip_file, output_path, municipality_code=None)`

Função para processamento do arquivo Shapefile, garantindo a limpeza dos dados.
Agora suporta filtragem por código de município através do parâmetro `municipality_code`.

### `export_sql(shapefile, output_sql)`

Converte o Shapefile para um script SQL usando `shp2pgsql`.

### `load_sql_data(state)`

Insere os dados do arquivo .sql gerado, removendo os antigos do banco usando `pgsql`.

## Exemplo de Saída

### Download por Estado

```
Digite a sigla do estado (ex: AC, SP): AC
Digite o código do município (opcional, ex: 1200708): 
📥 Baixando dados para: (AC)
Downloading polygon 'AREA_IMOVEL' for state 'AC': 100%|██████████| 14.4M/14.4M [00:02<00:00, 5.17MiB/s]
Download executado com sucesso para: State.AC
🛠 Processando shapefile para: AC
🔄 Lendo o arquivo: temp/AC_AREA_IMOVEL.zip
💾 Salvando Shapefile em: /home/user/data/shapefile/AC.shp
✅ Processamento concluído com sucesso para AC!
```

### Download por Município

```
Digite a sigla do estado (ex: AC, SP): AC
Digite o código do município (opcional, ex: 1200708): 1200708
📥 Baixando dados para: (AC)
Downloading polygon 'AREA_IMOVEL' for state 'AC': 100%|██████████| 14.4M/14.4M [00:02<00:00, 5.17MiB/s]
Download executado com sucesso para: State.AC
🛠 Processando shapefile para: AC
🔄 Lendo o arquivo: temp/AC_AREA_IMOVEL.zip
Filtro aplicado para o município: 1200708
💾 Salvando Shapefile em: /home/user/data/shapefile/AC.shp
✅ Processamento concluído com sucesso para AC!
```

## Contribuição

Sinta-se à vontade para abrir issues e enviar pull requests!

## Licença

Este projeto está sob a licença MIT.