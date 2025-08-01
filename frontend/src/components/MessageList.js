import React from "react";
import Message from "./Message";
import "./MessageList.css";

function MessageList({ messages }) {
  return (
    <div className="message-list">
      {messages.slice().reverse().map((msg) => (
        <Message key={msg.id} {...msg} />
      ))}
      {/* Дополнительный отступ для предотвращения ухода сообщений под поле ввода */}
      <div className="message-spacer"></div>
    </div>
  );
}

export default MessageList; 