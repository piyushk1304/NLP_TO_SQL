import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, Mic } from "lucide-react";

const InputBar = ({ onSend, isLoading, disabled }) => {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [value]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || isLoading || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="input-area">
      <div className={`input-bar ${disabled ? "input-bar-disabled" : ""}`}>
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder={
            disabled
              ? "Upload a dataset to start asking questions…"
              : "Ask a question about your data… (Enter to send, Shift+Enter for newline)"
          }
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading || disabled}
          rows={1}
        />

        <button
          className={`send-btn ${(!value.trim() || isLoading || disabled) ? "send-btn-disabled" : "send-btn-active"}`}
          onClick={handleSubmit}
          disabled={!value.trim() || isLoading || disabled}
          title="Send (Enter)"
        >
          {isLoading ? (
            <Loader2 size={18} className="spin" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>

      <div className="input-hint">
        NL2SQL · Powered by local LLM · Your data stays private
      </div>
    </div>
  );
};

export default InputBar;