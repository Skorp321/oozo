"""
Базовый класс для MCP инструментов
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class MCPTool(ABC):
    """
    Базовый класс для всех MCP инструментов
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя инструмента"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Описание инструмента"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema для входных параметров"""
        pass
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение инструмента
        
        Args:
            params: Параметры инструмента
            
        Returns:
            Результат выполнения
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование инструмента в словарь для MCP протокола
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }
