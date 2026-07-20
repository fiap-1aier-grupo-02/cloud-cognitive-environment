import os
import csv

from openai import AzureOpenAI

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


# ==============================
# CONFIGURAÇÕES
# ==============================

INDEX_NAME = "produtos-index"

AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = os.environ["AZURE_OPENAI_KEY"]

SEARCH_ENDPOINT = os.environ["SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["SEARCH_KEY"]


# ==============================
# CLIENTES AZURE
# ==============================

openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2024-02-01",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)


search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_KEY)
)


# ==============================
# GERAR EMBEDDING
# ==============================

def gerar_embedding(texto):

    resposta = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texto
    )

    return resposta.data[0].embedding



# ==============================
# LER CSV
# ==============================

def carregar_produtos():

    produtos = []

    with open(
        "produtos.csv",
        encoding="utf-8"
    ) as arquivo:

        leitor = csv.DictReader(arquivo)

        for linha in leitor:
            produtos.append(linha)

    return produtos



# ==============================
# INDEXAR PRODUTOS NO AI SEARCH
# ==============================

def indexar_produtos():

    produtos = carregar_produtos()

    documentos = []


    for produto in produtos:

        texto = (
            produto["nome"]
            + " "
            + produto["descricao"]
        )


        print(
            "Gerando embedding:",
            produto["nome"]
        )


        vetor = gerar_embedding(texto)


        documento = {

            "id": produto["id"],

            "nome": produto["nome"],

            "descricao": produto["descricao"],

            "categoria": produto["categoria"],

            "preco": float(produto["preco"]),

            "estoque": int(produto["estoque"]),

            "content_vector": vetor

        }


        documentos.append(documento)



    resultado = search_client.upload_documents(
        documents=documentos
    )


    print("\nIndexação concluída!")

    for r in resultado:
        print(r)



# ==============================
# BUSCA VETORIAL
# ==============================

def buscar_produtos():

    pergunta = "cadeira para minha coluna ergonômica"


    print("\nConsulta:")
    print(pergunta)


    vetor_consulta = gerar_embedding(
        pergunta
    )


    consulta_vetorial = VectorizedQuery(

        vector=vetor_consulta,

        k_nearest_neighbors=5,

        fields="content_vector"

    )


    resultados = search_client.search(

        search_text=None,

        vector_queries=[
            consulta_vetorial
        ],

        select=[
            "nome",
            "descricao",
            "categoria",
            "preco"
        ]

    )


    print("\n===== RESULTADOS =====")


    for resultado in resultados:

        print(
            "\nProduto:",
            resultado["nome"]
        )

        print(
            "Categoria:",
            resultado["categoria"]
        )

        print(
            "Descrição:",
            resultado["descricao"]
        )

        print(
            "Preço:",
            resultado["preco"]
        )



# ==============================
# EXECUÇÃO
# ==============================

if __name__ == "__main__":


    print("Iniciando Vector Search Azure...")


    indexar_produtos()


    buscar_produtos()


    print("\nFim!")