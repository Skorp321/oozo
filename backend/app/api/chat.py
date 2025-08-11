from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import json
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from typing import List
import logging
import asyncio

from ..schemas import (
    QueryRequest,
    QueryResponse,
    Source,
    TaskCreateResponse,
    TaskStatusResponse,
    TaskStatus,
)
from ..rag_system import rag_system
from ..task_manager import create_async_task, get_task_status

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Обработка запроса пользователя с использованием RAG системы
    """
    try:
        logger.info(f"Получен запрос: {request.question}")
        
        # Проверка инициализации системы
        if not rag_system._initialized:
            raise HTTPException(
                status_code=503,
                detail="RAG система не инициализирована"
            )
        
        # Выполнение запроса
        result = rag_system.query(
            question=request.question,
            return_sources=request.return_sources
        )
        
        # Формирование ответа
        response = QueryResponse(
            question=request.question,
            answer=result["answer"],
            sources=None
        )
        
        # Добавление источников если запрошено
        if request.return_sources and result.get("sources"):
            sources = []
            for source_data in result["sources"]:
                source = Source(
                    title=source_data["title"],
                    content=source_data["content"],
                    score=source_data["score"],
                    metadata=source_data.get("metadata")
                )
                sources.append(source)
            response.sources = sources
        
        logger.info(f"Запрос обработан успешно")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        ) 


@router.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    """
    Потоковая генерация ответа. Возвращает SSE-поток (text/event-stream)
    с чанками токенов по мере генерации.
    """
    try:
        logger.info(
            "[STREAM] POST /api/query/stream: received. question_len=%s, return_sources=%s",
            len(request.question or ""), request.return_sources,
        )

        if not rag_system._initialized:
            raise HTTPException(status_code=503, detail="RAG система не инициализирована")

        # Формируем контекст из наиболее релевантных документов (в executor)
        source_documents = []
        if rag_system.vector_store:
            try:
                loop = asyncio.get_running_loop()
                source_documents = await loop.run_in_executor(
                    None, lambda: rag_system.vector_store.similarity_search(request.question, k=5)
                )
                logger.info("[STREAM] retrieved %s source documents for context", len(source_documents))
                for i, doc in enumerate(source_documents):
                    logger.info("[STREAM] doc %s: content_len=%s, metadata=%s", i, len(getattr(doc, 'page_content', '')), getattr(doc, 'metadata', {}))
            except Exception as e:
                logger.warning("[STREAM] similarity_search failed: %s", e)
                source_documents = []

        context_parts = []
        for doc in source_documents or []:
            try:
                context_parts.append(doc.page_content)
            except Exception:
                continue
        context_text = "\n\n".join(context_parts)

        template = (
            "Ты - помощник по юридическим вопросам. Используй следующие части контекста из юридических документов, чтобы дать точный и полезный ответ на вопрос пользователя.\n\n"
            "Важные правила:\n"
            "1. Отвечай только на основе предоставленного контекста\n"
            "2. Если в контексте нет информации для ответа, честно скажи об этом\n"
            "3. Не придумывай информацию, которой нет в контексте\n"
            "4. Давай четкие и структурированные ответы\n"
            "5. При необходимости цитируй соответствующие части контекста\n\n"
            "Контекст: {context}\n\n"
            "Вопрос: {question}\n\n"
            "Ответ:"
        )

        final_prompt = template.format(context=context_text, question=request.question)
        logger.info(
            "[STREAM] prompt prepared. context_chars=%s, question_chars=%s",
            len(context_text), len(request.question or ""),
        )

        # Настройка LLM c потоковой отдачей (используем те же параметры, что и в системе)
        repo_id = "model-run-vekow-trunk"
        logger.info("[STREAM] initializing ChatOpenAI(streaming=True) ...")
        llm = ChatOpenAI(
            openai_api_key="dummy_key",
            openai_api_base="https://565df812-6798-4e3d-9a62-18d67e029d53.modelrun.inference.cloud.ru/v1",
            model=repo_id,
            temperature=0.1,
            timeout=600,
            streaming=True,
        )
        logger.info("[STREAM] ChatOpenAI ready, starting token stream")

        def sse_format(data: dict | str) -> bytes:
            if isinstance(data, dict):
                payload = json.dumps(data, ensure_ascii=False)
            else:
                payload = str(data)
            return (f"data: {payload}\n\n").encode("utf-8")

        async def token_stream_async():
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()

            # Подготовим и отправим источники (чанки) отдельным событием до начала токенов
            sources_payload = []
            try:
                def make_jsonable(value):
                    try:
                        import collections.abc as cabc
                    except Exception:
                        cabc = None
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        return value
                    if isinstance(value, dict):
                        return {str(k): make_jsonable(v) for k, v in value.items()}
                    if cabc and isinstance(value, cabc.Sequence) and not isinstance(value, (str, bytes, bytearray)):
                        return [make_jsonable(v) for v in value]
                    return str(value)

                for doc in source_documents or []:
                    try:
                        metadata = getattr(doc, "metadata", {}) or {}
                        jsonable_metadata = make_jsonable(metadata)
                        sources_payload.append({
                            "title": (metadata.get("title") if isinstance(metadata, dict) else None) or "Неизвестный источник",
                            "content": getattr(doc, "page_content", ""),
                            "score": 1.0,
                            "metadata": jsonable_metadata,
                        })
                    except Exception as e:
                        logger.debug("[STREAM] пропущен source из-за ошибки сериализации: %s", e)
                        continue
                logger.info("[STREAM] подготовлено %s источников для отправки", len(sources_payload))
            except Exception as e:
                logger.warning("[STREAM] не удалось подготовить sources для SSE: %s", e)

            def produce_tokens():
                try:
                    token_count = 0
                    for chunk in llm.stream([HumanMessage(content=final_prompt)]):
                        text = getattr(chunk, "content", None) or ""
                        if text:
                            token_count += 1
                            if token_count <= 5 or token_count % 10 == 0:
                                logger.info(
                                    "[STREAM] chunk #%s len=%s preview='%s'",
                                    token_count, len(text), text[:20].replace("\n", " ")
                                )
                            loop.call_soon_threadsafe(queue.put_nowait, ("token", text))
                    logger.info("[STREAM] completed. total_chunks=%s", token_count)
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
                except Exception as e:
                    logger.error("[STREAM] error while streaming: %s", e)
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

            # Сначала отправляем sources синхронно, чтобы они были первыми
            if len(sources_payload) > 0:
                logger.info("[STREAM] отправляем sources event с %s источниками в начале потока", len(sources_payload))
                yield sse_format({"sources": sources_payload})

            # Запускаем продюсера в пуле потоков
            _ = loop.run_in_executor(None, produce_tokens)

            while True:
                kind, payload = await queue.get()
                if kind == "token":
                    yield sse_format({"token": payload})
                elif kind == "sources":
                    # Эта ветка больше не нужна, так как sources отправляются синхронно выше
                    logger.info("[STREAM] получен sources event в очереди (пропускаем, уже отправлено)")
                    continue
                elif kind == "error":
                    yield sse_format({"error": payload})
                    break
                elif kind == "done":
                    yield sse_format("[DONE]")
                    break

        return StreamingResponse(token_stream_async(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@router.get("/api/query/stream")
async def query_stream_get(question: str = Query(..., description="Пользовательский вопрос")):
    """
    Потоковая генерация через GET для совместимости с EventSource.
    Поведение идентично POST /api/query/stream, но вопрос передаётся как query-параметр.
    """
    try:
        req = QueryRequest(question=question, return_sources=False)
        return await query_stream(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
