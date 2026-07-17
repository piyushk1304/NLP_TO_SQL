import React, { useState, useCallback, useRef, useEffect } from "react";
import html2canvas from "html2canvas";
import {
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  PieChart, Pie, Cell, Sector,
  ScatterChart, Scatter,
  XAxis, YAxis, ZAxis,
  CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
  ReferenceLine, Label,
} from "recharts";
import {
  detectChartType,
  detectAxisColumns,
  buildChartTitle,
  formatAxisValue,
  formatTooltipValue,
  preparePieData,
  CHART_COLORS,
  PIE_COLORS,
  ZOOM_LEVELS,
  ZOOM_DEFAULT,
} from "../utils/chartHelper";
import toast from "react-hot-toast";

// ══════════════════════════════════════════════════════════════
// ZOOM HOOK
// ══════════════════════════════════════════════════════════════
const useZoom = () => {
  const [zoomIdx, setZoomIdx] = useState(ZOOM_DEFAULT);

  const zoomIn = useCallback(
    () => setZoomIdx((i) => Math.min(i + 1, ZOOM_LEVELS.length - 1)),
    []
  );
  const zoomOut = useCallback(
    () => setZoomIdx((i) => Math.max(i - 1, 0)),
    []
  );
  const resetZoom = useCallback(
    () => setZoomIdx(ZOOM_DEFAULT),
    []
  );

  return {
    height:  ZOOM_LEVELS[zoomIdx],
    zoomIn,
    zoomOut,
    resetZoom,
    canIn:   zoomIdx < ZOOM_LEVELS.length - 1,
    canOut:  zoomIdx > 0,
    zoomIdx,
    total:   ZOOM_LEVELS.length,
    percent: Math.round(((zoomIdx + 1) / ZOOM_LEVELS.length) * 100),
  };
};

// ══════════════════════════════════════════════════════════════
// SCROLL ZOOM HOOK
// ══════════════════════════════════════════════════════════════
const useScrollZoom = (zoomIn, zoomOut) => {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const handler = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.deltaY < 0) zoomIn();
      else zoomOut();
    };

    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, [zoomIn, zoomOut]);

  return ref;
};

// ══════════════════════════════════════════════════════════════
// JPEG DOWNLOAD HOOK
// ══════════════════════════════════════════════════════════════
const useChartDownload = (chartBodyRef, title) => {
  const [downloading, setDownloading] = useState(false);

  const downloadJPEG = useCallback(async () => {
    const el = chartBodyRef.current;
    if (!el) {
      toast.error("Chart not ready for download.");
      return;
    }

    setDownloading(true);
    const loadingToast = toast.loading("Capturing chart…");

    try {
      // Wait a tick so any tooltip/hover state clears
      await new Promise((r) => setTimeout(r, 120));

      const canvas = await html2canvas(el, {
        backgroundColor: "#0f172a",   // match --bg-main
        scale:           2,           // 2x for crisp JPEG
        useCORS:         true,
        logging:         false,
        imageTimeout:    0,
        removeContainer: true,
      });

      // Convert to JPEG blob
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            toast.dismiss(loadingToast);
            toast.error("Failed to generate image.");
            setDownloading(false);
            return;
          }

          // Build safe filename from chart title
          const safeName = (title || "chart")
            .replace(/[^a-zA-Z0-9\s]/g, "")
            .trim()
            .replace(/\s+/g, "_")
            .slice(0, 60);

          const timestamp = new Date()
            .toISOString()
            .slice(0, 19)
            .replace(/[T:]/g, "-");

          const filename = `${safeName}_${timestamp}.jpg`;

          // Trigger download
          const url  = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href     = url;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          link.remove();
          URL.revokeObjectURL(url);

          toast.dismiss(loadingToast);
          toast.success("Chart downloaded as JPEG!");
          setDownloading(false);
        },
        "image/jpeg",
        0.95    // quality 0–1
      );
    } catch (err) {
      console.error("[CHART DOWNLOAD]", err);
      toast.dismiss(loadingToast);
      toast.error("Download failed. Please try again.");
      setDownloading(false);
    }
  }, [chartBodyRef, title]);

  return { downloadJPEG, downloading };
};

// ══════════════════════════════════════════════════════════════
// SHARED — CUSTOM TOOLTIP
// ══════════════════════════════════════════════════════════════
const CustomTooltip = ({ active, payload, label, labelKey }) => {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="chart-tooltip">
      {label !== undefined && label !== null && (
        <div className="tooltip-label">
          {labelKey ? `${labelKey}: ` : ""}
          {String(label)}
        </div>
      )}
      <div className="tooltip-rows">
        {payload.map((entry, i) => (
          <div key={i} className="tooltip-row">
            <span
              className="tooltip-dot"
              style={{ backgroundColor: entry.color || entry.fill }}
            />
            <span className="tooltip-name">{entry.name}</span>
            <span className="tooltip-value">
              {formatTooltipValue(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// SHARED — AXIS / GRID HELPERS
// ══════════════════════════════════════════════════════════════
const buildXAxisProps = (xKey, dataLen) => ({
  dataKey:    xKey,
  tick:       { fill: "#94a3b8", fontSize: 11 },
  tickLine:   false,
  axisLine:   { stroke: "rgba(255,255,255,0.08)" },
  tickFormatter: (val) =>
    typeof val === "string" && val.length > 13
      ? val.slice(0, 12) + "…"
      : val,
  angle:      dataLen > 8 ? -35 : 0,
  textAnchor: dataLen > 8 ? "end" : "middle",
  interval:   dataLen > 20 ? Math.floor(dataLen / 10) : 0,
  label: {
    value:    xKey,
    position: "insideBottom",
    offset:   -46,
    fill:     "#64748b",
    fontSize: 11,
  },
});

const buildYAxisProps = () => ({
  tickFormatter: formatAxisValue,
  tick:          { fill: "#94a3b8", fontSize: 11 },
  tickLine:      false,
  axisLine:      false,
  width:         64,
});

const SharedGrid = () => (
  <CartesianGrid
    strokeDasharray="3 3"
    stroke="rgba(255,255,255,0.06)"
    vertical={false}
  />
);

const SharedLegend = ({ show }) =>
  show ? (
    <Legend
      wrapperStyle={{ fontSize: 12, color: "#94a3b8", paddingTop: 8 }}
    />
  ) : null;

const ChartTitle = ({ title }) => (
  <div className="chart-title">{title}</div>
);

// ══════════════════════════════════════════════════════════════
// BAR CHART
// ══════════════════════════════════════════════════════════════
const BarView = ({ data, title, height }) => {
  const { xKey, yKeys } = detectAxisColumns(data);
  if (!xKey || !yKeys.length) return null;
  const multiColor = yKeys.length === 1;

  return (
    <div className="chart-container">
      <ChartTitle title={title} />
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{ top: 10, right: 30, left: 10, bottom: 64 }}
          barCategoryGap="30%"
        >
          <SharedGrid />
          <XAxis {...buildXAxisProps(xKey, data.length)} />
          <YAxis {...buildYAxisProps()} />
          <Tooltip
            content={<CustomTooltip labelKey={xKey} />}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
          />
          <SharedLegend show={yKeys.length > 1} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
          {yKeys.map((key, idx) => (
            <Bar
              key={key}
              dataKey={key}
              name={key}
              fill={CHART_COLORS[idx % CHART_COLORS.length]}
              radius={[4, 4, 0, 0]}
              maxBarSize={56}
            >
              {multiColor &&
                data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={CHART_COLORS[i % CHART_COLORS.length]}
                  />
                ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// LINE CHART
// ══════════════════════════════════════════════════════════════
const ActiveDot = ({ cx, cy, fill }) => (
  <g>
    <circle cx={cx} cy={cy} r={8}  fill={fill} fillOpacity={0.15} />
    <circle cx={cx} cy={cy} r={4}  fill={fill} />
    <circle cx={cx} cy={cy} r={4}  fill="none" stroke="#fff" strokeWidth={1.5} />
  </g>
);

const LineView = ({ data, title, height }) => {
  const { xKey, yKeys } = detectAxisColumns(data);
  if (!xKey || !yKeys.length) return null;

  return (
    <div className="chart-container">
      <ChartTitle title={title} />
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={data}
          margin={{ top: 10, right: 30, left: 10, bottom: 64 }}
        >
          <SharedGrid />
          <XAxis {...buildXAxisProps(xKey, data.length)} />
          <YAxis {...buildYAxisProps()} />
          <Tooltip
            content={<CustomTooltip labelKey={xKey} />}
            cursor={{ stroke: "rgba(255,255,255,0.12)", strokeWidth: 1 }}
          />
          <SharedLegend show={yKeys.length > 1} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.06)" />
          {yKeys.map((key, idx) => {
            const color = CHART_COLORS[idx % CHART_COLORS.length];
            return (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                name={key}
                stroke={color}
                strokeWidth={2.5}
                dot={{ r: 3, fill: color, strokeWidth: 0 }}
                activeDot={<ActiveDot fill={color} />}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// AREA CHART
// ══════════════════════════════════════════════════════════════
const AreaView = ({ data, title, height }) => {
  const { xKey, yKeys } = detectAxisColumns(data);
  if (!xKey || !yKeys.length) return null;

  return (
    <div className="chart-container">
      <ChartTitle title={title} />
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={data}
          margin={{ top: 10, right: 30, left: 10, bottom: 64 }}
        >
          <defs>
            {yKeys.map((key, idx) => (
              <linearGradient
                key={key}
                id={`areaGrad_${idx}`}
                x1="0" y1="0"
                x2="0" y2="1"
              >
                <stop
                  offset="5%"
                  stopColor={CHART_COLORS[idx % CHART_COLORS.length]}
                  stopOpacity={0.25}
                />
                <stop
                  offset="95%"
                  stopColor={CHART_COLORS[idx % CHART_COLORS.length]}
                  stopOpacity={0.02}
                />
              </linearGradient>
            ))}
          </defs>
          <SharedGrid />
          <XAxis {...buildXAxisProps(xKey, data.length)} />
          <YAxis {...buildYAxisProps()} />
          <Tooltip
            content={<CustomTooltip labelKey={xKey} />}
            cursor={{ stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }}
          />
          <SharedLegend show={yKeys.length > 1} />
          {yKeys.map((key, idx) => {
            const color = CHART_COLORS[idx % CHART_COLORS.length];
            return (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                name={key}
                stroke={color}
                strokeWidth={2.5}
                fill={`url(#areaGrad_${idx})`}
                dot={{ r: 3, fill: color, strokeWidth: 0 }}
                activeDot={{
                  r: 5,
                  fill: color,
                  stroke: "#fff",
                  strokeWidth: 1.5,
                }}
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// PIE CHART
// ══════════════════════════════════════════════════════════════
const ActiveSlice = (props) => {
  const {
    cx, cy,
    innerRadius, outerRadius,
    startAngle, endAngle,
    fill, payload, value, percent,
  } = props;

  return (
    <g>
      <Sector
        cx={cx} cy={cy}
        innerRadius={outerRadius + 4}
        outerRadius={outerRadius + 10}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        opacity={0.2}
      />
      <Sector
        cx={cx} cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 6}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      <text
        x={cx} y={cy - 14}
        textAnchor="middle"
        fill="#f1f5f9"
        fontSize={13}
        fontWeight={600}
      >
        {String(payload.name).length > 16
          ? String(payload.name).slice(0, 15) + "…"
          : payload.name}
      </text>
      <text
        x={cx} y={cy + 6}
        textAnchor="middle"
        fill="#94a3b8"
        fontSize={12}
      >
        {formatTooltipValue(value)}
      </text>
      <text
        x={cx} y={cy + 24}
        textAnchor="middle"
        fill="#64748b"
        fontSize={11}
      >
        {(percent * 100).toFixed(1)}%
      </text>
    </g>
  );
};

const PieView = ({ data, title, height }) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const { xKey, yKeys } = detectAxisColumns(data);
  if (!xKey || !yKeys.length) return null;

  const valueKey    = yKeys[0];
  const pieData     = preparePieData(data, xKey, valueKey, 10);
  if (pieData.length === 0) return null;

  const outerRadius = Math.min(height * 0.30, 140);
  const innerRadius = Math.min(height * 0.16, 76);

  return (
    <div className="chart-container">
      <ChartTitle title={title} />

      {data.length > 10 && (
        <div className="pie-info-pill">
          Top 10 of {data.length} items shown · rest grouped into Others
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="46%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            dataKey="value"
            nameKey="name"
            activeIndex={activeIndex}
            activeShape={ActiveSlice}
            onMouseEnter={(_, i) => setActiveIndex(i)}
            paddingAngle={2}
            strokeWidth={0}
          >
            {pieData.map((_, idx) => (
              <Cell
                key={idx}
                fill={PIE_COLORS[idx % PIE_COLORS.length]}
              />
            ))}
          </Pie>

          <Tooltip
            formatter={(value, name) => [formatTooltipValue(value), name]}
            contentStyle={{
              background:   "#1e293b",
              border:       "1px solid #1e3352",
              borderRadius: 10,
              color:        "#f1f5f9",
              fontSize:     12,
            }}
          />

          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            iconType="circle"
            iconSize={8}
            wrapperStyle={{
              fontSize:   11,
              color:      "#94a3b8",
              paddingTop: 6,
            }}
            formatter={(val) =>
              val.length > 18 ? val.slice(0, 17) + "…" : val
            }
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// SCATTER CHART
// ══════════════════════════════════════════════════════════════
const ScatterView = ({ data, title, height }) => {
  const { xKey, yKeys } = detectAxisColumns(data);
  if (!xKey || !yKeys.length) return null;

  const yKey        = yKeys[0];
  const scatterData = data.map((row) => ({
    x: row[xKey],
    y: row[yKey],
    ...row,
  }));

  return (
    <div className="chart-container">
      <ChartTitle title={title} />
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart
          margin={{ top: 10, right: 30, left: 10, bottom: 36 }}
        >
          <SharedGrid />
          <XAxis
            type="number"
            dataKey="x"
            name={xKey}
            tickFormatter={formatAxisValue}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
          >
            <Label
              value={xKey}
              offset={-10}
              position="insideBottom"
              fill="#64748b"
              fontSize={11}
            />
          </XAxis>
          <YAxis
            type="number"
            dataKey="y"
            name={yKey}
            tickFormatter={formatAxisValue}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={64}
          >
            <Label
              value={yKey}
              angle={-90}
              position="insideLeft"
              fill="#64748b"
              fontSize={11}
            />
          </YAxis>
          <ZAxis range={[40, 40]} />
          <Tooltip
            cursor={{
              strokeDasharray: "3 3",
              stroke: "rgba(255,255,255,0.15)",
            }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0]?.payload;
              return (
                <div className="chart-tooltip">
                  {Object.entries(d)
                    .filter(([k]) => k !== "x" && k !== "y")
                    .map(([k, v], i) => (
                      <div key={i} className="tooltip-row">
                        <span className="tooltip-name">{k}</span>
                        <span className="tooltip-value">
                          {String(v ?? "—")}
                        </span>
                      </div>
                    ))}
                </div>
              );
            }}
          />
          <Scatter
            data={scatterData}
            fill={CHART_COLORS[0]}
            fillOpacity={0.75}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════
// CHART TYPE CONFIG
// ══════════════════════════════════════════════════════════════
const CHART_TYPES = [
  { key: "bar",     label: "Bar",     icon: "▐▐"  },
  { key: "line",    label: "Line",    icon: "〜"   },
  { key: "area",    label: "Area",    icon: "◭"    },
  { key: "pie",     label: "Pie",     icon: "◔"    },
  { key: "scatter", label: "Scatter", icon: "⁚⁚"  },
];

// ══════════════════════════════════════════════════════════════
// ZOOM BAR
// ══════════════════════════════════════════════════════════════
const ZoomBar = ({
  zoomIn, zoomOut, resetZoom,
  canIn, canOut,
  zoomIdx, total, percent,
  onDownload, downloading,
}) => (
  <div className="zoom-bar">
    {/* Zoom out */}
    <button
      className="zoom-btn"
      onClick={zoomOut}
      disabled={!canOut}
      title="Zoom out (or scroll ↓ on chart)"
    >
      −
    </button>

    {/* Progress track */}
    <div
      className="zoom-track"
      title={`Zoom level ${zoomIdx + 1} of ${total}`}
    >
      <div
        className="zoom-track-fill"
        style={{ width: `${percent}%` }}
      />
    </div>

    {/* Zoom in */}
    <button
      className="zoom-btn"
      onClick={zoomIn}
      disabled={!canIn}
      title="Zoom in (or scroll ↑ on chart)"
    >
      +
    </button>

    {/* Reset */}
    <button
      className="zoom-reset-btn"
      onClick={resetZoom}
      title="Reset zoom"
    >
      ↺
    </button>

    {/* Height label */}
    <span className="zoom-level-label">
      {ZOOM_LEVELS[zoomIdx]}px
    </span>

    {/* Divider */}
    <div className="zoom-divider" />

    {/* Download JPEG button */}
    <button
      className={`chart-download-btn ${downloading ? "chart-download-btn-loading" : ""}`}
      onClick={onDownload}
      disabled={downloading}
      title="Download chart as JPEG"
    >
      {downloading ? (
        <>
          <span className="dl-spinner" />
          <span>Saving…</span>
        </>
      ) : (
        <>
          <span className="dl-icon">⬇</span>
          <span>JPEG</span>
        </>
      )}
    </button>
  </div>
);

// ══════════════════════════════════════════════════════════════
// SCROLL HINT
// ══════════════════════════════════════════════════════════════
const ScrollHint = ({ visible }) => (
  <div className={`scroll-hint ${visible ? "scroll-hint-visible" : ""}`}>
    🖱 Scroll to zoom
  </div>
);

// ══════════════════════════════════════════════════════════════
// MAIN EXPORT — ChartRenderer
// ══════════════════════════════════════════════════════════════
const ChartRenderer = ({ data, kpiDetected, question }) => {
  const autoType = detectChartType(data, kpiDetected, question);

  const [chartType,   setChartType]   = useState(autoType);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showHint,    setShowHint]    = useState(false);
  const [hintShown,   setHintShown]   = useState(false);

  const {
    height, zoomIn, zoomOut, resetZoom,
    canIn, canOut, zoomIdx, total, percent,
  } = useZoom();

  // Refs
  const scrollRef  = useScrollZoom(zoomIn, zoomOut);
  const chartTitle = buildChartTitle(question);

  // Download hook — targets the chart body div
  const { downloadJPEG, downloading } = useChartDownload(scrollRef, chartTitle);

  // Scroll hint on first hover
  const handleMouseEnter = useCallback(() => {
    if (!hintShown) {
      setShowHint(true);
      setHintShown(true);
      setTimeout(() => setShowHint(false), 2000);
    }
  }, [hintShown]);

  if (!autoType || !data || data.length < 2) return null;

  const renderChart = () => {
    const props = { data, title: chartTitle, height };
    switch (chartType) {
      case "bar":     return <BarView     {...props} />;
      case "line":    return <LineView    {...props} />;
      case "area":    return <AreaView    {...props} />;
      case "pie":     return <PieView     {...props} />;
      case "scatter": return <ScatterView {...props} />;
      default:        return <BarView     {...props} />;
    }
  };

  return (
    <div className="chart-wrapper">

      {/* ── Header ────────────────────────────────────────────── */}
      <div className="chart-header">

        {/* Auto badge */}
        <div className="chart-auto-badge">
          <span className="chart-auto-dot" />
          <span>
            Auto: {autoType.charAt(0).toUpperCase() + autoType.slice(1)}
          </span>
        </div>

        {/* Type switcher */}
        <div className="chart-type-switcher">
          {CHART_TYPES.map((t) => (
            <button
              key={t.key}
              className={`chart-type-btn ${
                chartType === t.key ? "chart-type-active" : ""
              }`}
              onClick={() => setChartType(t.key)}
              title={t.label}
            >
              <span className="chart-type-icon">{t.icon}</span>
              <span className="chart-type-label">{t.label}</span>
            </button>
          ))}
        </div>

        {/* Collapse */}
        <button
          className="chart-collapse-btn"
          onClick={() => setIsCollapsed((c) => !c)}
          title={isCollapsed ? "Show chart" : "Hide chart"}
        >
          {isCollapsed ? "▾ Show" : "▴ Hide"}
        </button>
      </div>

      {/* ── Zoom bar + download ────────────────────────────────── */}
      {!isCollapsed && (
        <div className="chart-zoom-row">
          <ZoomBar
            zoomIn={zoomIn}
            zoomOut={zoomOut}
            resetZoom={resetZoom}
            canIn={canIn}
            canOut={canOut}
            zoomIdx={zoomIdx}
            total={total}
            percent={percent}
            onDownload={downloadJPEG}
            downloading={downloading}
          />
        </div>
      )}

      {/* ── Chart body (scroll + download target) ─────────────── */}
      {!isCollapsed && (
        <div
          ref={scrollRef}
          className="chart-body"
          onMouseEnter={handleMouseEnter}
        >
          <ScrollHint visible={showHint} />
          {renderChart()}
        </div>
      )}
    </div>
  );
};

export default ChartRenderer;