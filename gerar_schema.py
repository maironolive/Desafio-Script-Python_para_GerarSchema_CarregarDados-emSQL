"""
===============================================================================
GERADOR AUTOMÁTICO DE SCHEMA POSTGRESQL A PARTIR DE ARQUIVOS CSV
===============================================================================

Projeto:
    Lighthouse - Desafio Técnico / Indicium Academy AI

Objetivo:
    Ler todos os arquivos CSV existentes em um diretório de entrada e gerar
    automaticamente um único arquivo SQL contendo os comandos CREATE TABLE
    necessários para criar as tabelas correspondentes no PostgreSQL.

Premissas:
    - Python 3
    - Somente bibliotecas padrão do Python
    - Não utiliza pandas, numpy, polars, dask ou outras bibliotecas externas
    - Todos os CSVs presentes no diretório de entrada são considerados fontes
    - A estrutura das tabelas é inferida diretamente dos arquivos CSV
    - Os dados dos CSVs não são alterados
    - O script gera somente o DDL (CREATE TABLE)

Estrutura esperada do projeto:

    lighthouse/
    |
    +-- gerar_schema.py
    |
    +-- csv/
    |   +-- addresses.csv
    |   +-- customers.csv
    |   +-- orders.csv
    |   +-- ...
    |
    +-- schema.sql

Execução:

    python gerar_schema.py

Saída:

    schema.sql

===============================================================================
"""

# ============================================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# ============================================================================
#
# São utilizadas somente bibliotecas que fazem parte da biblioteca padrão
# do Python 3, conforme solicitado no desafio.
# ============================================================================

import csv
import os
import re
from datetime import datetime


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Diretório onde estão armazenados os arquivos CSV.
DIRETORIO_CSV = "csv"

# Nome do arquivo SQL que será gerado.
ARQUIVO_SAIDA = "schema.sql"

# Quantidade de linhas analisadas por arquivo para inferência de tipos.
#
# O valor None significa que o script analisará todas as linhas.
# Isso torna a inferência mais confiável, especialmente em arquivos onde
# determinado tipo pode aparecer somente mais adiante.
LIMITE_LINHAS_ANALISE = None


# ============================================================================
# FUNÇÃO: NORMALIZAÇÃO DO NOME
# ============================================================================
def normalizar_nome(nome):
    """
    Normaliza nomes de tabelas e colunas para utilização no PostgreSQL.

    Exemplos:
        "Customer ID"  -> "customer_id"
        "created-at"   -> "created_at"
        "Nome Completo" -> "nome_completo"

    A função também evita problemas com caracteres especiais.
    """

    nome = nome.strip().lower()

    # Substitui espaços e caracteres que não sejam letras, números ou "_".
    nome = re.sub(r"[^a-zA-Z0-9_]", "_", nome)

    # Evita múltiplos "_" consecutivos.
    nome = re.sub(r"_+", "_", nome)

    # Remove "_" do início e do final.
    nome = nome.strip("_")

    # Caso o nome fique vazio, utiliza um nome genérico.
    if not nome:
        nome = "coluna"

    # PostgreSQL possui limite de 63 caracteres para identificadores.
    return nome[:63]


# ============================================================================
# FUNÇÃO: ESCAPE DE IDENTIFICADORES
# ============================================================================
def escapar_identificador(nome):
    """
    Coloca aspas duplas em identificadores PostgreSQL.

    Isso aumenta a segurança caso uma tabela ou coluna tenha nome que possa
    coincidir com uma palavra reservada do PostgreSQL.
    """

    nome = str(nome).replace('"', '""')

    return f'"{nome}"'


# ============================================================================
# FUNÇÃO: DETECÇÃO DE BOOLEAN
# ============================================================================
def parece_boolean(valor):
    """
    Verifica se o valor possui representação típica de booleano.
    """

    valor = valor.strip().lower()

    return valor in {
        "true",
        "false",
        "t",
        "f",
        "yes",
        "no",
        "y",
        "n",
        "sim",
        "nao",
        "não",
        "1",
        "0",
    }


# ============================================================================
# FUNÇÃO: DETECÇÃO DE INTEGER
# ============================================================================
def parece_integer(valor):
    """
    Verifica se um valor pode ser interpretado como número inteiro.

    Valores como "00123" continuam sendo considerados candidatos a inteiro
    nesta etapa. A decisão final de tipo considera também o nome da coluna,
    para evitar transformar identificadores em números quando isso poderia
    eliminar zeros à esquerda.
    """

    valor = valor.strip()

    if not valor:
        return False

    try:
        int(valor)
        return True
    except ValueError:
        return False


# ============================================================================
# FUNÇÃO: DETECÇÃO DE NUMERIC
# ============================================================================
def parece_numeric(valor):
    """
    Verifica se um valor pode ser interpretado como número decimal.

    Exemplos:
        100
        100.50
        -25.75
        0.123
    """

    valor = valor.strip()

    if not valor:
        return False

    # Trata formatos numéricos simples esperados nos CSVs.
    valor_normalizado = valor.replace(",", ".")

    try:
        float(valor_normalizado)
        return True
    except ValueError:
        return False


# ============================================================================
# FUNÇÃO: DETECÇÃO DE DATE / TIMESTAMP
# ============================================================================
def detectar_data_hora(valor):
    """
    Identifica se uma string representa DATE ou TIMESTAMP.

    A função retorna:
        "DATE"
        "TIMESTAMP"
        None

    São considerados formatos comuns encontrados em bases de dados.
    """

    valor = valor.strip()

    if not valor:
        return None

    # Formatos que representam timestamp.
    formatos_timestamp = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    for formato in formatos_timestamp:
        try:
            datetime.strptime(valor, formato)
            return "TIMESTAMP"
        except ValueError:
            pass

    # Formatos que representam somente data.
    formatos_date = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    for formato in formatos_date:
        try:
            datetime.strptime(valor, formato)
            return "DATE"
        except ValueError:
            pass

    return None


# ============================================================================
# FUNÇÃO: DETECÇÃO DO TIPO DA COLUNA
# ============================================================================
def inferir_tipo_coluna(nome_coluna, valores):
    """
    Infere o tipo PostgreSQL de uma coluna a partir dos valores encontrados.

    Hierarquia utilizada:

        BOOLEAN
        DATE
        TIMESTAMP
        INTEGER
        NUMERIC
        TEXT

    A função considera apenas valores não nulos.

    Importante:
        O objetivo desta etapa é gerar um schema inicial. A inferência não
        altera os arquivos CSV originais.
    """

    nome = nome_coluna.lower()

    # Remove valores vazios para a inferência.
    valores_validos = [
        str(valor).strip()
        for valor in valores
        if valor is not None and str(valor).strip() != ""
    ]

    # Se a coluna inteira estiver vazia, TEXT é o tipo mais seguro.
    if not valores_validos:
        return "TEXT"

    # ------------------------------------------------------------------------
    # 1. Identificação de campos que são claramente identificadores textuais
    # ------------------------------------------------------------------------
    #
    # Campos como CPF, telefone, CEP, SKU, EAN e códigos fiscais podem
    # possuir zeros à esquerda. Portanto, não devemos convertê-los
    # automaticamente para INTEGER.
    # ------------------------------------------------------------------------

    indicadores_textuais = [
        "cpf",
        "cnpj",
        "tax_id",
        "postal_code",
        "zip_code",
        "phone",
        "telephone",
        "sku",
        "barcode",
        "ean",
        "ncm",
        "access_key",
        "chave",
        "code",
    ]

    if any(indicador in nome for indicador in indicadores_textuais):
        return "TEXT"

    # ------------------------------------------------------------------------
    # 2. BOOLEAN
    # ------------------------------------------------------------------------

    if all(parece_boolean(valor) for valor in valores_validos):
        return "BOOLEAN"

    # ------------------------------------------------------------------------
    # 3. DATE / TIMESTAMP
    # ------------------------------------------------------------------------

    tipos_data = [
        detectar_data_hora(valor)
        for valor in valores_validos
    ]

    tipos_data_validos = [
        tipo
        for tipo in tipos_data
        if tipo is not None
    ]

    # Se todos os valores puderem ser interpretados como datas/timestamps,
    # escolhemos o tipo mais específico encontrado.
    if len(tipos_data_validos) == len(valores_validos):

        if "TIMESTAMP" in tipos_data_validos:
            return "TIMESTAMP"

        return "DATE"

    # ------------------------------------------------------------------------
    # 4. INTEGER
    # ------------------------------------------------------------------------

    if all(parece_integer(valor) for valor in valores_validos):
        return "INTEGER"

    # ------------------------------------------------------------------------
    # 5. NUMERIC
    # ------------------------------------------------------------------------

    if all(parece_numeric(valor) for valor in valores_validos):
        return "NUMERIC"

    # ------------------------------------------------------------------------
    # 6. TEXT
    # ------------------------------------------------------------------------

    return "TEXT"


# ============================================================================
# FUNÇÃO: LEITURA DE CSV
# ============================================================================
def analisar_csv(caminho):
    """
    Lê um arquivo CSV e retorna:

        - lista de colunas;
        - tipo inferido para cada coluna;
        - quantidade de linhas.

    O CSV é aberto com encoding UTF-8 com BOM, permitindo também arquivos
    exportados por ferramentas que adicionam BOM no início do arquivo.
    """

    with open(
        caminho,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as arquivo:

        # --------------------------------------------------------------------
        # Detecta automaticamente o delimitador.
        # --------------------------------------------------------------------
        #
        # O Sniffer é utilizado para lidar com CSVs separados por vírgula,
        # ponto e vírgula ou tabulação.
        # --------------------------------------------------------------------

        amostra = arquivo.read(8192)

        arquivo.seek(0)

        try:
            dialeto = csv.Sniffer().sniff(
                amostra,
                delimiters=",;\t|"
            )
        except csv.Error:
            # Caso não seja possível detectar o delimitador, considera
            # vírgula como padrão.
            dialeto = csv.excel

        leitor = csv.DictReader(
            arquivo,
            dialect=dialeto
        )

        if leitor.fieldnames is None:
            raise ValueError(
                f"O arquivo '{caminho}' não possui cabeçalho."
            )

        # Normaliza os nomes das colunas.
        colunas_originais = leitor.fieldnames

        colunas = [
            normalizar_nome(coluna)
            for coluna in colunas_originais
        ]

        # Estrutura que armazenará os valores de cada coluna.
        valores_por_coluna = {
            coluna: []
            for coluna in colunas
        }

        quantidade_linhas = 0

        # --------------------------------------------------------------------
        # Leitura das linhas.
        # --------------------------------------------------------------------

        for linha in leitor:

            quantidade_linhas += 1

            for coluna_original, coluna_normalizada in zip(
                colunas_originais,
                colunas
            ):

                valor = linha.get(coluna_original)

                valores_por_coluna[coluna_normalizada].append(valor)

            # Caso tenha sido definido limite de análise, interrompe a
            # leitura após atingir a quantidade configurada.
            if (
                LIMITE_LINHAS_ANALISE is not None
                and quantidade_linhas >= LIMITE_LINHAS_ANALISE
            ):
                break

        # --------------------------------------------------------------------
        # Inferência dos tipos.
        # --------------------------------------------------------------------

        tipos = {}

        for coluna in colunas:

            tipos[coluna] = inferir_tipo_coluna(
                coluna,
                valores_por_coluna[coluna]
            )

        return colunas, tipos, quantidade_linhas


# ============================================================================
# FUNÇÃO: GERAÇÃO DO CREATE TABLE
# ============================================================================
def gerar_create_table(nome_tabela, colunas, tipos):
    """
    Gera o comando CREATE TABLE correspondente a uma tabela.
    """

    linhas = []

    linhas.append(
        f"CREATE TABLE {escapar_identificador(nome_tabela)} ("
    )

    definicoes = []

    for coluna in colunas:

        tipo = tipos[coluna]

        definicoes.append(
            f"    {escapar_identificador(coluna)} {tipo}"
        )

    linhas.append(",\n".join(definicoes))

    linhas.append(");")

    return "\n".join(linhas)


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================
def main():
    """
    Função principal responsável por:

        1. validar o diretório de entrada;
        2. localizar os arquivos CSV;
        3. analisar cada arquivo;
        4. gerar os CREATE TABLE;
        5. escrever o arquivo schema.sql.
    """

    print("=" * 70)
    print("GERADOR DE SCHEMA POSTGRESQL")
    print("=" * 70)

    # ------------------------------------------------------------------------
    # Validação do diretório.
    # ------------------------------------------------------------------------

    if not os.path.isdir(DIRETORIO_CSV):

        raise FileNotFoundError(
            f"Diretório não encontrado: {DIRETORIO_CSV}"
        )

    # ------------------------------------------------------------------------
    # Localização dos CSVs.
    # ------------------------------------------------------------------------
    #
    # sorted() garante que a ordem das tabelas seja sempre a mesma,
    # tornando a execução reproduzível.
    # ------------------------------------------------------------------------

    arquivos_csv = sorted(
        arquivo
        for arquivo in os.listdir(DIRETORIO_CSV)
        if arquivo.lower().endswith(".csv")
    )

    if not arquivos_csv:

        raise FileNotFoundError(
            f"Nenhum arquivo CSV encontrado em '{DIRETORIO_CSV}'."
        )

    print(f"Diretório de entrada: {DIRETORIO_CSV}")
    print(f"Arquivos CSV encontrados: {len(arquivos_csv)}")
    print()

    # ------------------------------------------------------------------------
    # Cabeçalho do arquivo SQL.
    # ------------------------------------------------------------------------

    sql = []

    sql.append(
        "-- ====================================================================="
    )
    sql.append(
        "-- SCHEMA POSTGRESQL GERADO AUTOMATICAMENTE A PARTIR DOS CSVs"
    )
    sql.append(
        "-- ====================================================================="
    )
    sql.append(
        "-- Projeto: Lighthouse - Desafio Técnico / Indicium Academy AI"
    )
    sql.append(
        "--"
    )
    sql.append(
        "-- Este arquivo foi gerado pelo script gerar_schema.py."
    )
    sql.append(
        "-- Os tipos das colunas foram inferidos a partir dos dados presentes"
    )
    sql.append(
        "-- nos arquivos CSV de origem."
    )
    sql.append(
        "--"
    )
    sql.append(
        "-- Observação:"
    )
    sql.append(
        "-- Este arquivo representa uma estrutura inicial das tabelas."
    )
    sql.append(
        "-- Restrições como PK, FK, UNIQUE e NOT NULL não são adicionadas"
    )
    sql.append(
        "-- automaticamente nesta etapa, pois o objetivo é reproduzir a"
    )
    sql.append(
        "-- estrutura observada nos arquivos de origem."
    )
    sql.append(
        "-- ====================================================================="
    )
    sql.append("")

    # ------------------------------------------------------------------------
    # Análise de cada CSV.
    # ------------------------------------------------------------------------

    resultados = []

    for numero, arquivo in enumerate(arquivos_csv, start=1):

        caminho = os.path.join(
            DIRETORIO_CSV,
            arquivo
        )

        # O nome da tabela é derivado do nome do arquivo.
        nome_tabela = normalizar_nome(
            os.path.splitext(arquivo)[0]
        )

        print(
            f"[{numero}/{len(arquivos_csv)}] "
            f"Analisando: {arquivo}"
        )

        colunas, tipos, quantidade_linhas = analisar_csv(
            caminho
        )

        resultados.append(
            {
                "arquivo": arquivo,
                "tabela": nome_tabela,
                "colunas": colunas,
                "tipos": tipos,
                "linhas": quantidade_linhas,
            }
        )

        print(
            f"    Tabela: {nome_tabela} | "
            f"Colunas: {len(colunas)} | "
            f"Linhas analisadas: {quantidade_linhas}"
        )

    # ------------------------------------------------------------------------
    # Geração dos CREATE TABLE.
    # ------------------------------------------------------------------------

    for resultado in resultados:

        arquivo = resultado["arquivo"]
        tabela = resultado["tabela"]
        colunas = resultado["colunas"]
        tipos = resultado["tipos"]

        sql.append(
            "-- ====================================================================="
        )
        sql.append(
            f"-- Arquivo de origem: {arquivo}"
        )
        sql.append(
            f"-- Tabela destino: {tabela}"
        )
        sql.append(
            f"-- Quantidade de colunas: {len(colunas)}"
        )
        sql.append(
            "-- ====================================================================="
        )

        sql.append(
            gerar_create_table(
                tabela,
                colunas,
                tipos
            )
        )

        sql.append("")

    # ------------------------------------------------------------------------
    # Escrita do arquivo schema.sql.
    # ------------------------------------------------------------------------

    with open(
        ARQUIVO_SAIDA,
        "w",
        encoding="utf-8"
    ) as arquivo_saida:

        arquivo_saida.write(
            "\n".join(sql)
        )

    # ------------------------------------------------------------------------
    # Resumo final da execução.
    # ------------------------------------------------------------------------

    print()
    print("=" * 70)
    print("PROCESSAMENTO CONCLUÍDO")
    print("=" * 70)
    print(f"Schema gerado: {ARQUIVO_SAIDA}")
    print(f"Tabelas encontradas: {len(resultados)}")
    print("=" * 70)


# ============================================================================
# PONTO DE ENTRADA DO SCRIPT
# ============================================================================
#
# Essa estrutura permite executar o arquivo diretamente com:
#
#     python gerar_schema.py
#
# e também permite futuramente reutilizar as funções do script em outro
# programa sem executar automaticamente a função main().
# ============================================================================

if __name__ == "__main__":
    main()