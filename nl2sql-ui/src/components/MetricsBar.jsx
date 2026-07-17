import React from "react";
import {
  Clock,
  Rows,
  Target,
  Zap,
  CheckCircle2,
} from "lucide-react";
import {
  getConfidenceColor,
  getConfidenceLabel,
  getKPIBadgeColor,
  formatKPILabel,
} from "../utils/helpers";

const MetricsBar = ({ kpiDetected, confidenceScore, executionTime, rowsReturned, cached }) => {
  return (
    <div className="metrics-bar">
      {/* KPI Badge */}
      <div
        className="metric-badge kpi-badge"
        style={{ backgroundColor: `${getKPIBadgeColor(kpiDetected)}20`, borderColor: `${getKPIBadgeColor(kpiDetected)}40`, color: getKPIBadgeColor(kpiDetected) }}
      >
        <Target size={11} />
        <span>{formatKPILabel(kpiDetected)}</span>
      </div>

      {/* Confidence */}
      <div className="metric-badge">
        <div
          className="confidence-dot"
          style={{ backgroundColor: getConfidenceColor(confidenceScore) }}
        />
        <span style={{ color: getConfidenceColor(confidenceScore) }}>
          {getConfidenceLabel(confidenceScore)} ({confidenceScore?.toFixed(1)}%)
        </span>
      </div>

      {/* Rows */}
      <div className="metric-badge">
        <Rows size={11} className="text-slate-400" />
        <span>{rowsReturned?.toLocaleString()} rows</span>
      </div>

      {/* Time */}
      <div className="metric-badge">
        <Clock size={11} className="text-slate-400" />
        <span>{executionTime?.toFixed(3)}s</span>
      </div>

      {/* Cached */}
      {cached && (
        <div className="metric-badge cached-badge">
          <Zap size={11} />
          <span>Cached</span>
        </div>
      )}
    </div>
  );
};

export default MetricsBar;