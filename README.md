# Criação de Script Python para criação de tabelas no PostgreSQL e o carregamento de dados provenientes de arquivos CSV

## 1. Sobre o projeto

Este projeto foi desenvolvido como parte do desafio técnico Lighthouse da Indicium Academy AI, com o objetivo de automatizar a criação de tabelas no PostgreSQL e o carregamento de dados provenientes de arquivos CSV.

A solução foi dividida em dois scripts Python:

- **gerar_schema.py**: analisa os arquivos CSV, infere os tipos de dados das colunas e gera o arquivo schema.sql, contendo os comandos CREATE TABLE.
- **carregar_dados.py**: conecta-se ao PostgreSQL e carrega os registros dos arquivos CSV nas respectivas tabelas.

A implementação prioriza a organização, a documentação, a reprodutibilidade e o cumprimento das premissas estabelecidas no desafio.

## 2. Objetivos

- Automatizar a criação do schema PostgreSQL a partir dos arquivos CSV.
- Inferir os tipos de dados das colunas.
- Padronizar os nomes de tabelas e colunas.
- Carregar os registros nas tabelas correspondentes.
- Preservar os arquivos CSV originais, sem transformações de negócio.
- Utilizar transações para controlar as operações de carga.
- Evitar o armazenamento de credenciais diretamente no código-fonte.

## 3. Tecnologias utilizadas

- **Python 3**: desenvolvimento dos scripts e processamento dos arquivos.
- **PostgreSQL**: banco de dados de destino.
- **Bibliotecas padrão do Python**: csv, os, re, datetime e sys.
- **psycopg2-binary**: conexão com o PostgreSQL e execução dos comandos SQL.
- **DBeaver**: ferramenta gráfica utilizada para conectar-se ao PostgreSQL, executar comandos SQL e consultar as tabelas.

O script de geração do schema utiliza somente bibliotecas padrão do Python. A biblioteca psycopg2-binary é necessária apenas para o carregamento dos dados.

## 4. Estrutura do projeto

```text
lighthouse/
|
+-- csv/
|   +-- addresses.csv
|   +-- customers.csv
|   +-- orders.csv
|   +-- ...
|
+-- gerar_schema.py
+-- schema.sql
+-- carregar_dados.py
+-- README.md
```

- **csv/**: diretório com os arquivos de origem.
- **gerar_schema.py**: script responsável pela geração do schema.
- **schema.sql**: arquivo SQL gerado automaticamente.
- **carregar_dados.py**: script responsável pela carga dos registros.
- **README.md**: documentação do projeto.

Cada arquivo CSV representa uma tabela. Por exemplo, orders.csv corresponde à tabela orders no schema desafio_lighthouse.

## 5. Premissas do desafio

### 5.1. Premissas da geração do schema

- Python 3.
- Utilização exclusiva de bibliotecas padrão do Python.
- Não utilização de pandas, numpy, polars, dask ou outras bibliotecas externas na geração do schema.
- Todos os arquivos CSV presentes no diretório de entrada são considerados fontes de dados.
- A estrutura das tabelas é inferida diretamente dos arquivos CSV.
- Os dados dos arquivos CSV não são alterados.
- O script gera somente o DDL (CREATE TABLE), sem realizar a carga dos dados.

### 5.2. Premissas do carregamento dos dados

- Todos os arquivos CSV presentes no diretório de entrada são considerados fontes de dados.
- O nome do arquivo determina o nome da tabela de destino.
- As tabelas devem ser criadas antes da execução do carregamento.
- Os dados originais não são modificados, corrigidos ou removidos.
- Campos vazios são convertidos em NULL no PostgreSQL.
- Os arquivos são processados em ordem alfabética.
- A senha do banco de dados é obtida por meio de uma variável de ambiente.
- Cada arquivo CSV é carregado dentro de uma transação própria.

## 6. Script 1 — Geração do schema PostgreSQL

### 6.1. Objetivo

O script gerar_schema.py analisa os arquivos CSV e gera um único arquivo SQL com os comandos necessários para criar as tabelas no PostgreSQL.

### 6.2. Principais etapas

1. Verifica a existência do diretório csv/.
2. Localiza e ordena os arquivos CSV.
3. Lê os cabeçalhos e os registros.
4. Normaliza os nomes das tabelas e colunas.
5. Infere os tipos de dados.
6. Gera os comandos CREATE TABLE.
7. Salva o resultado em schema.sql.

### 6.3. Inferência dos tipos de dados

Os tipos são definidos a partir dos valores encontrados nas colunas:

- **BOOLEAN**: valores booleanos reconhecidos pelo script.
- **DATE**: valores que representam datas em formatos suportados.
- **TIMESTAMP**: valores que representam data e hora em formatos suportados.
- **INTEGER**: números inteiros.
- **NUMERIC**: números que podem conter casas decimais.
- **TEXT**: valores textuais, colunas vazias ou conteúdos incompatíveis com os demais tipos.

Campos como CPF, CNPJ, telefone, CEP, SKU e códigos são tratados preferencialmente como TEXT, evitando a perda de zeros à esquerda.

### 6.4. Padronização dos nomes

Os nomes das tabelas e colunas são normalizados para letras minúsculas, com substituição de caracteres especiais por sublinhados.

Exemplos:

- Customer ID -> customer_id
- created-at -> created_at
- Nome Completo -> nome_completo

O script também considera o limite de 63 caracteres dos identificadores do PostgreSQL.

### 6.5. Limitações

O schema gerado representa uma estrutura inicial e não inclui automaticamente chaves primárias, chaves estrangeiras, índices ou restrições de unicidade. A inferência de tipos depende dos valores observados e deve ser revisada quando necessário.

## 7. Script 2 — Carregamento dos dados

### 7.1. Objetivo

O script carregar_dados.py realiza a inserção dos registros dos arquivos CSV nas tabelas previamente criadas no PostgreSQL.

### 7.2. Configuração do banco

- **SGBD:** PostgreSQL
- **Host:** localhost
- **Porta:** 5432
- **Database:** postgres
- **Usuário:** postgres
- **Schema:** desafio_lighthouse

Esses parâmetros devem ser ajustados caso o ambiente utilize outras configurações.

### 7.3. Segurança das credenciais

A senha não fica armazenada diretamente no código. Ela é obtida por meio da variável de ambiente LIGHTHOUSE_DB_PASSWORD.

No PowerShell, execute:

```powershell
$env:LIGHTHOUSE_DB_PASSWORD = "SUA_SENHA"
```

Substitua SUA_SENHA pela senha válida do usuário PostgreSQL configurado.

### 7.4. Principais etapas

1. Valida o diretório de entrada e a variável de ambiente da senha.
2. Localiza e ordena os arquivos CSV.
3. Estabelece a conexão com o PostgreSQL.
4. Verifica a existência de cada tabela de destino.
5. Lê os cabeçalhos e os registros dos arquivos.
6. Executa os comandos INSERT.
7. Confirma a transação ao concluir cada arquivo.
8. Exibe o resumo da execução e encerra a conexão.

### 7.5. Tratamento de campos vazios

Campos vazios são convertidos de "" para None em Python, que o psycopg2 representa como NULL no PostgreSQL.

Não são realizadas limpezas, correções de inconsistências ou transformações de negócio.

### 7.6. Transações e erros

- **COMMIT**: confirma as inserções após a leitura completa do arquivo.
- **ROLLBACK**: desfaz as inserções da transação atual quando ocorre um erro.
- **Interrupção**: impede que os arquivos seguintes sejam carregados após uma falha.
- **Encerramento**: fecha a conexão com o PostgreSQL ao final do processo.

Como cada arquivo possui sua própria transação, tabelas carregadas anteriormente podem permanecer preenchidas mesmo que ocorra uma falha em um arquivo posterior.

## 8. Instalação e execução

### 8.1. Instalar a dependência

O script de geração não exige bibliotecas externas. Para executar o carregamento, instale o driver PostgreSQL:

```bash
python -m pip install psycopg2-binary
```

### 8.2. Gerar o schema

Na raiz do projeto, execute:

```bash
python gerar_schema.py
```

O arquivo schema.sql será gerado automaticamente.

### 8.3. Criar as tabelas

Certifique-se de que o schema desafio_lighthouse existe no banco de dados. Caso necessário, crie-o:

```sql
CREATE SCHEMA desafio_lighthouse;
```

Em seguida, execute o arquivo SQL:

```bash
psql -h localhost -p 5432 -U postgres -d postgres -f schema.sql
```

### 8.4. Configurar a senha

No PowerShell, defina a variável de ambiente:

```powershell
$env:LIGHTHOUSE_DB_PASSWORD = "SUA_SENHA"
```

### 8.5. Carregar os dados

Execute:

```bash
python carregar_dados.py
```

O script iniciará a conexão, processará os arquivos e exibirá o total de registros carregados.

## 9. Decisões técnicas

- **Separação de responsabilidades**: um script gera a estrutura e outro carrega os dados.
- **Modularização**: as funções dividem o processamento em etapas específicas, facilitando manutenção e testes.
- **Reprodutibilidade**: a ordenação alfabética mantém uma sequência de execução previsível.
- **Segurança**: a senha é obtida por variável de ambiente e os valores SQL são enviados por parâmetros.
- **Confiabilidade**: a existência das tabelas é verificada antes da carga e cada arquivo possui controle transacional.
- **Documentação**: os scripts incluem comentários, descrições das funções e mensagens de acompanhamento.

## 10. Limitações e pontos de atenção

- A inferência automática de tipos pode exigir revisão em formatos não reconhecidos.
- Nomes distintos podem resultar no mesmo identificador após a normalização.
- O gerador e o carregador utilizam conjuntos diferentes de delimitadores CSV.
- O gerador normaliza os nomes das colunas, mas o carregador utiliza os cabeçalhos originais. Isso pode causar incompatibilidade entre os INSERT e as tabelas criadas.
- A execução repetida do carregador pode duplicar registros, pois não há limpeza prévia das tabelas.
- A ordem alfabética não considera dependências entre tabelas.
- A inserção é realizada registro a registro, podendo ser lenta para grandes volumes.
- As transações são independentes por arquivo e não garantem rollback global.

## 11. Possíveis melhorias

- Implementar testes automatizados para as funções de leitura e inferência de tipos.
- Padronizar a normalização dos nomes de colunas nos dois scripts.
- Tratar colisões de nomes gerados durante a normalização.
- Implementar carga em lote ou utilizar COPY para melhorar o desempenho.
- Criar uma estratégia para evitar duplicações em reexecuções.
- Definir uma ordem de carga baseada nas dependências entre tabelas.
- Implementar validações adicionais de tipos e integridade referencial.
- Adicionar logs estruturados e relatórios de execução.

## 12. Considerações finais

A solução automatiza a criação de tabelas e o carregamento de dados no PostgreSQL a partir de arquivos CSV, mantendo as responsabilidades separadas e documentadas.

O primeiro script reduz o trabalho manual de criação do schema, enquanto o segundo organiza a inserção dos registros com validações básicas, controle transacional e tratamento de erros.

A implementação atende à proposta de automatização do desafio e estabelece uma base que pode ser aprimorada para cenários com maiores exigências de desempenho, integridade e validação dos dados.

**Fluxo geral do projeto:**

```text
Arquivos CSV
     |
     v
gerar_schema.py
     |
     v
schema.sql
     |
     v
Criação das tabelas no PostgreSQL
     |
     v
carregar_dados.py
     |
     v
Dados carregados no schema desafio_lighthouse
```
