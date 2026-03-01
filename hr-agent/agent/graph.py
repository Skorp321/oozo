"""
LangGraph React агент для HR системы
"""
import logging
import os
from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

import sys
from pathlib import Path

# Добавляем путь к backend для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tools import get_available_tools
from backend.config import settings

logger = logging.getLogger(__name__)
_tracing_initialized = False
_tracer_provider = None


# Системный промпт для HR ассистента
SYSTEM_PROMPT = """Ты - полезный HR ассистент, который помогает сотрудникам с вопросами об отпусках, документации компании и корпоративных политиках.

Твои возможности:
1. Получение информации о персональных днях отпуска сотрудников
2. Получение информации об оставшихся днях основного отпуска
3. Поиск информации в корпоративных документах с помощью RAG

Важные правила:
- Всегда будь вежливым и профессиональным
- Если не знаешь ответа, используй инструмент rag_query для поиска в документах
- Для вопросов об отпусках используй соответствующие инструменты (get_personal_days, get_remaining_vacation_days)
- Отвечай на русском языке
- Если инструмент вернул ошибку, объясни пользователю что произошло

Используй инструменты когда это необходимо для ответа на вопрос пользователя."""


def _setup_phoenix_tracing() -> None:
    global _tracing_initialized, _tracer_provider
    if _tracing_initialized:
        return
    _tracing_initialized = True

    if not settings.phoenix_enabled:
        logger.info("Phoenix tracing выключен (PHOENIX_ENABLED=false)")
        return

    endpoint = (settings.phoenix_endpoint or "").strip()
    protocol = (settings.phoenix_protocol or "auto").strip().lower()
    if not endpoint:
        logger.warning("Phoenix tracing пропущен: пустой PHOENIX_ENDPOINT")
        return

    if protocol == "auto":
        protocol = "http/protobuf" if endpoint.startswith(("http://", "https://")) else "grpc"

    try:
        project_name = os.getenv("PHOENIX_PROJECT_NAME", settings.phoenix_project_name or "hr-agent")
        headers = {"api_key": settings.phoenix_api_key} if settings.phoenix_api_key else None
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": project_name,
                    "project.name": project_name,
                }
            )
        )
        trace.set_tracer_provider(provider)

        if protocol == "http/protobuf":
            if not endpoint.startswith(("http://", "https://")):
                endpoint = f"http://{endpoint}"
            if not endpoint.rstrip("/").endswith("/v1/traces"):
                endpoint = f"{endpoint.rstrip('/')}/v1/traces"
            exporter = OTLPHTTPSpanExporter(endpoint=endpoint, headers=headers)
        else:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPGRPCSpanExporter

            grpc_endpoint = endpoint if endpoint.startswith(("http://", "https://")) else f"http://{endpoint}"
            exporter = OTLPGRPCSpanExporter(
                endpoint=grpc_endpoint,
                headers=headers,
                insecure=grpc_endpoint.startswith("http://"),
            )

        provider.add_span_processor(BatchSpanProcessor(exporter))
        _tracer_provider = provider

        # Даёт автоматические спаны для вызовов LangChain/LangGraph.
        LangChainInstrumentor().instrument()
        logger.info("Phoenix tracing включен: protocol=%s endpoint=%s", protocol, endpoint)
    except Exception as exc:
        logger.warning("Не удалось инициализировать Phoenix tracing: %s", exc)


def _flush_tracing() -> None:
    try:
        if _tracer_provider and hasattr(_tracer_provider, "force_flush"):
            _tracer_provider.force_flush(timeout_millis=3000)
    except Exception:
        # Flush не должен ломать основной флоу ответа пользователю.
        pass


def create_hr_agent():
    """
    Создание LangGraph React агента для HR системы
    
    Returns:
        Скомпилированный граф агента
    """
    _setup_phoenix_tracing()

    # Настройка LLM
    repo_id = settings.openai_model_name or "model-run-vekow-trunk"
    api_base = settings.openai_api_base or "https://10f9698e-46b7-4a33-be37-f6495989f01f.modelrun.inference.cloud.ru/v1"
    
    llm = ChatOpenAI(
        openai_api_key=settings.openai_api_key,
        openai_api_base=api_base,
        model=repo_id,
        temperature=settings.temperature,
        timeout=600
    )
    
    tools = get_available_tools()

    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    
    logger.info("HR агент создан успешно")
    return agent


# Глобальный экземпляр агента
_agent = None


def get_agent():
    """
    Получить или создать экземпляр агента
    
    Returns:
        Скомпилированный граф агента
    """
    global _agent
    if _agent is None:
        _agent = create_hr_agent()
    return _agent


def invoke_agent(user_message: str) -> str:
    """
    Вызвать агента с сообщением пользователя
    
    Args:
        user_message: Сообщение пользователя
        
    Returns:
        Ответ агента
    """
    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("hr_agent.invoke_agent") as span:
            span.set_attribute("input.length", len(user_message))
            span.set_attribute("input.preview", user_message[:200])

            agent = get_agent()
            
            # Создаем входное состояние для агента
            input_state = {
                "messages": [HumanMessage(content=user_message)]
            }
            
            logger.info(f"Обработка запроса пользователя: {user_message[:100]}...")
            
            # Вызываем агента
            result = agent.invoke(input_state)
            
            # Извлекаем последнее сообщение от агента
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, AIMessage):
                    output = last_message.content
                    span.set_attribute("output.length", len(output or ""))
                    return output
                elif hasattr(last_message, "content"):
                    output = str(last_message.content)
                    span.set_attribute("output.length", len(output))
                    return output
            
            return "Не удалось получить ответ от агента"
    except Exception as e:
        logger.error(f"Ошибка при вызове агента: {e}")
        return f"Произошла ошибка при обработке запроса: {str(e)}"
    finally:
        _flush_tracing()
