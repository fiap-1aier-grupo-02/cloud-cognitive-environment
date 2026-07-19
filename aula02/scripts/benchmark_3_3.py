import os
import csv
import time
import statistics
import pyodbc

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from azure.search.documents import SearchClient


QUERY = "cadeira ergonômica para dor lombar"
TERMOS = ["cadeira", "ergon", "dor", "lombar"]

COSMOS_DATABASE = "qcdb"
COSMOS_CONTAINER = "produtos-benchmark"
SEARCH_INDEX = "produtos-index"


def medir(nome, func, repeticoes=10):
    tempos = []
    ultimo_resultado = []

    for _ in range(repeticoes):
        inicio = time.perf_counter()
        ultimo_resultado = func()
        fim = time.perf_counter()
        tempos.append((fim - inicio) * 1000)

    print(f"\n=== {nome} ===")
    print(f"Latência média: {statistics.mean(tempos):.2f} ms")
    print(f"Latência mínima: {min(tempos):.2f} ms")
    print(f"Latência máxima: {max(tempos):.2f} ms")
    print("Top resultados:")
    for item in ultimo_resultado[:5]:
        print(f"- {item}")

    return {
        "servico": nome,
        "media_ms": statistics.mean(tempos),
        "min_ms": min(tempos),
        "max_ms": max(tempos),
        "resultados": ultimo_resultado[:5],
    }


def get_key_vault_client():
    kv_name = os.environ["KEY_VAULT_NAME"]
    credential = DefaultAzureCredential()

    return SecretClient(
        vault_url=f"https://{kv_name}.vault.azure.net",
        credential=credential
    )


def carregar_produtos_do_blob():
    storage = os.environ["STORAGE_ACCOUNT_NAME"]
    credential = DefaultAzureCredential()

    blob_service = BlobServiceClient(
        f"https://{storage}.blob.core.windows.net",
        credential=credential
    )

    blob = blob_service.get_blob_client("catalogo", "produtos.csv")
    csv_text = blob.download_blob().readall().decode("utf-8")
    return list(csv.DictReader(csv_text.splitlines()))


def preparar_cosmos(produtos):
    endpoint = os.environ["COSMOS_ENDPOINT"]
    kv_client = get_key_vault_client()

    cosmos_key = kv_client.get_secret("cosmos-primary-key").value
    client = CosmosClient(endpoint, credential=cosmos_key)

    database = client.create_database_if_not_exists(id=COSMOS_DATABASE)

    container = database.create_container_if_not_exists(
        id=COSMOS_CONTAINER,
        partition_key=PartitionKey(path="/categoria")
    )

    for p in produtos:
        container.upsert_item({
            "id": str(p["id"]),
            "nome": p.get("nome", ""),
            "descricao": p.get("descricao", ""),
            "categoria": p.get("categoria", "geral"),
            "preco": p.get("preco", "")
        })

    return container


def conectar_sql():
    kv_client = get_key_vault_client()
    conn_str = kv_client.get_secret("sql-connection-string").value
    driver = "{ODBC Driver 18 for SQL Server}"
    conn_str_with_driver = f"Driver={driver};{conn_str}"
    return pyodbc.connect(conn_str_with_driver)


def benchmark_sql():
    conn = conectar_sql()
    cursor = conn.cursor()

    sql = """
    SELECT TOP 5 id, nome, descricao, categoria
    FROM T_PRODUTOS
    WHERE
        LOWER(nome) LIKE '%cadeira%'
        OR LOWER(descricao) LIKE '%cadeira%'
        OR LOWER(nome) LIKE '%ergon%'
        OR LOWER(descricao) LIKE '%ergon%'
        OR LOWER(nome) LIKE '%dor%'
        OR LOWER(descricao) LIKE '%dor%'
        OR LOWER(nome) LIKE '%lombar%'
        OR LOWER(descricao) LIKE '%lombar%'
    """

    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()

    return [f"{r.nome} | {r.categoria}" for r in rows]


def benchmark_cosmos(container):
    filtro = " OR ".join([
        f"CONTAINS(LOWER(c.nome), '{t}') OR CONTAINS(LOWER(c.descricao), '{t}')"
        for t in TERMOS
    ])

    query = f"""
    SELECT TOP 5 c.id, c.nome, c.descricao, c.categoria
    FROM c
    WHERE {filtro}
    """

    rows = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    return [f"{r['nome']} | {r.get('categoria', '')}" for r in rows]


def benchmark_ai_search():
    endpoint = os.environ["SEARCH_ENDPOINT"]
    credential = DefaultAzureCredential()

    client = SearchClient(
        endpoint=endpoint,
        index_name=SEARCH_INDEX,
        credential=credential
    )

    results = client.search(
        search_text=QUERY,
        top=5
    )

    saida = []
    for r in results:
        nome = r.get("nome", "")
        categoria = r.get("categoria", "")
        score = r.get("@search.score", 0)
        saida.append(f"{nome} | {categoria} | score={score:.4f}")

    return saida


def main():
    print("Carregando produtos do Blob...")
    produtos = carregar_produtos_do_blob()
    print(f"Produtos carregados: {len(produtos)}")

    print("Preparando Cosmos...")
    cosmos_container = preparar_cosmos(produtos)
    print("Cosmos pronto.")

    resultados = []
    resultados.append(medir("Azure SQL - LIKE", benchmark_sql))
    resultados.append(medir("Cosmos DB - CONTAINS", lambda: benchmark_cosmos(cosmos_container)))
    resultados.append(medir("Azure AI Search - Keyword/BM25", benchmark_ai_search))

    print("\n=== RESUMO CSV ===")
    print("servico,media_ms,min_ms,max_ms")
    for r in resultados:
        print(f"{r['servico']},{r['media_ms']:.2f},{r['min_ms']:.2f},{r['max_ms']:.2f}")


if __name__ == "__main__":
    main()
