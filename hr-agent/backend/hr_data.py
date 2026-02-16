"""
Мок-данные сотрудников и функции для работы с отпусками
"""
from typing import Dict, Optional


# Мок-данные сотрудников
EMPLOYEES: Dict[str, Dict[str, int]] = {
    "alice": {
        "personal_days": 5,
        "total_vacation_days": 30,
        "used_vacation_days": 10
    },
    "bob": {
        "personal_days": 3,
        "total_vacation_days": 28,
        "used_vacation_days": 15
    },
    "charlie": {
        "personal_days": 7,
        "total_vacation_days": 30,
        "used_vacation_days": 5
    },
    "diana": {
        "personal_days": 2,
        "total_vacation_days": 25,
        "used_vacation_days": 20
    },
    "eve": {
        "personal_days": 10,
        "total_vacation_days": 30,
        "used_vacation_days": 0
    }
}


def get_personal_days(employee_name: str) -> int:
    """
    Получить количество персональных дней отпуска для сотрудника
    
    Args:
        employee_name: Имя сотрудника
        
    Returns:
        Количество персональных дней
        
    Raises:
        ValueError: Если сотрудник не найден
    """
    employee_name_lower = employee_name.lower()
    if employee_name_lower not in EMPLOYEES:
        raise ValueError(f"Сотрудник '{employee_name}' не найден")
    
    return EMPLOYEES[employee_name_lower]["personal_days"]


def get_remaining_vacation_days(employee_name: str) -> int:
    """
    Получить количество оставшихся дней отпуска для сотрудника
    
    Args:
        employee_name: Имя сотрудника
        
    Returns:
        Количество оставшихся дней отпуска
        
    Raises:
        ValueError: Если сотрудник не найден
    """
    employee_name_lower = employee_name.lower()
    if employee_name_lower not in EMPLOYEES:
        raise ValueError(f"Сотрудник '{employee_name}' не найден")
    
    employee = EMPLOYEES[employee_name_lower]
    return employee["total_vacation_days"] - employee["used_vacation_days"]


def get_employee_info(employee_name: str) -> Optional[Dict[str, int]]:
    """
    Получить полную информацию о сотруднике
    
    Args:
        employee_name: Имя сотрудника
        
    Returns:
        Словарь с информацией о сотруднике или None если не найден
    """
    employee_name_lower = employee_name.lower()
    return EMPLOYEES.get(employee_name_lower)
