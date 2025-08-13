#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings


def format_timestamp(timestamp_str: str) -> str:
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str


def view_logs(log_file: str = None, limit: int = 50, show_errors_only: bool = False):
    if log_file is None:
        log_file = settings.logs_path
    
    log_path = Path(log_file)
    
    if not log_path.exists():
        print(f"Файл логов не найден: {log_path}")
        return
    
    print(f"Просмотр логов из файла: {log_path}")
    print("=" * 80)
    
    logs = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    log_entry = json.loads(line.strip())
                    logs.append(log_entry)
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга строки {line_num}: {e}")
                    continue
    except Exception as e:
        print(f"Ошибка чтения файла логов: {e}")
        return
    
    if show_errors_only:
        logs = [log for log in logs if log.get('status') == 'error']
    
    logs = logs[-limit:] if limit else logs
    
    if not logs:
        print("Логи не найдены")
        return
    
    print(f"Найдено записей: {len(logs)}")
    print()
    
    for i, log in enumerate(logs, 1):
        print(f"Запись #{i}")
        print(f"Время: {format_timestamp(log.get('timestamp', ''))}")
        print(f"Тип: {log.get('type', 'regular')}")
        print(f"Статус: {log.get('status', 'unknown')}")
        
        request = log.get('request', {})
        question = request.get('question', '')
        print(f"Вопрос: {question[:100]}{'...' if len(question) > 100 else ''}")
        
        response = log.get('response', {})
        answer = response.get('answer', '')
        sources_count = response.get('sources_count', 0)
        print(f"Ответ: {answer[:100]}{'...' if len(answer) > 100 else ''}")
        print(f"Источников: {sources_count}")
        
        processing_time = log.get('processing_time_seconds')
        if processing_time:
            print(f"Время обработки: {processing_time:.2f} сек")
        
        error = log.get('error')
        if error:
            print(f"Ошибка: {error}")
        
        print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description='Просмотр логов вопросов и ответов')
    parser.add_argument('--file', '-f', help='Путь к файлу логов')
    parser.add_argument('--limit', '-l', type=int, default=50, help='Максимальное количество записей')
    parser.add_argument('--errors-only', '-e', action='store_true', help='Показать только ошибки')
    
    args = parser.parse_args()
    
    view_logs(
        log_file=args.file,
        limit=args.limit,
        show_errors_only=args.errors_only
    )


if __name__ == '__main__':
    main()
