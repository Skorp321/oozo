from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import json
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from typing import List
import logging
import asyncio
import time

from ..schemas import (
    QueryRequest,
    QueryResponse,
    Source,
    LogsResponse,
    LogEntry,
)
from ..rag_system import rag_system
from ..logger import qa_logger

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Обработка запроса пользователя с использованием RAG системы
    """
    start_time = time.time()
    error_message = None
    
    try:
        logger.info(f"Получен запрос: {request.question}")
        
        # Проверка инициализации системы
        if not rag_system._initialized:
            error_message = "RAG система не инициализирована"
            raise HTTPException(
                status_code=503,
                detail=error_message
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
        error_message = f"Ошибка при обработке запроса: {e}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )
    finally:
        # Логируем вопрос и ответ
        processing_time = time.time() - start_time
        if 'response' in locals():
            qa_logger.log_qa(request, response, processing_time, error_message)
            logger.info(f"[QUERY] Логирование завершено. Ответ: {len(response.answer)} символов, ошибка: {error_message}")
        else:
            # Если ответ не был создан, логируем только вопрос с ошибкой
            qa_logger.log_qa(request, QueryResponse(question=request.question, answer=""), processing_time, error_message)
            logger.warning(f"[QUERY] Логирование с пустым ответом из-за ошибки: {error_message}") 


@router.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    """
    Потоковая генерация ответа. Возвращает SSE-поток (text/event-stream)
    с чанками токенов по мере генерации.
    """
    start_time = time.time()
    error_message = None
    answer_parts = []
    sources_count = 0
    response_generated = False
    
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
            """
            Ты - помощник по юридическим вопросам. Используй предоставленные части контекста из юридических документов, чтобы дать точный и полезный ответ на вопрос пользователя.

            Важные правила:

            Отвечай только на основе предоставленного контекста.
            Если в контексте нет информации для ответа, честно скажи об этом.
            Не придумывай информацию, которой нет в контексте.
            Давай четкие и структурированные ответы.
            Контекст:
            “”"
            {context}
            “”"

            Вопрос:
            “”"
            {question}
            “”"

            Ответ:"""
        )

        final_prompt = template.format(context=context_text, question=request.question)
        logger.info(
            "[STREAM] prompt prepared. context_chars=%s, question_chars=%s",
            len(context_text), len(request.question or ""),
        )

        # Настройка LLM c потоковой отдачей (используем те же параметры, что и в системе)
        repo_id = "library/qwen3:32b"
        logger.info("[STREAM] initializing ChatOpenAI(streaming=True) ...")
        llm = ChatOpenAI(
            openai_api_key="dummy_key",
            openai_api_base="https://10f9698e-46b7-4a33-be37-f6495989f01f.modelrun.inference.cloud.ru/v1",
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
                sources_count = len(sources_payload)
                logger.info("[STREAM] подготовлено %s источников для отправки", sources_count)
            except Exception as e:
                logger.warning("[STREAM] не удалось подготовить sources для SSE: %s", e)

            def produce_tokens():
                nonlocal response_generated
                try:
                    token_count = 0
                    for chunk in llm.stream([HumanMessage(content=final_prompt)]):
                        text = getattr(chunk, "content", None) or ""
                        if text:
                            token_count += 1
                            answer_parts.append(text)  # Собираем части ответа для логирования
                            response_generated = True  # Отмечаем, что ответ начал генерироваться
                            if token_count <= 5 or token_count % 10 == 0:
                                logger.info(
                                    "[STREAM] chunk #%s len=%s preview='%s'",
                                    token_count, len(text), text[:20].replace("\n", " ")
                                )
                            loop.call_soon_threadsafe(queue.put_nowait, ("token", text))
                    logger.info("[STREAM] completed. total_chunks=%s", token_count)
                    # processing_time = time.time() - start_time
                    # full_answer = "".join(answer_parts) if answer_parts else ""
                    
                    # # Логируем только если был сгенерирован ответ или произошла ошибка
                    # if response_generated:
                    #     qa_logger.log_stream_qa(
                    #         question=request.question,
                    #         answer=full_answer,
                    #         sources_count=sources_count,
                    #         processing_time=processing_time,
                    #         error=None
                    #     )
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
                except Exception as e:
                    error_message = str(e)
                    logger.error("[STREAM] error while streaming: %s", error_message)
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", error_message))
                finally:
                    processing_time = time.time() - start_time
                    full_answer = "".join(answer_parts) if answer_parts else ""
                    error_message = None
                    # Логируем только если был сгенерирован ответ или произошла ошибка
                    if response_generated or error_message:
                        qa_logger.log_stream_qa(
                            question=request.question,
                            answer=full_answer.split('</think>')[-1].strip(),
                            sources_count=sources_count,
                            processing_time=processing_time,
                            error=error_message
                        )
                    answer_text = full_answer.split('</think>')[-1].strip()
                    logger.info(f"[STREAM] Логирование завершено. Ответ: {len(answer_text)} символов, ошибка: {error_message}")

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
        error_message = f"Внутренняя ошибка сервера: {str(e)}"
        raise HTTPException(status_code=500, detail=error_message)
    finally:
        # Логируем потоковый вопрос и ответ
        try:
            processing_time = time.time() - start_time
            full_answer = "".join(answer_parts) if answer_parts else ""
            
            # Логируем только если был сгенерирован ответ или произошла ошибка
            if response_generated or error_message:
                qa_logger.log_stream_qa(
                    question=request.question,
                    answer=full_answer,
                    sources_count=sources_count,
                    processing_time=processing_time,
                    error=error_message
                )
                logger.info(f"[STREAM] Логирование завершено. Ответ: {len(full_answer)} символов, ошибка: {error_message}")
            else:
                logger.warning("[STREAM] Пропуск логирования - ответ не был сгенерирован")
        except Exception as e:
            logger.error(f"[STREAM] Ошибка при логировании: {e}")


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


@router.get("/api/logs", response_model=LogsResponse)
async def get_logs(limit: int = Query(100, description="Максимальное количество записей")):
    """
    Получение логов вопросов и ответов
    """
    try:
        logs = qa_logger.get_logs(limit=limit)
        
        # Преобразуем в Pydantic модели
        log_entries = []
        for log in logs:
            try:
                log_entry = LogEntry(**log)
                log_entries.append(log_entry)
            except Exception as e:
                logger.warning(f"Ошибка при парсинге лога: {e}")
                continue
        
        return LogsResponse(
            logs=log_entries,
            total_count=len(log_entries)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении логов: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении логов: {str(e)}"
        )


@router.delete("/api/logs")
async def clear_logs():
    """
    Очистка всех логов
    """
    try:
        qa_logger.clear_logs()
        return {"message": "Логи успешно очищены"}
        
    except Exception as e:
        logger.error(f"Ошибка при очистке логов: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при очистке логов: {str(e)}"
        )
