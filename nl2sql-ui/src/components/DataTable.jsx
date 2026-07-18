import React, { useState, useMemo } from "react";
import { formatNumber } from "../utils/helpers";
import { downloadCSV, downloadExcel } from "../services/api";
import toast from "react-hot-toast";

const PAGE_SIZE = 10;

const DataTable = ({ data }) => {
  const [page, setPage] = useState(0);
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState("asc");
  const [downloading, setDownloading] = useState(null); // "csv" | "excel" | null

  const columns = useMemo(
    () => (data?.length ? Object.keys(data[0]) : []),
    [data]
  );

  const sorted = useMemo(() => {
    if (!sortCol) return data;
    return [...data].sort((a, b) => {
      const av = a[sortCol];
      const bv = b[sortCol];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      const cmp =
        typeof av === "number"
          ? av - bv
          : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortCol, sortDir]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
    setPage(0);
  };

  const handleDownloadCSV = async () => {
    setDownloading("csv");
    try {
      await downloadCSV();
      toast.success("CSV downloaded!");
    } catch {
      toast.error("CSV download failed.");
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadExcel = async () => {
    setDownloading("excel");
    try {
      await downloadExcel();
      toast.success("Excel downloaded!");
    } catch {
      toast.error("Excel download failed.");
    } finally {
      setDownloading(null);
    }
  };

  const renderCell = (val) => {
    if (val === null || val === undefined)
      return <span className="null-val">—</span>;
    if (typeof val === "number")
      return <span className="num-val">{formatNumber(val)}</span>;
    return String(val);
  };

  if (!data?.length)
    return <p className="empty-result-text">No results returned.</p>;

  return (
    <div className="data-table-wrapper">

      {/* ── Actions bar ─────────────────────────────────────────────── */}
      <div className="table-actions">
        <span className="table-count">
          {data.length.toLocaleString()} rows · {columns.length} columns
        </span>
        <div className="download-group">
          <button
            className="dl-btn"
            onClick={handleDownloadCSV}
            disabled={downloading !== null}
          >
            {downloading === "csv" ? "⏳" : "📄"} CSV
          </button>
          <button
            className="dl-btn"
            onClick={handleDownloadExcel}
            disabled={downloading !== null}
          >
            {downloading === "excel" ? "⏳" : "📊"} Excel
          </button>
        </div>
      </div>

      {/* ── Table ───────────────────────────────────────────────────── */}
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="th-sortable"
                >
                  {col}
                  <span className="sort-indicator">
                    {sortCol === col
                      ? sortDir === "asc"
                        ? " ↑"
                        : " ↓"
                      : " ⇅"}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? "row-even" : "row-odd"}>
                {columns.map((col) => (
                  <td key={col}>{renderCell(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ──────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="page-btn"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            ‹
          </button>
          <span className="page-info">
            Page {page + 1} / {totalPages}
          </span>
          <button
            className="page-btn"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            ›
          </button>
        </div>
      )}
    </div>
  );
};

export default DataTable;