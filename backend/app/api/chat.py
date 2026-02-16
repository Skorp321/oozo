import os
from fastapi import APIRouter, HTTPException, Query, Request, Header
from fastapi.responses import StreamingResponse
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from typing import List, Optional
import logging
import asyncio
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import func, case, and_

from ..schemas import (
    QueryRequest,
    QueryResponse,
    Source,
    LogsResponse,
    LogEntry,
    FeedbackRequest,
    FeedbackResponse,
    AdminHrReportResponse,
    AdminHrRow,
    AdminHrHourlyStat,
    AdminHrDailyStat,
)
from ..rag_system import rag_system
from ..logger import qa_logger
from ..models import ResponseFeedback, QueryLog, query_log_chunks
from ..database import get_db_session


load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)
router = APIRouter()


def get_client_ip(request: Request) -> str:
    """
    Получает IP адрес клиента из запроса
    """
    # Проверяем заголовки прокси
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Берем первый IP из списка
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Используем клиентский IP
    if request.client:
        return request.client.host
    
    return "unknown"


def get_user_login(request: Request) -> Optional[str]:
    """
    Получает логин пользователя из заголовков или запроса
    """
    # Можно добавить заголовок X-User-Login или использовать аутентификацию
    user_login = request.headers.get("X-User-Login")
    if user_login:
        return user_login
    
    # Если есть Authorization заголовок, можно извлечь логин из токена
    # Здесь можно добавить логику извлечения из JWT токена
    
    return None


def get_user_timezone(request: Request) -> Optional[str]:
    """
    Получает временную зону пользователя из заголовков запроса
    """
    # Проверяем заголовок X-User-Timezone
    user_timezone = request.headers.get("X-User-Timezone")
    if user_timezone:
        return user_timezone
    
    # Если заголовок не указан, возвращаем None
    return None


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest, http_request: Request):
    """
    Обработка запроса пользователя с использованием RAG системы
    """
    start_time = time.time()
    error_message = None
    
    # Получаем IP, логин и timezone пользователя
    user_ip = get_client_ip(http_request)
    user_login = get_user_login(http_request)
    user_timezone = get_user_timezone(http_request)
    
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
        if 'response' in locals() and 'result' in locals():
            chunk_ids_to_log = result.get("chunk_ids")
            logger.info(f"[QUERY] Передаем chunk_ids в логгер: {chunk_ids_to_log}")
            qa_logger.log_qa(
                request, 
                response, 
                processing_time, 
                error_message,
                user_login=user_login,
                user_ip=user_ip,
                final_prompt=result.get("final_prompt"),
                chunk_ids=chunk_ids_to_log,
                user_timezone=user_timezone
            )
            logger.info(f"[QUERY] Логирование завершено. Ответ: {len(response.answer)} символов, ошибка: {error_message}")
        else:
            # Если ответ не был создан, логируем только вопрос с ошибкой
            qa_logger.log_qa(
                request, 
                QueryResponse(question=request.question, answer=""), 
                processing_time, 
                error_message,
                user_login=user_login,
                user_ip=user_ip,
                user_timezone=user_timezone
            )
            logger.warning(f"[QUERY] Логирование с пустым ответом из-за ошибки: {error_message}") 


@router.post("/api/query/stream")
async def query_stream(request: QueryRequest, http_request: Request):
    """
    Потоковая генерация ответа. Возвращает SSE-поток (text/event-stream)
    с чанками токенов по мере генерации.
    """
    start_time = time.time()
    error_message = None
    answer_parts = []
    sources_count = 0
    response_generated = False
    
    # Получаем IP, логин и timezone пользователя
    user_ip = get_client_ip(http_request)
    user_login = get_user_login(http_request)
    user_timezone = get_user_timezone(http_request)
    chunk_ids = []
    final_prompt = None
    
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
                    None, lambda: rag_system.retrieve_documents(request.question, k=5)
                )
                embeddings_kind = (
                    type(rag_system.embeddings).__name__
                    if getattr(rag_system, "embeddings", None)
                    else "unknown"
                )
                logger.info(
                    "[STREAM] retrieved %s source documents for context (embedder=%s)",
                    len(source_documents),
                    embeddings_kind,
                )
                for i, doc in enumerate(source_documents):
                    logger.info("[STREAM] doc %s: content_len=%s, metadata=%s", i, len(getattr(doc, 'page_content', '')), getattr(doc, 'metadata', {}))

                    if hasattr(doc, 'metadata') and doc.metadata:
                        db_id = doc.metadata.get("db_id")
                        if db_id:
                            chunk_ids.append(db_id)
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
        repo_id = os.getenv("OPENAI_MODEL_NAME")
        logger.info("[STREAM] initializing ChatOpenAI(streaming=True) ...")
        llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base="https://foundation-models.api.cloud.ru/v1",
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
                nonlocal user_login, user_ip, final_prompt, chunk_ids
                stream_error = None
                try:
                    token_count = 0
                    for chunk in llm.stream([HumanMessage(content=final_prompt)]):
                        text = getattr(chunk, "content", None) or ""
                        if text:
                            token_count += 1
                            answer_parts.append(text)  # Собираем части ответа для логирования
                            response_generated = True  # Отмечаем, что ответ начал генерироваться
                            
                            loop.call_soon_threadsafe(queue.put_nowait, ("token", text))
                    logger.info("[STREAM] completed. total_chunks=%s", token_count)
                except Exception as e:
                    stream_error = str(e)
                    logger.error("[STREAM] error while streaming: %s", stream_error)
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", stream_error))
                finally:
                    processing_time = time.time() - start_time
                    full_answer = "".join(answer_parts) if answer_parts else ""
                    query_log_id = None
                    # Логируем только если был сгенерирован ответ или произошла ошибка
                    if response_generated or stream_error:
                        query_log_id = qa_logger.log_stream_qa(
                            question=request.question,
                            answer=full_answer.split('</think>')[-1].strip(),
                            sources_count=sources_count,
                            sources_payload=sources_payload,
                            processing_time=processing_time,
                            error=stream_error,
                            user_login=user_login,
                            user_ip=user_ip,
                            final_prompt=final_prompt,
                            chunk_ids=chunk_ids if chunk_ids else None,
                            user_timezone=user_timezone
                        )
                    answer_text = full_answer.split('</think>')[-1].strip()
                    logger.info(f"[STREAM] Логирование завершено. Ответ: {len(answer_text)} символов, query_log_id: {query_log_id}, ошибка: {stream_error}")
                    if query_log_id is not None:
                        loop.call_soon_threadsafe(queue.put_nowait, ("query_log_id", query_log_id))
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

            # Сначала отправляем sources синхронно, чтобы они были первыми
            if len(sources_payload) > 0:
                logger.info("[STREAM] отправляем sources event с %s источниками в начале потока", len(sources_payload))
                yield sse_format({"sources": sources_payload})

            # Запускаем продюсера в пуле потоков
            _ = loop.run_in_executor(None, produce_tokens)

            # Таймаут ожидания: если API не закрывает стрим, через N секунд без данных считаем поток завершённым
            STREAM_IDLE_TIMEOUT = 90  # меньше, чем read timeout на фронте (120с)
            while True:
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=STREAM_IDLE_TIMEOUT)
                except asyncio.TimeoutError:
                    logger.warning(
                        "[STREAM] Таймаут ожидания ответа от LLM (%.0f с). API не закрыл стрим. Отправляем [DONE] с частичным ответом.",
                        STREAM_IDLE_TIMEOUT,
                    )
                    yield sse_format("[DONE]")
                    break
                if kind == "token":
                    yield sse_format({"token": payload})
                elif kind == "sources":
                    # Эта ветка больше не нужна, так как sources отправляются синхронно выше
                    logger.info("[STREAM] получен sources event в очереди (пропускаем, уже отправлено)")
                    continue
                elif kind == "error":
                    yield sse_format({"error": payload})
                    break
                elif kind == "query_log_id":
                    if payload is not None:
                        yield sse_format({"query_log_id": payload})
                    continue
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


@router.get("/api/query/stream")
async def query_stream_get(http_request: Request, question: str = Query(..., description="Пользовательский вопрос")):
    """
    Потоковая генерация через GET для совместимости с EventSource.
    Поведение идентично POST /api/query/stream, но вопрос передаётся как query-параметр.
    """
    try:
        req = QueryRequest(question=question, return_sources=False)
        return await query_stream(req, http_request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@router.post("/api/feedback", response_model=FeedbackResponse)
async def save_feedback(body: FeedbackRequest):
    """
    Сохранение оценки ответа бота (like/dislike) в PostgreSQL. Связь с query_logs по query_log_id.
    """
    if body.feedback not in ("like", "dislike"):
        raise HTTPException(status_code=400, detail="feedback должен быть 'like' или 'dislike'")
    like_val = body.feedback == "like"
    dislike_val = body.feedback == "dislike"
    try:
        with get_db_session() as db:
            db.add(ResponseFeedback(
                query_log_id=body.query_log_id,
                like=like_val,
                dislike=dislike_val,
            ))
        logger.info(f"Feedback сохранён в БД: query_log_id={body.query_log_id}, like={like_val}, dislike={dislike_val}")
        return FeedbackResponse(ok=True, message="Оценка сохранена")
    except Exception as e:
        logger.error(f"Ошибка при сохранении feedback в БД: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения в БД: {str(e)}")


@router.get("/api/admin/hr-report", response_model=AdminHrReportResponse)
async def get_admin_hr_report(
    start_date: date = Query(..., description="Дата начала (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Дата окончания (YYYY-MM-DD)"),
    score_type: str = Query("all", description="all | like | dislike"),
    context_found_only: bool = Query(True, description="Только записи с найденным контекстом"),
    limit: int = Query(10, ge=1, le=500, description="Максимальное количество строк в таблице"),
):
    """
    Отчет для admin-hr страницы: метрики, табличные данные и статистика по часам.
    """
    allowed_score_types = {"all", "like", "dislike"}
    if score_type not in allowed_score_types:
        raise HTTPException(status_code=400, detail="score_type должен быть one of: all, like, dislike")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date не может быть меньше start_date")

    start_dt = datetime.combine(start_date, dt_time.min).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date + timedelta(days=1), dt_time.min).replace(tzinfo=timezone.utc)

    try:
        with get_db_session() as db:
            feedback_subq = (
                db.query(
                    ResponseFeedback.query_log_id.label("query_log_id"),
                    func.bool_or(ResponseFeedback.like).label("has_like"),
                    func.bool_or(ResponseFeedback.dislike).label("has_dislike"),
                )
                .group_by(ResponseFeedback.query_log_id)
                .subquery()
            )

            context_subq = (
                db.query(
                    query_log_chunks.c.query_log_id.label("query_log_id"),
                    func.count(query_log_chunks.c.chunk_id).label("chunk_count"),
                )
                .group_by(query_log_chunks.c.query_log_id)
                .subquery()
            )

            operation_expr = case(
                (
                    and_(
                        func.coalesce(feedback_subq.c.has_dislike, False).is_(True),
                        func.coalesce(feedback_subq.c.has_like, False).is_(False),
                    ),
                    "Dislike",
                ),
                (func.coalesce(feedback_subq.c.has_like, False).is_(True), "Like"),
                else_="Без оценки",
            )
            context_bool_expr = func.coalesce(context_subq.c.chunk_count, 0) > 0

            base_query = (
                db.query(
                    QueryLog.id.label("id"),
                    QueryLog.created_at.label("created_at"),
                    QueryLog.status.label("status"),
                    QueryLog.user_login.label("user_login"),
                    QueryLog.user_ip.label("user_ip"),
                    QueryLog.question.label("question"),
                    QueryLog.answer.label("answer"),
                    operation_expr.label("operation"),
                    context_bool_expr.label("context_found"),
                )
                .outerjoin(feedback_subq, feedback_subq.c.query_log_id == QueryLog.id)
                .outerjoin(context_subq, context_subq.c.query_log_id == QueryLog.id)
                .filter(
                    QueryLog.created_at >= start_dt,
                    QueryLog.created_at < end_dt,
                )
            )

            if score_type == "like":
                base_query = base_query.filter(func.coalesce(feedback_subq.c.has_like, False).is_(True))
            elif score_type == "dislike":
                base_query = base_query.filter(func.coalesce(feedback_subq.c.has_dislike, False).is_(True))

            if context_found_only:
                base_query = base_query.filter(context_bool_expr.is_(True))

            dataset_rows = base_query.order_by(QueryLog.created_at.asc()).all()

            total_records = len(dataset_rows)
            like_count = sum(1 for r in dataset_rows if r.operation == "Like")
            dislike_count = sum(1 for r in dataset_rows if r.operation == "Dislike")
            context_found_count = sum(1 for r in dataset_rows if r.context_found)

            def actor_key(row) -> Optional[str]:
                login = (row.user_login or "").strip() if hasattr(row, "user_login") else ""
                if login:
                    return f"login:{login}"
                ip = (row.user_ip or "").strip() if hasattr(row, "user_ip") else ""
                if ip:
                    return f"ip:{ip}"
                return None

            # DAO/MAO считаются по всем пользователям сервиса (без учета текущих фильтров отчета)
            day_start = datetime.combine(end_date, dt_time.min).replace(tzinfo=timezone.utc)
            day_end = datetime.combine(end_date + timedelta(days=1), dt_time.min).replace(tzinfo=timezone.utc)

            dao_rows = (
                db.query(
                    QueryLog.user_login.label("user_login"),
                    QueryLog.user_ip.label("user_ip"),
                )
                .filter(
                    QueryLog.created_at >= day_start,
                    QueryLog.created_at < day_end,
                )
                .all()
            )
            dao_actors = {k for k in (actor_key(r) for r in dao_rows) if k}
            dao = len(dao_actors)

            month_start = datetime(end_date.year, end_date.month, 1, tzinfo=timezone.utc)
            if end_date.month == 12:
                month_end = datetime(end_date.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                month_end = datetime(end_date.year, end_date.month + 1, 1, tzinfo=timezone.utc)

            month_query = (
                db.query(
                    QueryLog.user_login.label("user_login"),
                    QueryLog.user_ip.label("user_ip"),
                )
                .filter(
                    QueryLog.created_at >= month_start,
                    QueryLog.created_at < month_end,
                )
            )
            month_rows = month_query.all()
            mao_actors = {k for k in (actor_key(r) for r in month_rows) if k}
            mao = len(mao_actors)

            table_rows = []
            for row in dataset_rows[:limit]:
                created_at = row.created_at
                if created_at is None:
                    continue
                table_rows.append(
                    AdminHrRow(
                        id=row.id,
                        data=1000 + row.id,
                        date=created_at,
                        operation=row.operation,
                        content="Найден" if row.context_found else "Не найден",
                        status="Успешно" if row.status == "success" else "Ошибка",
                        hour=created_at.hour,
                        question=row.question,
                        answer=row.answer,
                    )
                )

            hour_buckets = [0] * 24
            for row in dataset_rows:
                created_at = row.created_at
                if created_at is not None:
                    hour_buckets[created_at.hour] += 1
            hourly_stats = [
                AdminHrHourlyStat(hour=hour, count=count)
                for hour, count in enumerate(hour_buckets)
                if count > 0
            ]

            day_buckets = {}
            for row in dataset_rows:
                created_at = row.created_at
                if created_at is None:
                    continue
                day_key = created_at.date().isoformat()
                day_buckets[day_key] = day_buckets.get(day_key, 0) + 1

            daily_stats = [
                AdminHrDailyStat(day=day, count=day_buckets[day])
                for day in sorted(day_buckets.keys())
            ]

            return AdminHrReportResponse(
                total_records=total_records,
                like_count=like_count,
                dislike_count=dislike_count,
                context_found=context_found_count,
                dao=dao,
                mao=mao,
                rows=table_rows,
                hourly_stats=hourly_stats,
                daily_stats=daily_stats,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения admin hr report: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка формирования отчета: {str(e)}")


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
