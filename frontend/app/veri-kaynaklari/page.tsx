"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function VeriKaynaklari() {
  const [sources, setSources] = useState<any[]>([]);
  const [ver, setVer] = useState<any>(null);
  useEffect(() => { api<any[]>("/api/sources").then(setSources); api<any>("/api/verification").then(setVer); }, []);
  return (
    <>
      <h1>Veri Kaynakları</h1>
      {sources.map(s => (
        <div className="card" key={s.code} style={{ marginBottom: 12 }}>
          <h2 style={{ marginTop: 0 }}>{s.code} — {s.name} <a href={s.base_url} target="_blank" rel="noreferrer">{s.base_url}</a></h2>
          <div className="note">Erişim: {s.access_method} {s.robots_note && `· ${s.robots_note}`}</div>
          <table><thead><tr><th>Veri seti</th><th>Frekans</th><th>Kapsam</th><th>Banka bazında</th><th>Keşif adresi / kalıp</th><th>Yayın gecikmesi</th><th>Durum</th></tr></thead>
            <tbody>{s.datasets.map((d: any) => <tr key={d.code}><td>{d.name}<div className="note">{d.status_note}</div></td><td>{d.frequency}</td><td>{d.scope}</td><td>{d.per_institution ? "Evet" : "Hayır"}</td><td className="note">{d.discovery_url && <a href={d.discovery_url} target="_blank" rel="noreferrer">{d.discovery_url}</a>}<div>{d.url_pattern}</div></td><td>{d.publication_lag_days ?? "—"} gün</td><td><span className={`status ${d.status}`}>{d.status}</span></td></tr>)}</tbody></table>
        </div>
      ))}
      {ver && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Doğrulama tablosu</h2>
          <div style={{ overflowX: "auto" }}>
            <table><thead><tr>{ver.columns.map((c: string) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>{ver.rows.map((r: any, i: number) => <tr key={i}><td>{r.field}</td><td>{r.source}</td><td className="note">{r.file}</td><td>{r.period}</td><td>{r.per_bank}</td><td className="note">{r.cells}</td><td><span className={`status ${r.status}`}>{r.status}</span></td><td className="note">{r.note}</td></tr>)}</tbody></table>
          </div>
          <h3>Öncelikli araştırma soruları</h3>
          {ver.questions.map((q: any, i: number) => <details key={i}><summary>{q.q}</summary><p>{q.a}</p></details>)}
        </div>
      )}
    </>
  );
}
