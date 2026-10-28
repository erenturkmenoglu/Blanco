"use client";
import { useEffect, useState } from "react";
import { api, Bank, fmt } from "@/lib/api";
import Provenance from "@/components/Provenance";
import { SeriesChart } from "@/components/SeriesChart";

const METRICS = ["total_assets", "loans_gross", "total_deposits", "total_equity", "net_profit", "net_interest_income", "npl_amount", "employee_count", "branch_count"];

export default function Karsilastirmalar() {
  const [banks, setBanks] = useState<Bank[]>([]);
  const [sel, setSel] = useState<string[]>([]);
  const [metric, setMetric] = useState("total_assets");
  const [periods, setPeriods] = useState<string[]>([]);
  const [period, setPeriod] = useState("");
  const [scope, setScope] = useState("solo");
  const [rows, setRows] = useState<any[]>([]);
  // varsayılan seçim: en güncel solo toplam aktife göre en büyük 8 banka (değeri olmayanlar seçilmez, 0 sayılmaz)
  useEffect(() => { api<Bank[]>("/api/banks").then(b => { setBanks(b); setSel([...b].filter(x => x.latest_total_assets != null).sort((x, y) => (y.latest_total_assets ?? 0) - (x.latest_total_assets ?? 0)).slice(0, 8).map(x => x.code)); }); }, []);
  useEffect(() => { api<any[]>("/api/periods").then(p => { const ps = Array.from(new Set(p.filter(x => x.scope === scope).map(x => x.period_end as string))); setPeriods(ps); setPeriod(ps[0] ?? ""); }); }, [scope]);
  useEffect(() => { if (!sel.length || !period) { setRows([]); return; } api<any>("/api/compare", { banks: sel.join(","), metric, period_end: period, scope }).then(r => setRows(r.rows)); }, [sel, metric, period, scope]);
  const unit = ["employee_count", "branch_count"].includes(metric) ? "count" : "TRY";
  return (
    <>
      <h1>Bankalar Arası Karşılaştırma</h1>
      <div className="controls">
        <label>Bankalar (çoklu)<select multiple size={8} value={sel} onChange={e => setSel(Array.from(e.target.selectedOptions).map(o => o.value))}>{banks.map(b => <option key={b.code} value={b.code}>{b.name}</option>)}</select></label>
        <label>Gösterge<select value={metric} onChange={e => setMetric(e.target.value)}>{METRICS.map(m => <option key={m}>{m}</option>)}</select></label>
        <label>Dönem<select value={period} onChange={e => setPeriod(e.target.value)}>{periods.map(p => <option key={p}>{p}</option>)}</select></label>
        <label>Kapsam<select value={scope} onChange={e => setScope(e.target.value)}><option value="solo">Solo</option><option value="consolidated">Konsolide</option></select></label>
      </div>
      <div className="card">
        <table><thead><tr><th>#</th><th>Banka</th><th className="num">{metric}</th><th>Durum</th></tr></thead>
          <tbody>{[...rows].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999)).map(r => <tr key={r.bank}><td>{r.rank ?? "—"}</td><td>{r.name ?? r.bank}</td><td className="num">{fmt(r.value, unit)}</td><td><span className={`status ${r.status}`}>{r.status}</span></td></tr>)}</tbody></table>
        {rows.some(r => r.value !== null) && <SeriesChart kind="bar" data={rows.filter(r => r.value !== null).map(r => ({ x: r.name ?? r.bank, v: r.value }))} series={[{ key: "v", name: metric }]} unit={unit} />}
        <Provenance period={period} unit={unit} method="Sıralama yalnızca değeri olan bankalar arasında; eksik veri sıralamaya girmez ve 0 sayılmaz. Sektör ortalaması ayrı katmandır." />
      </div>
    </>
  );
}
