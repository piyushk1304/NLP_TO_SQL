import React, { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check, ChevronDown, ChevronRight, Code2 } from "lucide-react";
import toast from "react-hot-toast";

const SQLViewer = ({ sql }) => {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      toast.success("SQL copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Copy failed");
    }
  };

  return (
    <div className="sql-viewer">
      <button className="sql-toggle" onClick={() => setOpen((o) => !o)}>
        <div className="sql-toggle-left">
          <Code2 size={13} />
          <span>Generated SQL</span>
        </div>
        <div className="sql-toggle-right">
          {open && (
            <button className="copy-btn" onClick={handleCopy}>
              {copied ? <Check size={12} /> : <Copy size={12} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
          )}
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {open && (
        <div className="sql-content">
          <SyntaxHighlighter
            language="sql"
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              borderRadius: "0 0 8px 8px",
              fontSize: "12.5px",
              lineHeight: "1.6",
              background: "#0d1117",
              padding: "16px",
            }}
            showLineNumbers
            lineNumberStyle={{ color: "#4a5568", minWidth: "2em" }}
          >
            {sql}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
};

export default SQLViewer;