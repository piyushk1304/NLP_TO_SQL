import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
});

api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "Unknown error occurred";
    return Promise.reject(new Error(message));
  }
);

export const uploadFile = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/api/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
  return response.data;
};

export const fetchSchema = async () => {
  const response = await api.get("/api/schema");
  return response.data;
};

export const askQuestion = async (question) => {
  const response = await api.post("/api/ask", { question });
  return response.data;
};

// ── Fixed download functions ──────────────────────────────────────────
export const downloadCSV = async () => {
  try {
    const response = await api.get("/api/download/csv", {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "query_result.csv");
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("CSV download failed:", err);
    throw err;
  }
};

export const downloadExcel = async () => {
  try {
    const response = await api.get("/api/download/excel", {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "query_result.xlsx");
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Excel download failed:", err);
    throw err;
  }
};

export const getCacheStats = async () => {
  const response = await api.get("/api/cache/stats");
  return response.data;
};

export const clearCache = async () => {
  const response = await api.delete("/api/cache/clear");
  return response.data;
};

export const healthCheck = async () => {
  const response = await api.get("/health");
  return response.data;
};