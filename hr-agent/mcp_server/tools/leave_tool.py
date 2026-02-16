"""
Инструменты для работы с отпусками
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Добавляем путь к backend для импорта
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.hr_data import get_personal_days, get_remaining_vacation_days
from .tool_base import MCPTool

logger = logging.getLogger(__name__)


class GetPersonalDaysTool(MCPTool):
    """
    Инструмент для получения персональных дней отпуска сотрудника
    """
    
    @property
    def name(self) -> str:
        return "get_personal_days"
    
    @property
    def description(self) -> str:
        return "Получить количество персональных дней отпуска для указанного сотрудника. Персональные дни - это дополнительные дни отпуска, предоставляемые сотруднику помимо основного отпуска."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_name": {
                    "type": "string",
                    "description": "Имя сотрудника (например: alice, bob, charlie)"
                }
            },
            "required": ["employee_name"]
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получить персональные дни сотрудника
        
        Args:
            params: Словарь с параметром "employee_name"
            
        Returns:
            Информация о персональных днях
        """
        employee_name = params.get("employee_name")
        if not employee_name:
            return {
                "error": "Параметр 'employee_name' обязателен",
                "employee_name": None,
                "personal_days": None
            }
        
        try:
            logger.info(f"Запрос персональных дней для сотрудника: {employee_name}")
            personal_days = get_personal_days(employee_name)
            
            return {
                "employee_name": employee_name,
                "personal_days": personal_days,
                "message": f"У сотрудника {employee_name} {personal_days} персональных дней отпуска"
            }
            
        except ValueError as e:
            logger.warning(f"Сотрудник не найден: {employee_name}")
            return {
                "error": str(e),
                "employee_name": employee_name,
                "personal_days": None,
                "message": f"Сотрудник '{employee_name}' не найден в системе"
            }
        except Exception as e:
            logger.error(f"Ошибка при получении персональных дней: {e}")
            return {
                "error": str(e),
                "employee_name": employee_name,
                "personal_days": None
            }


class GetRemainingVacationDaysTool(MCPTool):
    """
    Инструмент для получения оставшихся дней отпуска сотрудника
    """
    
    @property
    def name(self) -> str:
        return "get_remaining_vacation_days"
    
    @property
    def description(self) -> str:
        return "Получить количество оставшихся дней основного отпуска для указанного сотрудника. Возвращает разницу между общим количеством дней отпуска и уже использованными днями."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "employee_name": {
                    "type": "string",
                    "description": "Имя сотрудника (например: alice, bob, charlie)"
                }
            },
            "required": ["employee_name"]
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получить оставшиеся дни отпуска сотрудника
        
        Args:
            params: Словарь с параметром "employee_name"
            
        Returns:
            Информация об оставшихся днях отпуска
        """
        employee_name = params.get("employee_name")
        if not employee_name:
            return {
                "error": "Параметр 'employee_name' обязателен",
                "employee_name": None,
                "remaining_vacation_days": None
            }
        
        try:
            logger.info(f"Запрос оставшихся дней отпуска для сотрудника: {employee_name}")
            remaining_days = get_remaining_vacation_days(employee_name)
            
            return {
                "employee_name": employee_name,
                "remaining_vacation_days": remaining_days,
                "message": f"У сотрудника {employee_name} осталось {remaining_days} дней отпуска"
            }
            
        except ValueError as e:
            logger.warning(f"Сотрудник не найден: {employee_name}")
            return {
                "error": str(e),
                "employee_name": employee_name,
                "remaining_vacation_days": None,
                "message": f"Сотрудник '{employee_name}' не найден в системе"
            }
        except Exception as e:
            logger.error(f"Ошибка при получении оставшихся дней отпуска: {e}")
            return {
                "error": str(e),
                "employee_name": employee_name,
                "remaining_vacation_days": None
            }
