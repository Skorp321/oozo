import React, { useState, useRef, useEffect } from "react";
import "./MessageInput.css";

function MessageInput({ onSend, atBottom, disabled }) {
  const [text, setText] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!atBottom && inputRef.current) {
      inputRef.current.focus();
    }
  }, [atBottom]);

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text);
      setText("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`message-input-wrapper ${atBottom ? "bottom" : "center"} ${disabled ? "disabled" : ""}`}>
      <div className="message-input-content">
        <textarea
          ref={inputRef}
          className="message-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Система недоступна..." : "Введите сообщение..."}
          rows={1}
          disabled={disabled}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          aria-label="Отправить"
        >
          ➤
        </button>
      </div>
    </div>
  );
}

export default MessageInput; 