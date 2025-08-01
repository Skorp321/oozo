import re
import json
import os
from typing import List, Dict, Tuple


class DocumentChunker:
    """Класс для разбивки документа на чанки по пунктам и подпунктам"""
    
    def __init__(self):
        # Паттерн для поиска пунктов (1., 2.1., 2.1.1., и т.д.)
        self.section_pattern = re.compile(r'^(\d+(?:\.\d+)*\.)\s+(.+?)$', re.MULTILINE)
        # Паттерн для поиска приложений
        self.appendix_pattern = re.compile(r'^(Приложение\s*№\s*\d+)', re.MULTILINE | re.IGNORECASE)
        
    def read_document(self, file_path: str) -> str:
        """Читает документ из файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return ""
    
    def find_sections(self, text: str) -> List[Dict]:
        """Находит все секции документа с их позициями"""
        sections = []
        
        # Ищем основные пункты
        for match in self.section_pattern.finditer(text):
            sections.append({
                'number': match.group(1),
                'title': match.group(2).strip(),
                'start_pos': match.start(),
                'type': 'section'
            })
        
        # Ищем приложения
        for match in self.appendix_pattern.finditer(text):
            sections.append({
                'number': match.group(1),
                'title': match.group(1),
                'start_pos': match.start(),
                'type': 'appendix'
            })
        
        # Сортируем по позиции в тексте
        sections.sort(key=lambda x: x['start_pos'])
        return sections
    
    def extract_section_content(self, text: str, current_section: Dict, next_section: Dict = None) -> str:
        """Извлекает содержимое секции между текущей и следующей секцией"""
        start_pos = current_section['start_pos']
        end_pos = next_section['start_pos'] if next_section else len(text)
        
        # Извлекаем текст секции
        section_text = text[start_pos:end_pos].strip()
        
        # Убираем лишние пустые строки
        lines = section_text.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_lines.append(line.rstrip())
        
        # Удаляем пустые строки в конце
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
            
        return '\n'.join(cleaned_lines)
    
    def create_chunk_title(self, section: Dict, parent_sections: List[Dict] = None) -> str:
        """Создает заголовок чанка с иерархией разделов"""
        title_parts = []
        
        # Добавляем родительские разделы для контекста
        if parent_sections:
            for parent in parent_sections:
                title_parts.append(f"{parent['number']} {parent['title']}")
        
        # Добавляем текущий раздел
        title_parts.append(f"{section['number']} {section['title']}")
        
        return " → ".join(title_parts)
    
    def get_parent_sections(self, current_number: str, all_sections: List[Dict]) -> List[Dict]:
        """Получает список родительских разделов для создания иерархии"""
        if current_number.count('.') <= 1:  # Главный раздел
            return []
        
        parents = []
        number_parts = current_number.rstrip('.').split('.')
        
        # Ищем родительские разделы
        for i in range(1, len(number_parts)):
            parent_number = '.'.join(number_parts[:i]) + '.'
            for section in all_sections:
                if section['number'] == parent_number:
                    parents.append(section)
                    break
        
        return parents
    
    def create_hierarchy_path(self, parent_sections: List[Dict], current_section: Dict) -> List[Dict]:
        """Создает полный путь иерархии разделов"""
        hierarchy = []
        
        # Добавляем родительские разделы
        for parent in parent_sections:
            hierarchy.append({
                'level': parent['number'].count('.') - 1,
                'number': parent['number'],
                'title': parent['title'],
                'type': parent['type']
            })
        
        # Добавляем текущий раздел
        hierarchy.append({
            'level': current_section['number'].count('.') - 1,
            'number': current_section['number'],
            'title': current_section['title'],
            'type': current_section['type']
        })
        
        return hierarchy
    
    def chunk_document(self, file_path: str) -> List[Dict]:
        """Основная функция для разбивки документа на чанки в формате JSON"""
        # Читаем документ
        text = self.read_document(file_path)
        if not text:
            return []
        
        # Находим все секции
        sections = self.find_sections(text)
        
        if not sections:
            print("Не найдено ни одной секции в документе")
            return []
        
        chunks = []
        
        # Создаем чанки для каждой секции
        for i, section in enumerate(sections):
            next_section = sections[i + 1] if i + 1 < len(sections) else None
            
            # Извлекаем содержимое секции
            content = self.extract_section_content(text, section, next_section)
            
            if not content.strip():
                continue
            
            # Получаем родительские разделы для иерархии
            parent_sections = self.get_parent_sections(section['number'], sections)
            
            # Создаем заголовок с иерархией
            chunk_title = self.create_chunk_title(section, parent_sections)
            
            # Создаем полный путь иерархии
            hierarchy_path = self.create_hierarchy_path(parent_sections, section)
            
            # Формируем чанк в формате JSON
            chunk = {
                'meta': {
                    'section_number': section['number'],
                    'section_title': section['title'],
                    'section_type': section['type'],
                    'chunk_title': chunk_title,
                    'hierarchy': hierarchy_path,
                    'level': section['number'].count('.') - 1,
                    'parent_sections': [
                        {
                            'number': p['number'],
                            'title': p['title'],
                            'type': p['type']
                        } for p in parent_sections
                    ],
                    'text_length': len(content),
                    'chunk_index': i + 1
                },
                'text': content
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def save_chunks(self, chunks: List[Dict], output_dir: str = "chunks"):
        """Сохраняет чанки в JSON файлы"""
        # Создаем директорию для чанков
        os.makedirs(output_dir, exist_ok=True)
        
        # Сохраняем каждый чанк в отдельный JSON файл
        for chunk in chunks:
            # Создаем безопасное имя файла
            safe_number = chunk['meta']['section_number'].replace('.', '_').rstrip('_')
            filename = f"chunk_{chunk['meta']['chunk_index']:03d}_{safe_number}.json"
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
                print(f"Сохранен чанк: {filename}")
            except Exception as e:
                print(f"Ошибка при сохранении чанка {filename}: {e}")
        
        # Также сохраняем все чанки в один файл
        all_chunks_file = os.path.join(output_dir, "all_chunks.json")
        try:
            with open(all_chunks_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            print(f"Сохранены все чанки в файл: all_chunks.json")
        except Exception as e:
            print(f"Ошибка при сохранении файла all_chunks.json: {e}")
    
    def print_chunks_summary(self, chunks: List[Dict]):
        """Выводит сводку по созданным чанкам"""
        print(f"\nСоздано чанков: {len(chunks)}")
        print("=" * 50)
        
        for chunk in chunks:
            meta = chunk['meta']
            print(f"{meta['chunk_index']:3d}. {meta['section_number']} {meta['section_title']}")
            print(f"     Размер: {meta['text_length']} символов")
            print(f"     Тип: {meta['section_type']}")
            print(f"     Уровень: {meta['level']}")
            if meta['parent_sections']:
                parents = " → ".join([f"{p['number']} {p['title'][:30]}..." 
                                    if len(p['title']) > 30 else f"{p['number']} {p['title']}" 
                                    for p in meta['parent_sections']])
                print(f"     Родители: {parents}")
            print()
    
    def search_chunks(self, chunks: List[Dict], search_term: str) -> List[Dict]:
        """Поиск по чанкам"""
        found_chunks = []
        
        for chunk in chunks:
            if search_term.lower() in chunk['text'].lower():
                found_chunks.append(chunk)
        
        return found_chunks


def main():
    """Основная функция для демонстрации работы"""
    
    # Путь к документу
    document_path = "../documents/Untitled.txt"
    
    # Создаем экземпляр чанкера
    chunker = DocumentChunker()
    
    # Разбиваем документ на чанки
    print("Начинаем разбивку документа на чанки в формате JSON...")
    chunks = chunker.chunk_document(document_path)
    
    if not chunks:
        print("Не удалось создать чанки")
        return
    
    # Выводим сводку
    chunker.print_chunks_summary(chunks)
    
    # Сохраняем чанки в JSON файлы
    output_directory = "../documents/chunks_json"
    print(f"Сохраняем чанки в директорию: {output_directory}")
    chunker.save_chunks(chunks, output_directory)
    
    # Показываем пример первого чанка
    print("\nПример первого чанка в JSON формате:")
    print("=" * 50)
    print(json.dumps(chunks[0], ensure_ascii=False, indent=2)[:800] + "..." if len(str(chunks[0])) > 800 else json.dumps(chunks[0], ensure_ascii=False, indent=2))
    
    return chunks


if __name__ == "__main__":
    main() 