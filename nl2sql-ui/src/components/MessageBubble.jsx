import React from "react";
import MetricsBar    from "./MetricsBar";
import SQLViewer     from "./SQLViewer";
import DataTable     from "./DataTable";
import ChartRenderer from "./ChartRenderer";

// ══════════════════════════════════════════════════════════════
// TYPING INDICATOR
// ══════════════════════════════════════════════════════════════
const TypingIndicator = () => (
  <div className="typing-indicator">
    <span />
    <span />
    <span />
  </div>
);

// ══════════════════════════════════════════════════════════════
// USER BUBBLE
// ══════════════════════════════════════════════════════════════
const UserBubble = ({ message }) => (
  <div className="message-row user-row">
    <div className="message-content user-content">
      <div className="bubble user-bubble">
        <p>{message.content}</p>
      </div>
      <div className="msg-meta right">{message.timestamp}</div>
    </div>
    <div className="avatar user-avatar">U</div>
  </div>
);

// ══════════════════════════════════════════════════════════════
// ASSISTANT BUBBLE — LOADING STATE
// ══════════════════════════════════════════════════════════════
const LoadingBubble = () => (
  <div className="message-row assistant-row">
    <div className="avatar assistant-avatar">AI</div>
    <div className="message-content assistant-content">
      <div className="loading-bubble">
        <TypingIndicator />
        <span className="loading-text">Analyzing your question…</span>
      </div>
    </div>
  </div>
);

// ══════════════════════════════════════════════════════════════
// ASSISTANT BUBBLE — ERROR STATE
// ══════════════════════════════════════════════════════════════
const ErrorBubble = ({ message }) => (
  <div className="message-row assistant-row">
    <div className="avatar error-avatar">!</div>
    <div className="message-content assistant-content">
      <div className="error-message">
        <span className="error-icon">⚠</span>
        <p>{message.content}</p>
      </div>
      <div className="msg-meta left">{message.timestamp}</div>
    </div>
  </div>
);

// ══════════════════════════════════════════════════════════════
// ASSISTANT BUBBLE — SUCCESS STATE
// ══════════════════════════════════════════════════════════════
const SuccessBubble = ({ message }) => (
  <div className="message-row assistant-row">
    <div className="avatar assistant-avatar">AI</div>
    <div className="message-content assistant-content">

      {/* ── 0. Metrics strip ──────────────────────────────────── */}
      {message.kpiDetected !== undefined && (
        <MetricsBar
          kpiDetected={message.kpiDetected}
          confidenceScore={message.confidenceScore}
          executionTime={message.executionTime}
          rowsReturned={message.rowsReturned}
          cached={message.cached}
        />
      )}

      {/* ── 1. SQL Query ──────────────────────────────────────── */}
      {message.sqlQuery && (
        <SQLViewer sql={message.sqlQuery} />
      )}

      {/* ── 2. Chart ──────────────────────────────────────────── */}
      {message.data?.length > 0 && (
        <ChartRenderer
          data={message.data}
          kpiDetected={message.kpiDetected}
          question={message.question || ""}
        />
      )}

      {/* ── 3. Data Table ─────────────────────────────────────── */}
      {message.data?.length > 0 && (
        <DataTable data={message.data} />
      )}

      {/* ── Empty result ──────────────────────────────────────── */}
      {message.data?.length === 0 && (
        <p className="empty-result-text">
          No data rows returned for this query.
        </p>
      )}

      {/* ── 4. Rationale ──────────────────────────────────────── */}
      {message.content && (
        <p className="rationale-text">
          💬 {message.content}
        </p>
      )}

      <div className="msg-meta left">{message.timestamp}</div>
    </div>
  </div>
);

// ══════════════════════════════════════════════════════════════
// ASSISTANT BUBBLE — ROUTER
// ══════════════════════════════════════════════════════════════
const AssistantBubble = ({ message }) => {
  if (message.isLoading)          return <LoadingBubble />;
  if (message.status === "error") return <ErrorBubble message={message} />;
  return <SuccessBubble message={message} />;
};

// ══════════════════════════════════════════════════════════════
// MAIN EXPORT
// ══════════════════════════════════════════════════════════════
const MessageBubble = ({ message }) => {
  if (message.role === "user") return <UserBubble message={message} />;
  return <AssistantBubble message={message} />;
};

export default MessageBubble;