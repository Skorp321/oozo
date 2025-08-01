import React, { useState } from "react";
import ChatInterface from "./components/ChatInterface";
import { sendMessage } from "./services/api";
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

    // Add a "thinking" message
    const thinkingMsg = {
      id: Date.now() + 1,
      sender: "bot",
      text: "Обрабатываю ваш запрос...",
      timestamp: new Date().toLocaleTimeString(),
      isThinking: true,
    };

    setMessages((msgs) => [thinkingMsg, ...msgs]);

    try {
      // Send message to RAG API
      const response = await sendMessage(text, true);
      
      // Remove thinking message and add real response
      setMessages((msgs) => {
        const filteredMsgs = msgs.filter(msg => !msg.isThinking);
        const botMsg = {
          id: Date.now() + 2,
          sender: "bot",
          text: response.answer,
          timestamp: new Date().toLocaleTimeString(),
          sources: response.sources || [],
          originalQuestion: response.question,
        };
        return [botMsg, ...filteredMsgs];
      });

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Remove thinking message and add error message
      setMessages((msgs) => {
        const filteredMsgs = msgs.filter(msg => !msg.isThinking);
        const errorMsg = {
          id: Date.now() + 2,
          sender: "bot",
          text: `Извините, произошла ошибка при обработке вашего запроса: ${error.message}`,
          timestamp: new Date().toLocaleTimeString(),
          isError: true,
        };
        return [errorMsg, ...filteredMsgs];
      });
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