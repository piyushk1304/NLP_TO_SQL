// ══════════════════════════════════════════════════════════════
// CHART TYPE DETECTION
// ══════════════════════════════════════════════════════════════

/**
 * Detects the best chart type based on:
 * - KPI type returned by LLM
 * - Question keywords
 * - Column structure of result data
 */
export const detectChartType = (data, kpiDetected, question = "") => {
  if (!data || data.length === 0) return null;

  const columns     = Object.keys(data[0]);
  const q           = question.toLowerCase();
  const numericCols = columns.filter((c) => typeof data[0][c] === "number");
  const textCols    = columns.filter((c) => typeof data[0][c] !== "number");

  // ── Guard: need at least one numeric column to draw any chart ────────
  if (numericCols.length === 0) return null;

  // ── KPI-driven detection ─────────────────────────────────────────────
  if (kpiDetected === "growth_rate")    return "line";
  if (kpiDetected === "running_total")  return "area";
  if (kpiDetected === "churn_rate")     return "line";
  if (kpiDetected === "retention_rate") return "bar";
  if (kpiDetected === "aov")            return "bar";

  // ── Question keyword detection ───────────────────────────────────────
  if (
    q.includes("trend")    ||
    q.includes("over time") ||
    q.includes("monthly")  ||
    q.includes("daily")    ||
    q.includes("weekly")   ||
    q.includes("yearly")   ||
    q.includes("growth")
  ) return "line";

  if (
    q.includes("distribut") ||
    q.includes("breakdown") ||
    q.includes("proportion") ||
    q.includes("share")     ||
    q.includes("percentage") ||
    q.includes("ratio")
  ) return "pie";

  if (
    q.includes("scatter")     ||
    q.includes("correlation") ||
    q.includes(" vs ")        ||
    q.includes("versus")
  ) return "scatter";

  if (
    q.includes("running") ||
    q.includes("cumulative")
  ) return "area";

  // ── Data-structure heuristics ────────────────────────────────────────

  // Exactly 2 columns (1 text + 1 number)
  if (
    columns.length === 2 &&
    textCols.length === 1 &&
    numericCols.length === 1
  ) {
    // Count unique text values after aggregation
    const uniqueLabels = new Set(
      data.map((r) => String(r[textCols[0]] ?? ""))
    ).size;
    // Pie for small categorical sets, bar for larger
    return uniqueLabels <= 12 ? "pie" : "bar";
  }

  // Multiple numeric columns → line works best
  if (numericCols.length >= 2) return "line";

  // Has a date / time column → line
  const hasDateCol = columns.some((c) => {
    const cl = c.toLowerCase();
    return (
      cl.includes("date")   ||
      cl.includes("month")  ||
      cl.includes("year")   ||
      cl.includes("week")   ||
      cl.includes("day")    ||
      cl.includes("period") ||
      cl.includes("time")
    );
  });
  if (hasDateCol && data.length > 3) return "line";

  // Default fallback
  return "bar";
};

// ══════════════════════════════════════════════════════════════
// AXIS COLUMN DETECTION
// ══════════════════════════════════════════════════════════════

/**
 * Identifies which column should be the X-axis label
 * and which columns should be the Y-axis values.
 *
 * Priority for X:
 *   1. Date / time column
 *   2. First text column
 *   3. First column in data
 */
export const detectAxisColumns = (data) => {
  if (!data || data.length === 0) return { xKey: null, yKeys: [] };

  const columns     = Object.keys(data[0]);
  const numericCols = columns.filter((c) => typeof data[0][c] === "number");
  const textCols    = columns.filter((c) => typeof data[0][c] !== "number");

  // Prefer date-like column as X axis
  const dateCol = columns.find((c) => {
    const cl = c.toLowerCase();
    return (
      cl.includes("date")   ||
      cl.includes("month")  ||
      cl.includes("year")   ||
      cl.includes("week")   ||
      cl.includes("day")    ||
      cl.includes("period") ||
      cl.includes("time")
    );
  });

  const xKey  = dateCol || textCols[0] || columns[0];
  const yKeys = numericCols.filter((c) => c !== xKey);

  return { xKey, yKeys };
};

// ══════════════════════════════════════════════════════════════
// PIE DATA PREPARATION
// ══════════════════════════════════════════════════════════════

/**
 * Prepares data for pie chart:
 *   1. Aggregates rows with duplicate label values (sum)
 *   2. Sorts descending by value
 *   3. Keeps top N slices
 *   4. Groups remaining slices into an "Others" bucket
 *
 * This prevents the chart from rendering hundreds of tiny slices.
 */
export const preparePieData = (
  data,
  xKey,
  valueKey,
  maxSlices = 10
) => {
  if (!data || !xKey || !valueKey) return [];

  // Step 1 — aggregate duplicate labels
  const aggregated = {};
  data.forEach((row) => {
    const label = String(row[xKey] ?? "Unknown").trim();
    const value = Number(row[valueKey]) || 0;
    if (label === "" || label === "null" || label === "undefined") return;
    aggregated[label] = (aggregated[label] || 0) + value;
  });

  // Step 2 — sort descending
  const sorted = Object.entries(aggregated)
    .map(([name, value]) => ({ name, value }))
    .filter((d) => d.value > 0)          // drop zero-value slices
    .sort((a, b) => b.value - a.value);

  if (sorted.length === 0) return [];

  // Step 3 — if within limit, return as-is
  if (sorted.length <= maxSlices) return sorted;

  // Step 4 — keep top N-1, group the rest into "Others"
  const top    = sorted.slice(0, maxSlices - 1);
  const rest   = sorted.slice(maxSlices - 1);
  const others = rest.reduce((sum, d) => sum + d.value, 0);

  return [...top, { name: "Others", value: others }];
};

// ══════════════════════════════════════════════════════════════
// CHART TITLE
// ══════════════════════════════════════════════════════════════

/**
 * Builds a clean chart title from the user question.
 * Capitalises first letter and trims long strings.
 */
export const buildChartTitle = (question = "") => {
  if (!question || question.trim() === "") return "Query Results";

  const trimmed =
    question.length > 80
      ? question.slice(0, 80) + "…"
      : question;

  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
};

// ══════════════════════════════════════════════════════════════
// NUMBER FORMATTERS
// ══════════════════════════════════════════════════════════════

/**
 * Compact format for axis tick labels (e.g. 1.2M, 45.6K).
 */
export const formatAxisValue = (value) => {
  if (value === null || value === undefined) return "";
  if (typeof value !== "number")            return String(value);

  const abs = Math.abs(value);

  if (abs >= 1_000_000_000)
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000)
    return `${(value / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000)
    return `${(value / 1_000).toFixed(1)}K`;
  if (!Number.isInteger(value))
    return value.toFixed(2);

  return value.toLocaleString();
};

/**
 * Full-precision format for tooltip values.
 */
export const formatTooltipValue = (value) => {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "number")            return String(value);

  return value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
};

// ══════════════════════════════════════════════════════════════
// COLOUR PALETTES
// ══════════════════════════════════════════════════════════════

/**
 * General chart colour palette (bar, line, area, scatter).
 */
export const CHART_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ef4444", // red
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#ec4899", // pink
  "#14b8a6", // teal
];

/**
 * Pie chart palette — slightly adjusted for donut rings.
 * Last slot is muted grey for the "Others" bucket.
 */
export const PIE_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ef4444", // red
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#ec4899", // pink
  "#64748b", // slate  ← "Others"
];

// ══════════════════════════════════════════════════════════════
// ZOOM LEVELS
// ══════════════════════════════════════════════════════════════

/**
 * Available chart height steps (pixels) for zoom in/out.
 * Index 1 (320px) is the default.
 */
export const ZOOM_LEVELS  = [260, 320, 400, 500, 620, 780, 960, 1200];
export const ZOOM_DEFAULT = 1;