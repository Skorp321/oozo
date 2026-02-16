"""
MCP Server на FastAPI
"""
import logging
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

# Добавляем путь к корню проекта для импорта backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.schemas import (
    ListToolsResponse,
    ToolCallRequest,
    ToolCallResponse,
    ToolInfo,
    HealthResponse
)
from mcp_server.tools.rag_tool import RAGTool
from mcp_server.tools.leave_tool import GetPersonalDaysTool, GetRemainingVacationDaysTool

logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title="HR Agent MCP Server",
    description="MCP сервер для HR агента с инструментами RAG и отпусков",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация инструментов
TOOLS: Dict[str, any] = {
    "rag_query": RAGTool(),
    "get_personal_days": GetPersonalDaysTool(),
    "get_remaining_vacation_days": GetRemainingVacationDaysTool(),
}


@app.get("/health", response_model=HealthResponse)
async def health():
    """Проверка здоровья сервера"""
    return HealthResponse(status="healthy", message="MCP Server is running")


@app.post("/mcp/tools/list", response_model=ListToolsResponse)
async def list_tools():
    """
    Получить список доступных инструментов
    """
    tools_info = [ToolInfo(**tool.to_dict()) for tool in TOOLS.values()]
    return ListToolsResponse(tools=tools_info)


@app.post("/mcp/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """
    Вызвать инструмент
    
    Args:
        request: Запрос на вызов инструмента
        
    Returns:
        Результат выполнения инструмента
    """
    tool_name = request.name
    
    if tool_name not in TOOLS:
        raise HTTPException(
            status_code=404,
            detail=f"Инструмент '{tool_name}' не найден"
        )
    
    tool = TOOLS[tool_name]
    
    try:
        logger.info(f"Вызов инструмента '{tool_name}' с параметрами: {request.arguments}")
        result = await tool.execute(request.arguments)
        
        # Форматируем результат в соответствии с MCP протоколом
        import json
        result_text = json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else str(result)
        
        return ToolCallResponse(
            content=[{
                "type": "text",
                "text": result_text
            }],
            isError=False
        )
    except Exception as e:
        logger.error(f"Ошибка при выполнении инструмента '{tool_name}': {e}")
        return ToolCallResponse(
            content=[{
                "type": "text",
                "text": f"Ошибка: {str(e)}"
            }],
            isError=True
        )


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "name": "HR Agent MCP Server",
        "version": "1.0.0",
        "description": "MCP сервер для HR агента",
        "endpoints": {
            "health": "/health",
            "list_tools": "/mcp/tools/list",
            "call_tool": "/mcp/tools/call"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "mcp_server.server:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
