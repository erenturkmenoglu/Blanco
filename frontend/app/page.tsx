"use client";
import { useEffect, useState } from "react";
import { api, Bank } from "@/lib/api";
import Provenance from "@/components/Provenance";

export default function Overview() {
  const [banks, setBanks] = useState<Bank[]>([]);
  const [periods, setPeriods] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([api<Bank[]>("/api/banks"), api<any[]>("/api/periods"), api<any[]>("/api/jobs", { limit: 5 }), api<any[]>("/api/sources")])
      .then(([b, p, j, s]) => { setBanks(b); setPeriods(p); setJobs(j); setSources(s); }).catch(e => setErr(String(e)));
  }, []);
  const withData = banks.filter(b => b.observations > 0);
  const datasets = sources.flatMap(s => s.datasets.map((d: any) => ({ ...d, source: s.code })));
  return (
    <>
      <h1>Genel Bakış — Bankalar modülü</h1>
      {err && <p className="note">API'ye ulaşılamadı: {err}</p>}
      <div className="grid">
        <div className="card"><div className="note">Kayıtlı banka</div><div className="kpi">{banks.length}</div><div className="note">{withData.length} bankada doğrulanmış gözlem var</div></div>
        <div className="card"><div className="note">Son dönem (gözlem olan)</div><div className="kpi">{periods[0]?.period_end ?? "—"}</div><div className="note">{periods.length} dönem</div></div>
        <div className="card"><div className="note">Veri setleri</div><div className="kpi">{datasets.length}</div>
          <div className="note">{["VERIFIED", "UNVERIFIED", "UNAVAILABLE", "ERROR"].map(s => `${s}: ${datasets.filter(d => d.status === s).length}`).join(" · ")}</div></div>
        <div className="card"><div className="note">Son veri toplama işi</div><div className="kpi">{jobs[0]?.status ?? "—"}</div><div className="note">{jobs[0] ? `${jobs[0].dataset} ${jobs[0].period} — ${jobs[0].message}` : "henüz çalışmadı"}</div></div>
      </div>
      <h2>Veri setleri ve doğrulama durumu</h2>
      <div className="card">
        <table><thead><tr><th>Kaynak</th><th>Veri seti</th><th>Frekans</th><th>Kapsam</th><th>Banka bazında</th><th>Durum</th></tr></thead>
          <tbody>{datasets.map(d => <tr key={d.code}><td>{d.source}</td><td>{d.name}<div className="note">{d.status_note}</div></td><td>{d.frequency}</td><td>{d.scope}</td><td>{d.per_institution ? "Evet" : "Hayır"}</td><td><span className={`status ${d.status}`}>{d.status}</span></td></tr>)}</tbody></table>
        <Provenance method="Durumlar veri keşfi bulgularıdır; dosya açılıp alan görülmeden VERIFIED yazılmaz." />
      </div>
    </>
  );
}
