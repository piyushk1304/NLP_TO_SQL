import React, { useState } from "react";
import {
  Database,
  Upload,
  Trash2,
  BarChart3,
  ChevronRight,
  ChevronDown,
  Table,
  Hash,
  Type,
  Zap,
  Github,
} from "lucide-react";

const Sidebar = ({
  schema,
  hasData,
  onUploadClick,
  onClearChat,
  onSampleQuestion,
  sampleQuestions,
}) => {
  const [schemaOpen, setSchemaOpen] = useState(true);

  const getTypeIcon = (type) => {
    const t = (type || "").toUpperCase();
    if (t.includes("INT") || t.includes("REAL") || t.includes("FLOAT") || t.includes("NUM"))
      return <Hash size={12} className="text-blue-400" />;
    return <Type size={12} className="text-emerald-400" />;
  };

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-icon">
          <Zap size={18} />
        </div>
        <div>
          <div className="brand-title">NL2SQL</div>
          <div className="brand-sub">AI Data Analyst</div>
        </div>
      </div>

      {/* Upload Button */}
      <button className="upload-btn" onClick={onUploadClick}>
        <Upload size={16} />
        <span>Upload Dataset</span>
      </button>

      {/* Schema Panel */}
      {hasData && schema && (
        <div className="schema-section">
          <button
            className="schema-toggle"
            onClick={() => setSchemaOpen((o) => !o)}
          >
            <div className="schema-toggle-left">
              <Database size={14} />
              <span>Schema</span>
              <span className="schema-badge">{schema.columns?.length}</span>
            </div>
            {schemaOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>

          {schemaOpen && (
            <div className="schema-body">
              <div className="schema-meta">
                <Table size={12} />
                <span>{schema.table_name}</span>
                <span className="dot">·</span>
                <span>{schema.row_count?.toLocaleString()} rows</span>
              </div>

              <div className="column-list">
                {schema.columns?.map((col) => (
                  <div key={col.name} className="column-item">
                    {getTypeIcon(col.type)}
                    <span className="col-name">{col.name}</span>
                    <span className="col-type">{col.type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sample Questions */}
      <div className="samples-section">
        <div className="samples-label">
          <BarChart3 size={13} />
          <span>Try asking</span>
        </div>
        <div className="samples-list">
          {sampleQuestions.slice(0, 5).map((q, i) => (
            <button
              key={i}
              className="sample-item"
              onClick={() => onSampleQuestion(q)}
              disabled={!hasData}
            >
              <span className="sample-arrow">›</span>
              <span>{q}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <button className="footer-btn danger" onClick={onClearChat}>
          <Trash2 size={14} />
          <span>Clear Chat</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;