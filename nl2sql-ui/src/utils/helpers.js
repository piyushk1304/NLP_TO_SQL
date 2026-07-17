import { format } from "date-fns";

export const formatTimestamp = (date = new Date()) =>
  format(date, "HH:mm");

export const formatNumber = (num) => {
  if (num === null || num === undefined) return "—";
  if (typeof num !== "number") return String(num);
  if (Number.isInteger(num)) return num.toLocaleString();
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

export const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const getConfidenceColor = (score) => {
  if (score >= 80) return "#10b981"; // green
  if (score >= 60) return "#f59e0b"; // amber
  return "#ef4444"; // red
};

export const getConfidenceLabel = (score) => {
  if (score >= 80) return "High";
  if (score >= 60) return "Medium";
  return "Low";
};

export const getKPIBadgeColor = (kpi) => {
  const colors = {
    growth_rate: "#6366f1",
    retention_rate: "#10b981",
    churn_rate: "#ef4444",
    aov: "#f59e0b",
    running_total: "#3b82f6",
    none: "#64748b",
  };
  return colors[kpi] || "#64748b";
};

export const formatKPILabel = (kpi) => {
  const labels = {
    growth_rate: "Growth Rate",
    retention_rate: "Retention Rate",
    churn_rate: "Churn Rate",
    aov: "Avg Order Value",
    running_total: "Running Total",
    none: "Standard Query",
  };
  return labels[kpi] || kpi;
};

export const generateId = () =>
  `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const SAMPLE_QUESTIONS = [
  "What is the total revenue by region?",
  "Show me the top 10 customers by sales",
  "Calculate the monthly growth rate of sales",
  "What is the average order value?",
  "Show me the running total of sales over time",
  "Which product category has the highest revenue?",
  "What is the customer retention rate?",
  "Show me sales trends by month",
];