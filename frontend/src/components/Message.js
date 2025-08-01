import React, { useState } from "react";
import "./Message.css";

function Message({ sender, text, timestamp, sources, isError, isThinking }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = sender === "user";
  const hasSources = sources && sources.length > 0;

  return (
    <div className={`message-row ${isUser ? "user" : "bot"} ${isError ? "error" : ""} ${isThinking ? "thinking" : ""}`}>
      <div className="avatar">
        {isUser ? "🧑" : isThinking ? "⏳" : isError ? "❌" : "🤖"}
      </div>
      <div className="message-bubble">
        <div className={`message-text ${isError ? "error-text" : ""}`}>
          {text}
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
                      {source.content}
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