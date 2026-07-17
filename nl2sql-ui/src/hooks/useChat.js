import { useState, useCallback } from "react";
import { askQuestion, fetchSchema } from "../services/api";
import { generateId, formatTimestamp } from "../utils/helpers";
import toast from "react-hot-toast";

const useChat = () => {
  const [messages,  setMessages]  = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [schema,    setSchema]    = useState(null);
  const [hasData,   setHasData]   = useState(false);

  // ── Load schema from backend ─────────────────────────────────────────
  const loadSchema = useCallback(async () => {
    try {
      const data = await fetchSchema();

      const rowCount   = data?.row_count   ?? 0;
      const hasColumns = (data?.columns?.length ?? 0) > 0;

      // Only mark as ready when real rows exist
      if (hasColumns && rowCount > 0) {
        setSchema(data);
        setHasData(true);
        console.log(
          `[SCHEMA] Loaded: ${rowCount} rows, ` +
          `${data.columns.length} columns`
        );
        return data;
      }

      // Schema endpoint returned something but with no usable data
      console.log("[SCHEMA] Response has no rows — treating as no data");
      setSchema(null);
      setHasData(false);
      return null;

    } catch (err) {
      // 404  = no file uploaded yet  (expected on fresh start)
      // other = real network / server error
      if (err?.response?.status !== 404) {
        console.warn("[SCHEMA] Unexpected error:", err.message);
      } else {
        console.log("[SCHEMA] 404 — no data uploaded yet");
      }
      setSchema(null);
      setHasData(false);
      return null;
    }
  }, []);

  // ── Add a message to the chat ────────────────────────────────────────
  const addMessage = useCallback((message) => {
    setMessages((prev) => [
      ...prev,
      { id: generateId(), ...message }
    ]);
  }, []);

  // ── Send user question to backend ────────────────────────────────────
  const sendMessage = useCallback(
    async (question) => {
      if (!question.trim() || isLoading) return;

      // Add user bubble
      addMessage({
        role:      "user",
        content:   question,
        timestamp: formatTimestamp(),
      });

      // Add placeholder assistant bubble (loading state)
      const assistantId = generateId();
      setMessages((prev) => [
        ...prev,
        {
          id:        assistantId,
          role:      "assistant",
          content:   null,
          isLoading: true,
          timestamp: formatTimestamp(),
        },
      ]);

      setIsLoading(true);

      try {
        const result = await askQuestion(question);

        // Replace placeholder with real response
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  isLoading:       false,
                  content:         result.rationale,
                  sqlQuery:        result.sql_query,
                  kpiDetected:     result.kpi_detected,
                  confidenceScore: result.confidence_score,
                  executionTime:   result.execution_time,
                  rowsReturned:    result.rows_returned,
                  data:            result.data,
                  cached:          result.cached,
                  status:          "success",
                }
              : m
          )
        );
      } catch (err) {
        // Replace placeholder with error state
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  isLoading: false,
                  content:
                    err.message || "Failed to process your question.",
                  status: "error",
                }
              : m
          )
        );
        toast.error("Query failed. Please try again.");
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, addMessage]
  );

  // ── Clear all messages ───────────────────────────────────────────────
  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  // ── Called after a successful file upload ────────────────────────────
  const onUploadSuccess = useCallback(
    async (uploadData) => {
      // Reload schema so sidebar updates immediately
      await loadSchema();

      addMessage({
        role:      "assistant",
        content:
          `File uploaded successfully! ` +
          `I have loaded your dataset with ` +
          `${uploadData.rows.toLocaleString()} rows and ` +
          `${uploadData.columns.length} columns. ` +
          `You can now ask questions about your data!`,
        timestamp: formatTimestamp(),
        uploadInfo: {
          rows:      uploadData.rows,
          columns:   uploadData.columns,
          tableName: uploadData.table_name,
        },
        status: "success",
      });

      toast.success(
        `Loaded ${uploadData.rows.toLocaleString()} rows successfully!`
      );
    },
    [addMessage, loadSchema]
  );

  return {
    messages,
    isLoading,
    schema,
    hasData,
    sendMessage,
    clearChat,
    loadSchema,
    onUploadSuccess,
  };
};

export default useChat;