import React, { useState, useRef, useEffect } from "react";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import "./ChatInterface.css";

function ChatInterface({ messages, onSendMessage, isLoading, systemStatus }) {
  const [inputAtBottom, setInputAtBottom] = useState(false);
  const messagesRef = useRef(null);

  const handleSend = (text) => {
    if (!inputAtBottom) setInputAtBottom(true);
    onSendMessage(text);
  };

  // Автоматическая прокрутка к новым сообщениям с учетом поля ввода
  useEffect(() => {
    if (messagesRef.current && messages.length > 0) {
      const scrollToBottom = () => {
        const container = messagesRef.current;
        // Прокручиваем к самому низу контейнера
        // Благодаря padding-bottom сообщения не будут уходить под поле ввода
        container.scrollTop = container.scrollHeight;
      };
      
      // Небольшая задержка для корректной прокрутки после рендера
      setTimeout(scrollToBottom, 100);
    }
  }, [messages]);

  // Перемещение поля ввода вниз при появлении первого сообщения
  useEffect(() => {
    if (messages.length > 0 && !inputAtBottom) {
      setInputAtBottom(true);
    }
  }, [messages.length, inputAtBottom]);

  return (
    <div className="chat-container">
      <div className="chat-messages" ref={messagesRef}>
        <MessageList messages={messages} />
        
        {/* Loading Indicator */}
        {isLoading && (
          <div className="loading-indicator">
            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="loading-text">Бот обрабатывает запрос...</span>
          </div>
        )}
      </div>
      
      <MessageInput
        onSend={handleSend}
        atBottom={inputAtBottom}
        disabled={isLoading}
      />
    </div>
  );
}

export default ChatInterface; 