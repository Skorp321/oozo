#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример использования класса DocumentChunker для разбивки договора на чанки в формате JSON
"""

import json
from document_chunker import DocumentChunker


def demonstrate_chunking():
    """Демонстрация работы с чанкером документов в JSON формате"""
    
    print("=== ДЕМОНСТРАЦИЯ РАЗБИВКИ ДОКУМЕНТА НА JSON ЧАНКИ ===\n")
    
    # Создаем экземпляр чанкера
    chunker = DocumentChunker()
    
    # Путь к документу
    document_path = "../documents/Untitled.txt"
    
    print(f"Обрабатываем документ: {document_path}")
    
    # Разбиваем на чанки
    chunks = chunker.chunk_document(document_path)
    
    if not chunks:
        print("❌ Не удалось создать чанки")
        return
    
    print(f"✅ Создано {len(chunks)} чанков\n")
    
    # Показываем статистику по типам разделов
    section_stats = {}
    for chunk in chunks:
        section_type = chunk['meta']['section_type']
        level = chunk['meta']['level']
        key = f"{section_type}_level_{level}"
        section_stats[key] = section_stats.get(key, 0) + 1
    
    print("📊 Статистика по типам разделов:")
    for key, count in sorted(section_stats.items()):
        print(f"   {key}: {count} чанков")
    print()
    
    # Показываем несколько примеров разных типов чанков
    print("📋 Примеры чанков:\n")
    
    # Главный раздел
    main_sections = [c for c in chunks if c['meta']['level'] == 0 and c['meta']['section_type'] == 'section']
    if main_sections:
        chunk = main_sections[0]
        print("🔹 Главный раздел:")
        print(f"   Номер: {chunk['meta']['section_number']}")
        print(f"   Заголовок: {chunk['meta']['section_title']}")
        print(f"   Размер текста: {chunk['meta']['text_length']} символов")
        print(f"   Текст: {chunk['text'][:100]}...")
        print()
    
    # Подраздел с иерархией
    sub_sections = [c for c in chunks if c['meta']['level'] >= 2]
    if sub_sections:
        chunk = sub_sections[0]
        print("🔸 Подраздел с иерархией:")
        print(f"   Полный путь: {chunk['meta']['chunk_title']}")
        print(f"   Уровень: {chunk['meta']['level']}")
        print(f"   Родительские разделы:")
        for parent in chunk['meta']['parent_sections']:
            print(f"     - {parent['number']} {parent['title'][:50]}...")
        print(f"   Размер текста: {chunk['meta']['text_length']} символов")
        print()
    
    # Приложение
    appendix_chunks = [c for c in chunks if c['meta']['section_type'] == 'appendix']
    if appendix_chunks:
        chunk = appendix_chunks[0]
        print("📎 Приложение:")
        print(f"   Номер: {chunk['meta']['section_number']}")
        print(f"   Заголовок: {chunk['meta']['section_title']}")
        print(f"   Размер текста: {chunk['meta']['text_length']} символов")
        print()
    
    return chunks


def search_in_chunks():
    """Демонстрация поиска в чанках"""
    
    print("=== ПОИСК В ЧАНКАХ ===\n")
    
    # Загружаем все чанки из файла
    try:
        with open("../documents/chunks_json/all_chunks.json", 'r', encoding='utf-8') as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print("❌ Файл all_chunks.json не найден. Сначала запустите разбивку документа.")
        return
    
    print(f"Загружено {len(chunks)} чанков\n")
    
    # Примеры поиска
    search_terms = ["лизинговый платеж", "страхование", "ответственность"]
    
    for term in search_terms:
        print(f"🔍 Поиск: '{term}'")
        found_chunks = []
        
        for chunk in chunks:
            if term.lower() in chunk['text'].lower():
                found_chunks.append(chunk)
        
        print(f"   Найдено: {len(found_chunks)} чанков")
        
        # Показываем первые 2 результата
        for i, chunk in enumerate(found_chunks[:2]):
            print(f"   {i+1}. {chunk['meta']['section_number']} {chunk['meta']['section_title'][:50]}...")
            print(f"      Уровень: {chunk['meta']['level']}, Размер: {chunk['meta']['text_length']} символов")
        
        if len(found_chunks) > 2:
            print(f"      ... и еще {len(found_chunks) - 2} результатов")
        print()


def analyze_chunk_structure():
    """Анализ структуры чанков"""
    
    print("=== АНАЛИЗ СТРУКТУРЫ ЧАНКОВ ===\n")
    
    try:
        with open("../documents/chunks_json/all_chunks.json", 'r', encoding='utf-8') as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print("❌ Файл all_chunks.json не найден. Сначала запустите разбивку документа.")
        return
    
    # Анализ по уровням
    levels = {}
    for chunk in chunks:
        level = chunk['meta']['level']
        levels[level] = levels.get(level, 0) + 1
    
    print("📊 Распределение по уровням вложенности:")
    for level in sorted(levels.keys()):
        print(f"   Уровень {level}: {levels[level]} чанков")
    print()
    
    # Самые большие и маленькие чанки
    chunks_by_size = sorted(chunks, key=lambda x: x['meta']['text_length'])
    
    print("📏 Размеры чанков:")
    print(f"   Самый маленький: {chunks_by_size[0]['meta']['text_length']} символов")
    print(f"   Самый большой: {chunks_by_size[-1]['meta']['text_length']} символов")
    print(f"   Средний размер: {sum(c['meta']['text_length'] for c in chunks) // len(chunks)} символов")
    print()
    
    # Самые большие чанки
    print("📋 Топ-5 самых больших чанков:")
    for i, chunk in enumerate(chunks_by_size[-5:], 1):
        print(f"   {i}. {chunk['meta']['section_number']} - {chunk['meta']['text_length']} символов")
        print(f"      {chunk['meta']['section_title'][:70]}...")
    print()


def export_chunk_metadata():
    """Экспорт метаданных чанков в CSV"""
    
    print("=== ЭКСПОРТ МЕТАДАННЫХ ===\n")
    
    try:
        with open("../documents/chunks_json/all_chunks.json", 'r', encoding='utf-8') as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print("❌ Файл all_chunks.json не найден. Сначала запустите разбивку документа.")
        return
    
    # Создаем CSV с метаданными
    csv_content = "chunk_index,section_number,section_title,section_type,level,text_length,parent_count\n"
    
    for chunk in chunks:
        meta = chunk['meta']
        csv_content += f"{meta['chunk_index']},{meta['section_number']},\"{meta['section_title'][:50]}...\",{meta['section_type']},{meta['level']},{meta['text_length']},{len(meta['parent_sections'])}\n"
    
    # Сохраняем CSV
    with open("../documents/chunks_json/chunks_metadata.csv", 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    print("✅ Метаданные экспортированы в chunks_metadata.csv")
    print(f"   Обработано {len(chunks)} чанков")


if __name__ == "__main__":
    # Демонстрация всех функций
    chunks = demonstrate_chunking()
    
    if chunks:
        print("\n" + "="*60 + "\n")
        search_in_chunks()
        
        print("\n" + "="*60 + "\n")
        analyze_chunk_structure()
        
        print("\n" + "="*60 + "\n")
        export_chunk_metadata()
        
        print("\n🎉 Демонстрация завершена!") 