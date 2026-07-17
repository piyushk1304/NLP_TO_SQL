import React, { useEffect, useRef } from "react";
import { Bot, Upload, Sparkles } from "lucide-react";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";
import { SAMPLE_QUESTIONS } from "../utils/helpers";

const EmptyState = ({ hasData, onUpload, onSample }) => (
  <div className="empty-state">
    <div className="empty-icon">
      <Bot size={40} />
    </div>
    <h2 className="empty-title">AI Data Analyst</h2>
    <p className="empty-sub">
      {hasData
        ? "Your dataset is ready. Ask anything about your data!"
        : "Upload a CSV or Excel file to get started."}
    </p>

    {!hasData && (
      <button className="empty-upload-btn" onClick={onUpload}>
        <Upload size={16} />
        <span>Upload Dataset</span>
      </button>
    )}

    {hasData && (
      <div className="suggestion-grid">
        {SAMPLE_QUESTIONS.slice(0, 4).map((q, i) => (
          <button key={i} className="suggestion-card" onClick={() => onSample(q)}>
            <Sparkles size={13} />
            <span>{q}</span>
          </button>
        ))}
      </div>
    )}
  </div>
);

const ChatWindow = ({
  messages,
  isLoading,
  hasData,
  onSend,
  onUpload,
  onSampleQuestion,
}) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat-window">
      {/* Messages */}
      <div className="messages-area">
        {messages.length === 0 ? (
          <EmptyState
            hasData={hasData}
            onUpload={onUpload}
            onSample={onSampleQuestion}
          />
        ) : (
          <div className="messages-list">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <InputBar
        onSend={onSend}
        isLoading={isLoading}
        disabled={!hasData}
      />
    </div>
  );
};

export default ChatWindow;