#!/bin/bash
# Скрипт для запуска MCP сервера

cd "$(dirname "$0")"
python -m mcp_server.server
