"""
Упрощенная динамическая загрузка инструментов из MCP сервера.
"""
import json
import logging
import os
from typing import Any, Dict, List

import requests
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")


def _call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{MCP_SERVER_URL}/mcp/tools/call"
    payload = {"name": tool_name, "arguments": arguments}
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()

    if result.get("isError"):
        text = result.get("content", [{}])[0].get("text", "Неизвестная ошибка")
        return {"error": text}

    text = result.get("content", [{}])[0].get("text", "")
    try:
        return json.loads(text)
    except Exception:
        return {"result": text}


def _list_mcp_tools() -> List[Dict[str, Any]]:
    url = f"{MCP_SERVER_URL}/mcp/tools/list"
    response = requests.post(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload.get("tools", [])


def _build_tool_description(tool_info: Dict[str, Any]) -> str:
    description = tool_info.get("description") or f"MCP инструмент {tool_info.get('name')}"
    input_schema = tool_info.get("inputSchema") or {}
    properties = input_schema.get("properties") or {}
    required = set(input_schema.get("required") or [])

    if not properties:
        return description

    params = []
    for name, schema in properties.items():
        type_name = (schema or {}).get("type", "any")
        req = "required" if name in required else "optional"
        params.append(f"{name}:{type_name}:{req}")

    return f"{description}. Аргументы (JSON): {', '.join(params)}"


def _parse_tool_input(tool_input: str, tool_info: Dict[str, Any]) -> Dict[str, Any]:
    input_schema = tool_info.get("inputSchema") or {}
    properties = input_schema.get("properties") or {}
    required = list(input_schema.get("required") or [])

    # 1) Если пришел JSON-объект, используем как есть.
    try:
        parsed = json.loads(tool_input)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # 2) Если ровно один обязательный параметр, кладем туда plain text.
    if len(required) == 1:
        return {required[0]: tool_input}

    # 3) Если ровно одно поле в схеме, кладем туда plain text.
    if len(properties) == 1:
        only_field = next(iter(properties.keys()))
        return {only_field: tool_input}

    raise ValueError(
        "Ожидается JSON-объект с аргументами инструмента "
        f"(например: {{...}}). Получено: {tool_input}"
    )


def _make_tool(tool_info: Dict[str, Any]) -> Tool:
    name = tool_info["name"]
    description = _build_tool_description(tool_info)

    def _runner(tool_input: str) -> str:
        try:
            arguments = _parse_tool_input(tool_input, tool_info)
            result = _call_mcp_tool(name, arguments)
            if "error" in result:
                return f"Ошибка: {result['error']}"
            if "formatted_answer" in result:
                return str(result["formatted_answer"])
            if "answer" in result:
                return str(result["answer"])
            if "message" in result:
                return str(result["message"])
            if "result" in result:
                return str(result["result"])
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return f"Ошибка: {exc}"

    return Tool(name=name, description=description, func=_runner)


def get_available_tools() -> List[Tool]:
    """
    Запрашивает список инструментов из MCP сервера и строит список Tool для модели.
    """
    tool_infos = _list_mcp_tools()
    if not tool_infos:
        raise RuntimeError("MCP вернул пустой список инструментов")

    tools: List[Tool] = []
    for tool_info in tool_infos:
        if isinstance(tool_info, dict) and "name" in tool_info:
            tools.append(_make_tool(tool_info))

    if not tools:
        raise RuntimeError("Не удалось построить инструменты из ответа MCP")

    logger.info("Подгружено инструментов из MCP: %s", len(tools))
    return tools

