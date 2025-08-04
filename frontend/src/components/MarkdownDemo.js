import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-sql';

const MarkdownDemo = () => {
  const markdownText = `# Демонстрация Markdown

## Возможности форматирования

### Текстовое форматирование
Это **жирный текст** и *курсив*. Также можно использовать ~~зачеркнутый текст~~.

### Списки

#### Маркированный список:
- Первый элемент
- Второй элемент
  - Вложенный элемент
  - Еще один вложенный
- Третий элемент

#### Нумерованный список:
1. Первый пункт
2. Второй пункт
3. Третий пункт

### Код

#### Встроенный код:
Используйте \`console.log('Hello World')\` для вывода в консоль.

#### Блоки кода:

\`\`\`javascript
function greet(name) {
  console.log(\`Hello, \${name}!\`);
  return \`Hello, \${name}!\`;
}

greet('World');
\`\`\`

\`\`\`python
def greet(name):
    print(f"Hello, {name}!")
    return f"Hello, {name}!"

greet("World")
\`\`\`

\`\`\`sql
SELECT name, age, city 
FROM users 
WHERE age > 18 
ORDER BY name;
\`\`\`

### Ссылки
[Ссылка на Google](https://google.com)

### Цитаты
> Это цитата
> 
> Вторая строка цитаты
> 
> > Вложенная цитата

### Таблицы
| Имя | Возраст | Город |
|-----|---------|-------|
| Иван | 25 | Москва |
| Мария | 30 | СПб |
| Петр | 22 | Казань |

### Эмодзи
😀 🚀 💻 📚 🎯 ⭐

### Задачи
- [x] Добавить поддержку Markdown
- [x] Добавить подсветку синтаксиса
- [ ] Добавить дополнительные темы
- [ ] Оптимизировать производительность`;

  React.useEffect(() => {
    Prism.highlightAll();
  }, []);

  return (
    <div style={{ 
      padding: '20px', 
      maxWidth: '800px', 
      margin: '0 auto',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h1 style={{ color: '#2d3748', textAlign: 'center', marginBottom: '30px' }}>
        Демонстрация Markdown рендеринга
      </h1>
      
      <div style={{ 
        background: '#f8f9fa', 
        padding: '30px', 
        borderRadius: '12px',
        border: '1px solid #e9ecef',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
      }}>
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({node, ...props}) => <h1 className="markdown-h1" {...props} />,
            h2: ({node, ...props}) => <h2 className="markdown-h2" {...props} />,
            h3: ({node, ...props}) => <h3 className="markdown-h3" {...props} />,
            h4: ({node, ...props}) => <h4 className="markdown-h4" {...props} />,
            h5: ({node, ...props}) => <h5 className="markdown-h5" {...props} />,
            h6: ({node, ...props}) => <h6 className="markdown-h6" {...props} />,
            code: ({node, inline, className, children, ...props}) => {
              const match = /language-(\w+)/.exec(className || '');
              const language = match ? match[1] : '';
              
              if (!inline) {
                return (
                  <pre className="markdown-code-block">
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                );
              } else {
                return (
                  <code className="markdown-inline-code" {...props}>
                    {children}
                  </code>
                );
              }
            },
            pre: ({node, ...props}) => <pre className="markdown-pre" {...props} />,
            ul: ({node, ...props}) => <ul className="markdown-ul" {...props} />,
            ol: ({node, ...props}) => <ol className="markdown-ol" {...props} />,
            li: ({node, ...props}) => <li className="markdown-li" {...props} />,
            a: ({node, ...props}) => <a className="markdown-link" target="_blank" rel="noopener noreferrer" {...props} />,
            table: ({node, ...props}) => <table className="markdown-table" {...props} />,
            thead: ({node, ...props}) => <thead className="markdown-thead" {...props} />,
            tbody: ({node, ...props}) => <tbody className="markdown-tbody" {...props} />,
            tr: ({node, ...props}) => <tr className="markdown-tr" {...props} />,
            th: ({node, ...props}) => <th className="markdown-th" {...props} />,
            td: ({node, ...props}) => <td className="markdown-td" {...props} />,
            blockquote: ({node, ...props}) => <blockquote className="markdown-blockquote" {...props} />,
            p: ({node, ...props}) => <p className="markdown-p" {...props} />,
            strong: ({node, ...props}) => <strong className="markdown-strong" {...props} />,
            em: ({node, ...props}) => <em className="markdown-em" {...props} />,
          }}
        >
          {markdownText}
        </ReactMarkdown>
      </div>
      
      <div style={{ 
        marginTop: '20px', 
        textAlign: 'center', 
        color: '#666',
        fontSize: '14px'
      }}>
        <p>✅ Markdown рендеринг работает корректно!</p>
        <p>Теперь все сообщения в чате будут отображаться с поддержкой Markdown форматирования.</p>
      </div>
    </div>
  );
};

export default MarkdownDemo; 