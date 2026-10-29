"use client";
import { fmt, fmtPct, qlabel } from "@/lib/data";

export type Row = { label: string; level?: number; values: (number | null)[]; pct?: boolean; digits?: number; status?: string; tip?: string };
/** Dönem kolonlu tablo; boş = "—". */
export function Table({ periods, rows, unit }: { periods: string[]; rows: Row[]; unit?: string }) {
  return (
    <div className="tbl-wrap">
      <table>
        <thead><tr><th>{unit ?? ""}</th>{periods.map(p => <th key={p} className="num" title={p}>{qlabel(p)}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className={`lvl${r.level ?? 1}`} title={r.tip}>{r.label}{r.status && r.status !== "VERIFIED" ? <> <span className={`status ${r.status}`}>{r.status}</span></> : null}</td>
              {r.values.map((v, j) => <td key={j} className={`num${typeof v === "number" && v < 0 ? " neg" : ""}`}>{r.pct ? fmtPct(v, r.digits ?? 1) : fmt(v, r.digits ?? 0)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
