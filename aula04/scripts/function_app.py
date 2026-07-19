"""
Function App — Aula 4 Quantum Commerce
Rotas cognitivas via Managed Identity (Language, Vision) e Key Vault (Speech):
  GET  /api/health
  GET  /api/transcrever?blob=<nome>&container=audios&idioma=pt-BR
  POST /api/analisar-reviews?limit=10
  GET  /api/analisar-imagem?blob=<nome>&container=imagens
"""
import json
import logging
import os
import requests
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timezone

from azure.ai.textanalytics import (
    ExtractiveSummaryAction,
    TextAnalyticsClient,
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

AI_ENDPOINT          = os.environ["AI_ENDPOINT"]
AI_REGION            = os.environ.get("AI_REGION", "eastus2")
AI_KEY               = os.environ.get("AI_KEY", "")  # Key Vault reference resolvida pelo runtime
DATA_STORAGE_ACCOUNT = os.environ["DATA_STORAGE_ACCOUNT"]
MONGODB_URI          = os.environ["MONGODB_URI"]

_credential = DefaultAzureCredential()
_blob_service = BlobServiceClient(
    f"https://{DATA_STORAGE_ACCOUNT}.blob.core.windows.net",
    credential=_credential,
)


def _get_speech_token(region: str) -> str:
    """
    Troca a subscription key (do Key Vault) por speech token.
    Speech exige a role 'Cognitive Services Speech User' para MI — usamos key por simplicidade.
    """
    resp = requests.post(
        f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
        headers={"Ocp-Apim-Subscription-Key": AI_KEY, "Content-Length": "0"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.text


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({
            "status": "ok",
            "service": "qc-cognitive",
            "rotas": ["/api/health", "/api/transcrever", "/api/analisar-reviews", "/api/analisar-imagem"],
            "ai_endpoint": AI_ENDPOINT,
        }),
        mimetype="application/json",
    )


@app.route(route="transcrever", methods=["GET", "POST"])
def transcrever(req: func.HttpRequest) -> func.HttpResponse:
    """
    Transcreve áudio WAV do Blob via Azure Speech STT (REST API).
    GET /api/transcrever?blob=audio-teste.wav&idioma=pt-BR
    """
    blob_name = req.params.get("blob", "audio-teste.wav")
    container = req.params.get("container", "audios")
    idioma    = req.params.get("idioma", "pt-BR")

    try:
        # 1. Baixar áudio do Blob via MI
        blob_client = _blob_service.get_blob_client(container=container, blob=blob_name)
        audio_bytes = blob_client.download_blob().readall()

        # 2. Obter speech token via key (do Key Vault)
        token = _get_speech_token(AI_REGION)
        resp = requests.post(
            f"https://{AI_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "Accept": "application/json",
            },
            params={"language": idioma, "format": "detailed"},
            data=audio_bytes,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        transcricao = ""
        if "NBest" in data and data["NBest"]:
            transcricao = data["NBest"][0].get("Display", "")
        elif "DisplayText" in data:
            transcricao = data["DisplayText"]

        return func.HttpResponse(
            json.dumps({
                "transcricao": transcricao,
                "idioma": idioma,
                "blob": blob_name,
                "status_stt": data.get("RecognitionStatus", ""),
            }, ensure_ascii=False),
            mimetype="application/json",
        )
    except Exception as e:
        logging.exception("Falha em /transcrever")
        return func.HttpResponse(json.dumps({"erro": str(e)}), mimetype="application/json", status_code=500)

def _formatar_scores(confidence_scores) -> dict:
    """Converte os scores do SDK em um dicionário serializável."""
    return {
        "positive": round(confidence_scores.positive, 3),
        "negative": round(confidence_scores.negative, 3),
        "neutral": round(confidence_scores.neutral, 3),
    }


def _extrair_aspectos(sentiment_result) -> list[dict]:
    """
    Extrai os targets encontrados pelo Opinion Mining.

    Exemplo:
    entrega -> negative
    qualidade -> positive
    """
    aspectos = []
    encontrados = set()

    for sentence in sentiment_result.sentences:
        for opinion in sentence.mined_opinions:
            target = opinion.target

            chave = (
                target.text.strip().lower(),
                target.sentiment,
            )

            if chave in encontrados:
                continue

            encontrados.add(chave)

            aspectos.append({
                "texto": target.text,
                "sentimento": target.sentiment,
                "confianca": _formatar_scores(
                    target.confidence_scores
                ),
                "avaliacoes": [
                    {
                        "texto": assessment.text,
                        "sentimento": assessment.sentiment,
                        "confianca": _formatar_scores(
                            assessment.confidence_scores
                        ),
                    }
                    for assessment in opinion.assessments
                ],
            })

    return aspectos


def _gerar_resumos(
    text_analytics_client: TextAnalyticsClient,
    documentos: list[str],
) -> list[str | None]:
    """
    Gera resumo extractive de uma frase apenas para textos
    com mais de 300 caracteres.

    A posição dos resultados permanece alinhada à lista original.
    """
    resumos: list[str | None] = [None] * len(documentos)

    indices_longos = [
        indice
        for indice, documento in enumerate(documentos)
        if len(documento) > 300
    ]

    if not indices_longos:
        return resumos

    documentos_longos = [
        documentos[indice]
        for indice in indices_longos
    ]

    poller = text_analytics_client.begin_analyze_actions(
        documents=documentos_longos,
        language="pt",
        actions=[
            ExtractiveSummaryAction(
                max_sentence_count=1,
                order_by="Rank",
                disable_service_logs=True,
            )
        ],
    )

    resultados = poller.result()

    for indice_original, resultados_documento in zip(
        indices_longos,
        resultados,
    ):
        # Há uma única action: ExtractiveSummaryAction.
        summary_result = resultados_documento[0]

        if summary_result.is_error:
            logging.warning(
                "Falha na sumarização: %s",
                summary_result.error.message,
            )
            continue

        resumos[indice_original] = " ".join(
            sentence.text
            for sentence in summary_result.sentences
        )

    return resumos

@app.route(route="analisar-reviews", methods=["GET", "POST"])
def analisar_reviews(req: func.HttpRequest) -> func.HttpResponse:
    """
    Pipeline robusto de reviews:

    1. PII Detection;
    2. redação de dados pessoais;
    3. sentimento + Opinion Mining;
    4. reconhecimento de entidades;
    5. resumo de uma frase para reviews > 300 caracteres;
    6. persistência estruturada no MongoDB.
    """
    try:
        limit = int(req.params.get("limit", "10"))
        limit = max(1, min(limit, 100))
    except ValueError:
        return func.HttpResponse(
            json.dumps({
                "erro": "O parâmetro limit deve ser um número inteiro."
            }),
            mimetype="application/json",
            status_code=400,
        )

    mongo = None

    try:
        from pymongo import MongoClient

        # Banco de documentos do laboratório.
        mongo = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
        )

        collection = mongo["qc-db"]["reviews"]

        # Permite reprocessar os documentos do Lab 3,
        # que já têm sentimento_label, mas ainda não possuem processado_em.
        items = list(
            collection.find({
                "processado_em": {"$exists": False}
            }).limit(limit)
        )

        if not items:
            return func.HttpResponse(
                json.dumps({
                    "mensagem": "Nenhuma review pendente para processar."
                }),
                mimetype="application/json",
            )

        text_analytics_client = TextAnalyticsClient(
            endpoint=AI_ENDPOINT,
            credential=_credential,
        )

        resultados_processados = []
        erros = []

        # Mantém lotes pequenos, seguindo o padrão do laboratório.
        batch_size = 5

        for inicio in range(0, len(items), batch_size):
            batch_items = items[inicio:inicio + batch_size]

            textos_originais = [
                item["texto"]
                for item in batch_items
            ]

            # ---------------------------------------------------------
            # 1. PII Detection antes das demais análises
            # ---------------------------------------------------------
            pii_results = (
                text_analytics_client.recognize_pii_entities(
                    textos_originais,
                    language="pt",
                    disable_service_logs=True,
                )
            )

            reviews_validas = []

            for item, pii_result in zip(
                batch_items,
                pii_results,
            ):
                if pii_result.is_error:
                    erros.append({
                        "id": item.get("id"),
                        "etapa": "pii_detection",
                        "erro": pii_result.error.message,
                    })

                    # Fail closed: texto não anonimizado não segue
                    # para as outras operações.
                    continue

                reviews_validas.append({
                    "item": item,
                    "texto_redacted": pii_result.redacted_text,
                    "pii_result": pii_result,
                })

            if not reviews_validas:
                continue

            textos_redacted = [
                review["texto_redacted"]
                for review in reviews_validas
            ]

            # ---------------------------------------------------------
            # 2. Sentimento + Opinion Mining
            # ---------------------------------------------------------
            sentiment_results = (
                text_analytics_client.analyze_sentiment(
                    textos_redacted,
                    language="pt",
                    show_opinion_mining=True,
                    disable_service_logs=True,
                )
            )

            # ---------------------------------------------------------
            # 3. Entidades no texto já anonimizado
            # ---------------------------------------------------------
            entity_results = (
                text_analytics_client.recognize_entities(
                    textos_redacted,
                    language="pt",
                    disable_service_logs=True,
                )
            )

            # ---------------------------------------------------------
            # 4. Resumo apenas para textos > 300 caracteres
            # ---------------------------------------------------------
            resumos = _gerar_resumos(
                text_analytics_client,
                textos_redacted,
            )

            # ---------------------------------------------------------
            # 5. Persistência estruturada
            # ---------------------------------------------------------
            for review, sentiment, entities, resumo in zip(
                reviews_validas,
                sentiment_results,
                entity_results,
                resumos,
            ):
                item = review["item"]
                pii_result = review["pii_result"]

                if sentiment.is_error:
                    erros.append({
                        "id": item.get("id"),
                        "etapa": "sentiment",
                        "erro": sentiment.error.message,
                    })
                    continue

                if entities.is_error:
                    erros.append({
                        "id": item.get("id"),
                        "etapa": "entities",
                        "erro": entities.error.message,
                    })
                    continue

                processado_em = (
                    datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )

                update = {
                    "texto_redacted": review["texto_redacted"],

                    "sentimento_label": sentiment.sentiment,

                    "sentimento_score": _formatar_scores(
                        sentiment.confidence_scores
                    ),

                    "aspectos": _extrair_aspectos(
                        sentiment
                    ),

                    "entidades": [
                        {
                            "texto": entity.text,
                            "categoria": entity.category,
                            "subcategoria": entity.subcategory,
                            "confianca": round(
                                entity.confidence_score,
                                3,
                            ),
                        }
                        for entity in entities.entities
                    ],

                    # Apenas categorias de PII, sem replicar
                    # e-mail, CPF ou telefone em outros campos.
                    "pii_categorias": sorted({
                        pii_entity.category
                        for pii_entity in pii_result.entities
                    }),

                    "resumo": resumo,
                    "processado_em": processado_em,
                }

                collection.update_one(
                    {"_id": item["_id"]},
                    {"$set": update},
                )

                resultados_processados.append({
                    "id": item.get("id", str(item["_id"])),
                    "produto_id": item.get("produto_id"),
                    "texto": item.get("texto"),
                    **update,
                })

        return func.HttpResponse(
            json.dumps(
                {
                    "total_encontradas": len(items),
                    "total_processadas": len(
                        resultados_processados
                    ),
                    "total_erros": len(erros),
                    "resultados": resultados_processados,
                    "erros": erros,
                },
                ensure_ascii=False,
            ),
            mimetype="application/json",
        )

    except Exception as error:
        logging.exception(
            "Falha no pipeline robusto de reviews"
        )

        return func.HttpResponse(
            json.dumps(
                {"erro": str(error)},
                ensure_ascii=False,
            ),
            mimetype="application/json",
            status_code=500,
        )

    finally:
        if mongo is not None:
            mongo.close()


@app.route(route="analisar-imagem", methods=["GET", "POST"])
def analisar_imagem(req: func.HttpRequest) -> func.HttpResponse:
    """
    Analisa imagem do Blob com Vision 4.0 (Tags + OCR + Objects) via MI.
    GET /api/analisar-imagem?blob=produto.jpg
    """
    blob_name = req.params.get("blob", "produto.jpg")
    container = req.params.get("container", "imagens")

    try:
        from azure.ai.vision.imageanalysis import ImageAnalysisClient
        from azure.ai.vision.imageanalysis.models import VisualFeatures

        # 1. Baixar imagem do Blob via MI
        blob_client = _blob_service.get_blob_client(container=container, blob=blob_name)
        image_data = blob_client.download_blob().readall()

        # 2. Vision 4.0 via MI
        vision_client = ImageAnalysisClient(endpoint=AI_ENDPOINT, credential=_credential)

        # Caption não disponível em eastus2 — usar DENSE_CAPTIONS em eastus/westus2/westeurope
        result = vision_client.analyze(
            image_data=image_data,
            visual_features=[VisualFeatures.TAGS, VisualFeatures.READ, VisualFeatures.OBJECTS],
        )

        tags = [{"name": t.name, "confidence": round(t.confidence, 3)} for t in (result.tags.list if result.tags else [])]
        texto_extraido = ""
        if result.read:
            texto_extraido = "\n".join(line.text for block in result.read.blocks for line in block.lines)

        objetos = []
        if result.objects and result.objects.list:
            for obj in result.objects.list:
                box = obj.bounding_box
                objetos.append({"label": obj.tags[0].name if obj.tags else "obj",
                                 "box": {"x": box.x, "y": box.y, "w": box.width, "h": box.height}})

        return func.HttpResponse(
            json.dumps({"caption": "", "tags": tags[:10], "texto_extraido": texto_extraido,
                        "objetos_detectados": objetos, "blob": blob_name}, ensure_ascii=False),
            mimetype="application/json",
        )
    except Exception as e:
        logging.exception("Falha em /analisar-imagem")
        return func.HttpResponse(json.dumps({"erro": str(e)}), mimetype="application/json", status_code=500)
