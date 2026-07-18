import React, { useState, useEffect } from "react";
import { Toaster } from "react-hot-toast";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import UploadModal from "./components/UploadModal";
import useChat from "./hooks/useChat";
import { SAMPLE_QUESTIONS } from "./utils/helpers";
import { healthCheck } from "./services/api";
import "./App.css";

const App = () => {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);

  const {
    messages,
    isLoading,
    schema,
    hasData,
    sendMessage,
    clearChat,
    loadSchema,
    onUploadSuccess,
  } = useChat();

  // Check backend health on mount
  useEffect(() => {
    healthCheck()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  // Load schema on mount if data exists
  useEffect(() => {
    loadSchema();
  }, [loadSchema]);

  const handleSampleQuestion = (q) => {
    if (hasData) sendMessage(q);
    else setUploadOpen(true);
  };

  return (
    <div className="app">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#1e293b",
            color: "#f1f5f9",
            border: "1px solid #334155",
            borderRadius: "10px",
            fontSize: "13px",
          },
          success: { iconTheme: { primary: "#10b981", secondary: "#fff" } },
          error: { iconTheme: { primary: "#ef4444", secondary: "#fff" } },
        }}
      />

      {/* Backend Status Banner */}
      {backendOnline === false && (
        <div className="status-banner">
          ⚠️ Backend server is offline. Please start your FastAPI server at{" "}
          <code>http://localhost:8000</code>
        </div>
      )}

      <div className="app-layout">
        {/* Sidebar */}
        <Sidebar
          schema={schema}
          hasData={hasData}
          onUploadClick={() => setUploadOpen(true)}
          onClearChat={clearChat}
          onSampleQuestion={handleSampleQuestion}
          sampleQuestions={SAMPLE_QUESTIONS}
        />

        {/* Main Chat */}
        <main className="main-area">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            hasData={hasData}
            onSend={sendMessage}
            onUpload={() => setUploadOpen(true)}
            onSampleQuestion={handleSampleQuestion}
          />
        </main>
      </div>

      {/* Upload Modal */}
      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onSuccess={onUploadSuccess}
        />
      )}
    </div>
  );
};

export default App;