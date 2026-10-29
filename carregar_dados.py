"""
===============================================================================
QUESTÃO 3 - CARREGAMENTO DOS DADOS
PROJETO LIGHTHOUSE - INDICIUM ACADEMY AI
===============================================================================

OBJETIVO
--------
Realizar o carregamento dos arquivos CSV fornecidos pela fonte para as
respectivas tabelas do PostgreSQL.

ORIGEM DOS DADOS
----------------
Os arquivos CSV devem estar armazenados no diretório:

    ./csv

Cada arquivo CSV representa uma tabela no banco de dados.

Exemplo:

    csv/orders.csv
        ->
    desafio_lighthouse.orders


BANCO DE DADOS DE DESTINO
-------------------------
SGBD:       PostgreSQL
Host:       localhost
Porta:      5432
Database:   postgres
Schema:     desafio_lighthouse
Usuário:    postgres


PREMISSAS DA QUESTÃO
--------------------
- Todos os arquivos CSV presentes no diretório de origem serão carregados.
- O nome do arquivo determina o nome da tabela de destino.
- O schema das tabelas deve ter sido criado previamente.
- A estrutura das tabelas é definida pelo schema.sql produzido na Questão 2.
- Não são realizadas limpezas ou tratamentos nos dados.
- Não são removidos registros.
- Não são corrigidos valores inconsistentes.
- Não são corrigidos caracteres especiais.
- Não são realizadas conversões de negócio nos dados.
- Campos vazios dos CSVs são enviados como NULL ao PostgreSQL.
- Os dados são carregados respeitando a ordem das colunas encontrada no CSV.


SEGURANÇA
---------
A senha do PostgreSQL NÃO é armazenada diretamente neste código.

A credencial é obtida por meio da variável de ambiente:

    LIGHTHOUSE_DB_PASSWORD

No PowerShell, antes de executar o script:

    $env:LIGHTHOUSE_DB_PASSWORD = "SUA_SENHA"

Depois:

    python carregar_dados.py


DEPENDÊNCIA
-----------
Biblioteca utilizada:

    psycopg2-binary

Instalação:

    python -m pip install psycopg2-binary


EXECUÇÃO
--------
A partir do diretório raiz do projeto:

    python carregar_dados.py


ESTRUTURA ESPERADA DO PROJETO
-----------------------------

    lighthouse/
    |
    +-- csv/
    |   +-- addresses.csv
    |   +-- attributes.csv
    |   +-- brands.csv
    |   +-- categories.csv
    |   +-- customers.csv
    |   +-- ...
    |
    +-- schema.sql
    +-- carregar_dados.py


TRANSAÇÕES
----------
Cada arquivo CSV é carregado dentro de uma transação.

Se ocorrer algum erro durante o carregamento de uma tabela:

    - A transação daquela tabela é desfeita com rollback().
    - O processo é encerrado.
    - Nenhum tratamento ou correção dos dados é realizado automaticamente.

===============================================================================
"""

# =============================================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# =============================================================================

import csv
import os
import sys

import psycopg2
from psycopg2 import sql


# =============================================================================
# CONFIGURAÇÕES DO PROJETO
# =============================================================================

# Diretório que contém os arquivos CSV fornecidos pela fonte.
#
# O caminho é relativo ao diretório onde o script é executado.
CSV_DIR = "csv"


# Schema PostgreSQL onde as tabelas foram criadas na Questão 2.
#
# É importante informar o schema explicitamente nos comandos SQL para não
# depender da configuração do search_path do PostgreSQL.
DB_SCHEMA = "desafio_lighthouse"


# Configurações de conexão com o PostgreSQL.
#
# A senha não fica armazenada diretamente no código.
# Ela é obtida da variável de ambiente LIGHTHOUSE_DB_PASSWORD.
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": os.getenv("LIGHTHOUSE_DB_PASSWORD"),
}


# =============================================================================
# FUNÇÃO: VALIDAR CONFIGURAÇÃO
# =============================================================================

def validar_configuracao():
    """
    Valida as configurações básicas necessárias para executar o carregamento.

    São verificadas:
        1. Existência do diretório de CSVs.
        2. Existência da variável de ambiente contendo a senha.

    Nenhum dado é alterado nesta etapa.
    """

    # -------------------------------------------------------------------------
    # Verifica se o diretório de origem existe.
    # -------------------------------------------------------------------------

    if not os.path.isdir(CSV_DIR):
        print()
        print("ERRO: diretório de CSVs não encontrado.")
        print(f"Diretório esperado: {os.path.abspath(CSV_DIR)}")
        print()

        sys.exit(1)


    # -------------------------------------------------------------------------
    # Verifica se a senha foi informada por variável de ambiente.
    # -------------------------------------------------------------------------

    if not DB_CONFIG["password"]:
        print()
        print("ERRO: senha do PostgreSQL não configurada.")
        print()
        print("No PowerShell, execute:")
        print()
        print('    $env:LIGHTHOUSE_DB_PASSWORD = "SUA_SENHA"')
        print()
        print("Depois execute novamente:")
        print()
        print("    python carregar_dados.py")
        print()

        sys.exit(1)


# =============================================================================
# FUNÇÃO: OBTER ARQUIVOS CSV
# =============================================================================

def obter_arquivos_csv():
    """
    Localiza todos os arquivos CSV presentes no diretório configurado.

    Retorna:
        Lista contendo os nomes dos arquivos CSV.

    Os arquivos são ordenados alfabeticamente para que a execução seja
    determinística e facilmente replicável.
    """

    arquivos = []

    for nome_arquivo in os.listdir(CSV_DIR):

        # Verifica se o arquivo possui extensão .csv.
        if nome_arquivo.lower().endswith(".csv"):

            caminho = os.path.join(CSV_DIR, nome_arquivo)

            # Garante que estamos considerando somente arquivos.
            if os.path.isfile(caminho):
                arquivos.append(nome_arquivo)

    # Ordenação para garantir a mesma sequência de execução.
    arquivos.sort()

    return arquivos


# =============================================================================
# FUNÇÃO: VERIFICAR TABELA
# =============================================================================

def verificar_tabela(conexao, tabela):
    """
    Verifica se a tabela de destino existe no schema configurado.

    Parâmetros:
        conexao: conexão ativa com PostgreSQL.
        tabela: nome da tabela que será verificada.

    Retorna:
        True  -> tabela encontrada.
        False -> tabela não encontrada.
    """

    cursor = conexao.cursor()

    try:

        # Consulta o catálogo do PostgreSQL para verificar a existência
        # da tabela dentro do schema especificado.
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
            );
            """,
            (DB_SCHEMA, tabela)
        )

        resultado = cursor.fetchone()

        return resultado[0]

    finally:

        cursor.close()


# =============================================================================
# FUNÇÃO: CARREGAR CSV
# =============================================================================

def carregar_csv(conexao, nome_arquivo):
    """
    Carrega um arquivo CSV para a tabela correspondente no PostgreSQL.

    Relação entre arquivo e tabela:

        nome_do_arquivo.csv
                |
                v
        nome_do_arquivo

    Exemplo:

        orders.csv
            ->
        desafio_lighthouse.orders

    Nenhuma limpeza ou transformação de negócio é realizada.

    Campos vazios são convertidos para None, que o psycopg2 envia ao
    PostgreSQL como NULL.
    """

    # -------------------------------------------------------------------------
    # Define o caminho completo do arquivo.
    # -------------------------------------------------------------------------

    caminho_csv = os.path.join(CSV_DIR, nome_arquivo)


    # -------------------------------------------------------------------------
    # Define o nome da tabela removendo a extensão .csv.
    # -------------------------------------------------------------------------

    tabela = os.path.splitext(nome_arquivo)[0]


    print()
    print("-" * 70)
    print(f"Arquivo : {nome_arquivo}")
    print(f"Tabela  : {DB_SCHEMA}.{tabela}")
    print("-" * 70)


    # -------------------------------------------------------------------------
    # Verifica se a tabela correspondente ao CSV existe.
    # -------------------------------------------------------------------------

    if not verificar_tabela(conexao, tabela):

        raise RuntimeError(
            f"A tabela '{DB_SCHEMA}.{tabela}' não existe no PostgreSQL."
        )


    cursor = conexao.cursor()

    try:

        # =====================================================================
        # ABERTURA DO CSV
        # =====================================================================

        # utf-8-sig permite trabalhar também com arquivos CSV que possuem
        # BOM (Byte Order Mark) no início do arquivo.
        #
        # O conteúdo dos dados não é corrigido ou tratado.
        with open(
            caminho_csv,
            mode="r",
            encoding="utf-8-sig",
            newline=""
        ) as arquivo:

            # Detecta automaticamente o delimitador utilizado pelo CSV.
            #
            # Alguns arquivos podem utilizar vírgula (,) enquanto outros podem utilizar
            # ponto e vírgula (;). A detecção não altera os dados; apenas informa ao
            # módulo csv como interpretar a estrutura das colunas.
            amostra = arquivo.read(4096)
            arquivo.seek(0)

            try:
                dialeto = csv.Sniffer().sniff(
                    amostra,
                    delimiters=",;"
                )
            except csv.Error:
                # Caso não seja possível detectar automaticamente, utiliza vírgula
                # como delimitador padrão.
                dialeto = csv.excel

            leitor = csv.reader(
                arquivo,
                dialect=dialeto
            )


            # -----------------------------------------------------------------
            # LEITURA DO CABEÇALHO
            # -----------------------------------------------------------------

            # A primeira linha contém os nomes das colunas.
            #
            # Esses nomes serão utilizados para construir o comando INSERT.
            try:
                colunas = next(leitor)

            except StopIteration:

                raise RuntimeError(
                    f"O arquivo '{nome_arquivo}' está vazio."
                )


            # -----------------------------------------------------------------
            # VALIDAÇÃO BÁSICA DO CABEÇALHO
            # -----------------------------------------------------------------

            if not colunas:

                raise RuntimeError(
                    f"O arquivo '{nome_arquivo}' não possui colunas."
                )


            # =================================================================
            # CONSTRUÇÃO DO INSERT
            # =================================================================

            # O schema é informado explicitamente no comando SQL.
            #
            # Dessa forma, o PostgreSQL executará:
            #
            #     INSERT INTO desafio_lighthouse.orders
            #
            # em vez de depender do search_path e executar apenas:
            #
            #     INSERT INTO orders
            #
            # psycopg2.sql.Identifier é utilizado para tratar corretamente
            # nomes de schema, tabela e colunas como identificadores SQL.
            comando = sql.SQL("""
                INSERT INTO {}.{}
                ({})
                VALUES ({})
            """).format(
                sql.Identifier(DB_SCHEMA),
                sql.Identifier(tabela),
                sql.SQL(", ").join(
                    sql.Identifier(coluna)
                    for coluna in colunas
                ),
                sql.SQL(", ").join(
                    sql.Placeholder()
                    for _ in colunas
                )
            )


            # -----------------------------------------------------------------
            # CONTADOR DE REGISTROS
            # -----------------------------------------------------------------

            total = 0


            # =================================================================
            # LEITURA E INSERÇÃO DOS REGISTROS
            # =================================================================

            for numero_linha, linha in enumerate(leitor, start=2):

                # -------------------------------------------------------------
                # Validação da quantidade de colunas
                # -------------------------------------------------------------
                #
                # Essa validação não altera os dados.
                #
                # Ela apenas evita que uma linha estruturalmente incompatível
                # seja enviada para o PostgreSQL.
                # -------------------------------------------------------------

                if len(linha) != len(colunas):

                    raise RuntimeError(
                        f"Linha {numero_linha} possui "
                        f"{len(linha)} campos, mas o cabeçalho possui "
                        f"{len(colunas)} colunas."
                    )


                # -------------------------------------------------------------
                # CAMPOS VAZIOS
                # -------------------------------------------------------------
                #
                # Campos vazios do CSV são representados por None.
                #
                # O psycopg2 transforma None em NULL no PostgreSQL.
                #
                # Não estamos corrigindo ou removendo o valor.
                # Estamos apenas realizando a representação necessária para
                # que o banco registre o campo como NULL.
                # -------------------------------------------------------------

                valores = [
                    None if valor == "" else valor
                    for valor in linha
                ]


                # -------------------------------------------------------------
                # EXECUTA O INSERT
                # -------------------------------------------------------------

                cursor.execute(comando, valores)

                total += 1


                # -------------------------------------------------------------
                # MOSTRA PROGRESSO A CADA 10.000 REGISTROS
                # -------------------------------------------------------------

                if total % 10000 == 0:

                    print(
                        f"  Registros processados: {total:,}"
                    )


        # =====================================================================
        # COMMIT
        # =====================================================================

        # A transação é confirmada somente após a leitura completa do arquivo.
        #
        # Dessa forma, se ocorrer um erro antes deste ponto, os registros
        # inseridos durante esta transação poderão ser desfeitos pelo
        # rollback().
        conexao.commit()


        print()
        print(
            f"OK - {total:,} registros carregados."
        )

        return total


    except Exception:

        # =====================================================================
        # ROLLBACK
        # =====================================================================

        # Em caso de qualquer erro, desfazemos a transação atual.
        #
        # Nenhum tratamento ou correção do conteúdo do CSV é realizado.
        conexao.rollback()

        raise


    finally:

        # Fecha o cursor utilizado nesta tabela.
        cursor.close()


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main():
    """
    Controla a execução completa do processo de carregamento.

    Fluxo:

        1. Validação da configuração.
        2. Localização dos CSVs.
        3. Conexão com PostgreSQL.
        4. Carregamento de cada CSV.
        5. Exibição do resumo.
        6. Encerramento da conexão.
    """

    print()
    print("=" * 70)
    print("CARREGAMENTO DOS DADOS - LIGHTHOUSE")
    print("=" * 70)
    print()


    # -------------------------------------------------------------------------
    # VALIDAÇÃO INICIAL
    # -------------------------------------------------------------------------

    validar_configuracao()


    # -------------------------------------------------------------------------
    # LOCALIZAÇÃO DOS CSVs
    # -------------------------------------------------------------------------

    arquivos_csv = obter_arquivos_csv()

    print(
        f"Arquivos CSV encontrados: {len(arquivos_csv)}"
    )


    # Verifica se existem arquivos para carregar.
    if not arquivos_csv:

        print()
        print("ERRO: nenhum arquivo CSV encontrado.")
        print(
            f"Diretório analisado: {os.path.abspath(CSV_DIR)}"
        )
        print()

        sys.exit(1)


    # -------------------------------------------------------------------------
    # CONEXÃO COM POSTGRESQL
    # -------------------------------------------------------------------------

    conexao = None

    try:

        conexao = psycopg2.connect(**DB_CONFIG)

        print(
            "Conexão com PostgreSQL estabelecida com sucesso."
        )


    except psycopg2.Error as erro:

        print()
        print("ERRO: não foi possível conectar ao PostgreSQL.")
        print()
        print("Detalhes:")
        print(erro)
        print()

        sys.exit(1)


    # -------------------------------------------------------------------------
    # CARREGAMENTO DOS ARQUIVOS
    # -------------------------------------------------------------------------

    total_geral = 0
    tabelas_carregadas = 0


    try:

        for indice, nome_arquivo in enumerate(
            arquivos_csv,
            start=1
        ):

            print()
            print(
                f"[{indice}/{len(arquivos_csv)}] "
                f"Processando: {nome_arquivo}"
            )


            try:

                quantidade = carregar_csv(
                    conexao,
                    nome_arquivo
                )

                total_geral += quantidade
                tabelas_carregadas += 1


            except Exception as erro:

                # -------------------------------------------------------------
                # ERRO DE CARREGAMENTO
                # -------------------------------------------------------------

                tabela = os.path.splitext(
                    nome_arquivo
                )[0]

                print()
                print(
                    f"ERRO ao carregar a tabela '{tabela}'."
                )

                print(
                    f"Detalhes: {erro}"
                )

                print()

                # O processo é encerrado para evitar que algumas tabelas
                # sejam carregadas e outras não, deixando a execução parcial.
                raise


        # =====================================================================
        # RESUMO FINAL
        # =====================================================================

        print()
        print("=" * 70)
        print("CARREGAMENTO CONCLUÍDO COM SUCESSO")
        print("=" * 70)
        print()
        print(
            f"Tabelas carregadas : {tabelas_carregadas}"
        )
        print(
            f"Registros carregados: {total_geral:,}"
        )
        print()


    except Exception:

        print()
        print("=" * 70)
        print("CARREGAMENTO INTERROMPIDO")
        print("=" * 70)
        print()

        # Retorna código de erro para o sistema operacional.
        sys.exit(1)


    finally:

        # ---------------------------------------------------------------------
        # ENCERRAMENTO DA CONEXÃO
        # ---------------------------------------------------------------------

        if conexao is not None:

            conexao.close()

            print(
                "Conexão com PostgreSQL encerrada."
            )


# =============================================================================
# PONTO DE ENTRADA DO SCRIPT
# =============================================================================

if __name__ == "__main__":

    main()