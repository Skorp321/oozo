import React, { useState, useRef } from "react";
import { flushSync } from "react-dom";
import ChatInterface from "./components/ChatInterface";
import { sendMessage, streamMessage, getSimilarDocuments } from "./services/api";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (text) => {
    if (!text.trim() || isLoading) return;

    const userMsg = {
      id: Date.now(),
      sender: "user",
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((msgs) => [userMsg, ...msgs]);
    setIsLoading(true);

    // Создаем пустое бот-сообщение, которое будем постепенно обновлять
    const botMsgId = Date.now() + 1;
    const baseBotMsg = {
      id: botMsgId,
      sender: "bot",
      text: "",
      timestamp: new Date().toLocaleTimeString(),
      sources: [],
      originalQuestion: text.trim(),
      isStreaming: true, // Флаг для индикации активного стриминга
    };
    setMessages((msgs) => [baseBotMsg, ...msgs]);

    try {
      let accumulated = "";
      let tokenCount = 0;
      
      // Сначала пробуем поток
      await streamMessage(text, (chunk) => {
        accumulated += chunk;
        tokenCount++;
        
        // Отладочная информация для проверки работы
        if (tokenCount <= 10 || tokenCount % 20 === 0) {
          console.log(`[STREAM] Token #${tokenCount}: "${chunk}" -> Total: "${accumulated.slice(-50)}"`);
        }
        
        // Принудительное синхронное обновление DOM для каждого токена
        flushSync(() => {
          setMessages((prevMessages) => {
            return prevMessages.map((m) => 
              m.id === botMsgId 
                ? { 
                    ...m, 
                    text: accumulated,
                    isStreaming: true,
                    // Добавляем индикатор печатания для визуального эффекта
                    showTyping: tokenCount % 5 === 0
                  } 
                : m
            );
          });
        });
        
        // Небольшая пауза для предотвращения блокировки UI
        if (tokenCount % 10 === 0) {
          setTimeout(() => {}, 1);
        }
      });

      // Убираем флаг стриминга после завершения
      setMessages((msgs) =>
        msgs.map((m) => (m.id === botMsgId ? { 
          ...m, 
          isStreaming: false,
          showTyping: false 
        } : m))
      );

      // После завершения стрима можно подтянуть источники отдельно
      try {
        const similar = await getSimilarDocuments(text, 4);
        const sources = similar?.documents || [];
        setMessages((msgs) =>
          msgs.map((m) => (m.id === botMsgId ? { ...m, sources } : m))
        );
      } catch (e) {
        // игнорируем, если не удалось получить источники
        console.log('Could not fetch sources:', e.message);
      }
    } catch (streamErr) {
      console.warn('Streaming failed, falling back to non-streaming:', streamErr);
      try {
        const response = await sendMessage(text, true);
        setMessages((msgs) =>
          msgs.map((m) => (m.id === botMsgId ? {
            ...m,
            text: response.answer,
            sources: response.sources || [],
            originalQuestion: response.question,
            isStreaming: false,
            showTyping: false
          } : m))
        );
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages((msgs) =>
          msgs.map((m) => (m.id === botMsgId ? {
            ...m,
            text: `Извините, произошла ошибка при обработке вашего запроса: ${error.message}`,
            isError: true,
            isStreaming: false,
            showTyping: false
          } : m))
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <div className="main-content">
        <ChatInterface
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

export default App; 