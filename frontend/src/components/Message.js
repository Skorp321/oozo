import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Prism from "prismjs";
import "prismjs/themes/prism.css";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-python";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-json";
import "prismjs/components/prism-css";
import "prismjs/components/prism-sql";
import "./Message.css";

function Message({ sender, text, timestamp, sources, isError, isThinking, isStreaming, showTyping }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = sender === "user";
  const hasSources = sources && sources.length > 0;

  // Подсветка синтаксиса после рендеринга
  useEffect(() => {
    if (text) {
      Prism.highlightAll();
    }
  }, [text]);

  useEffect(() => {
    if (showSources && sources) {
      Prism.highlightAll();
    }
  }, [showSources, sources]);

  return (
    <div className={`message-row ${isUser ? "user" : "bot"} ${isError ? "error" : ""} ${isThinking ? "thinking" : ""} ${isStreaming ? "streaming" : ""}`}>
      <div className="avatar">
        {isUser ? "🧑" : isThinking ? "⏳" : isError ? "❌" : isStreaming ? "✍️" : "🤖"}
      </div>
      <div className="message-bubble">
        <div className={`message-text ${isError ? "error-text" : ""} ${isStreaming ? "streaming-text" : ""}`}>
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              // Стилизация заголовков
              h1: ({node, ...props}) => <h1 className="markdown-h1" {...props} />,
              h2: ({node, ...props}) => <h2 className="markdown-h2" {...props} />,
              h3: ({node, ...props}) => <h3 className="markdown-h3" {...props} />,
              h4: ({node, ...props}) => <h4 className="markdown-h4" {...props} />,
              h5: ({node, ...props}) => <h5 className="markdown-h5" {...props} />,
              h6: ({node, ...props}) => <h6 className="markdown-h6" {...props} />,
              // Стилизация кода с подсветкой синтаксиса
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
              // Стилизация блоков кода
              pre: ({node, ...props}) => <pre className="markdown-pre" {...props} />,
              // Стилизация списков
              ul: ({node, ...props}) => <ul className="markdown-ul" {...props} />,
              ol: ({node, ...props}) => <ol className="markdown-ol" {...props} />,
              li: ({node, ...props}) => <li className="markdown-li" {...props} />,
              // Стилизация ссылок
              a: ({node, ...props}) => <a className="markdown-link" target="_blank" rel="noopener noreferrer" {...props} />,
              // Стилизация таблиц
              table: ({node, ...props}) => <table className="markdown-table" {...props} />,
              thead: ({node, ...props}) => <thead className="markdown-thead" {...props} />,
              tbody: ({node, ...props}) => <tbody className="markdown-tbody" {...props} />,
              tr: ({node, ...props}) => <tr className="markdown-tr" {...props} />,
              th: ({node, ...props}) => <th className="markdown-th" {...props} />,
              td: ({node, ...props}) => <td className="markdown-td" {...props} />,
              // Стилизация цитат
              blockquote: ({node, ...props}) => <blockquote className="markdown-blockquote" {...props} />,
              // Стилизация параграфов
              p: ({node, ...props}) => <p className="markdown-p" {...props} />,
              // Стилизация выделения
              strong: ({node, ...props}) => <strong className="markdown-strong" {...props} />,
              em: ({node, ...props}) => <em className="markdown-em" {...props} />,
            }}
          >
            {text}
          </ReactMarkdown>
          {/* Индикатор печатания для стриминга */}
          {isStreaming && (
            <span className="streaming-cursor">|</span>
          )}
        </div>
        
        {/* Sources Section */}
        {hasSources && (
          <div className="sources-section">
            <button 
              className="sources-toggle"
              onClick={() => setShowSources(!showSources)}
            >
              📚 Источники ({sources.length})
              <span className={`arrow ${showSources ? 'up' : 'down'}`}>▼</span>
            </button>
            
            {showSources && (
              <div className="sources-list">
                {sources.map((source, index) => (
                  <div key={index} className="source-item">
                    <div className="source-header">
                      <span className="source-number">#{index + 1}</span>
                      {source.metadata && source.metadata.source && (
                        <span className="source-file">
                          📄 {source.metadata.source.split('/').pop()}
                        </span>
                      )}
                    </div>
                    <div className="source-content">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          code: ({node, inline, className, children, ...props}) => {
                            const match = /language-(\w+)/.exec(className || '');
                            const language = match ? match[1] : '';
                            
                            if (!inline) {
                              return (
                                <pre className="markdown-code-block source-code">
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
                          pre: ({node, ...props}) => <pre className="markdown-pre source-code" {...props} />,
                        }}
                      >
                        {source.content}
                      </ReactMarkdown>
                    </div>
                    {source.metadata && Object.keys(source.metadata).length > 1 && (
                      <div className="source-metadata">
                        {Object.entries(source.metadata)
                          .filter(([key]) => key !== 'source')
                          .map(([key, value]) => (
                            <span key={key} className="metadata-item">
                              <strong>{key}:</strong> {String(value)}
                            </span>
                          ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        <div className="message-meta">
          <span className="timestamp">{timestamp}</span>
          {hasSources && (
            <span className="sources-indicator">
              📚 {sources.length} источник{sources.length > 1 ? 'ов' : ''}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default Message; 