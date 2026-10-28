"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Durum() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [dq, setDq] = useState<any[]>([]);
  const load = () => { api<any[]>("/api/jobs").then(setJobs); api<any[]>("/api/documents").then(setDocs); api<any[]>("/api/quality").then(setDq); };
  useEffect(load, []);
  return (
    <>
      <h1>Veri Güncelleme Durumu</h1>
      <p className="note">Veri toplama zamanlayıcı tarafından yayın takvimine göre tetiklenir; kullanıcı dosya indirmez. Her deneme (yöntem, adres, sonuç, neden) kayıt altındadır.</p>
      <div className="card" style={{ marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Veri toplama işleri</h2>
        <table><thead><tr><th>#</th><th>Veri seti</th><th>Dönem</th><th>Tetik</th><th>Başlangıç</th><th>Durum</th><th>Dosya</th><th>Gözlem</th><th>Mesaj</th></tr></thead>
          <tbody>{jobs.map(j => <tr key={j.id}><td>{j.id}</td><td>{j.dataset}</td><td>{j.period}</td><td>{j.trigger}</td><td>{j.started_at && new Date(j.started_at).toLocaleString("tr-TR")}</td><td><span className={`status ${j.status === "success" ? "VERIFIED" : j.status === "failed" ? "ERROR" : "UNVERIFIED"}`}>{j.status}</span></td><td className="num">{j.documents}</td><td className="num">{j.observations}</td><td className="note">{j.message}<details><summary>log</summary><pre>{JSON.stringify(j.log, null, 1)}</pre></details></td></tr>)}</tbody></table>
      </div>
      <div className="card" style={{ marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>Kaynak dosyalar</h2>
        <table><thead><tr><th>Veri seti</th><th>Adres</th><th>Biçim</th><th>SHA-256</th><th>Boyut</th><th>Durum</th><th>Alındı</th><th>Hata</th></tr></thead>
          <tbody>{docs.map(d => <tr key={d.id}><td>{d.dataset}</td><td className="note"><a href={d.url} target="_blank" rel="noreferrer">{d.file_name ?? d.url}</a></td><td>{d.format ?? "—"}</td><td className="note">{d.sha256?.slice(0, 12) ?? "—"}</td><td className="num">{d.size ?? "—"}</td><td><span className={`status ${d.status === "parsed" ? "VERIFIED" : d.status === "failed" ? "ERROR" : "UNVERIFIED"}`}>{d.status}</span></td><td>{d.retrieved_at && new Date(d.retrieved_at).toLocaleString("tr-TR")}</td><td className="note">{d.error}</td></tr>)}</tbody></table>
      </div>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Veri kalitesi kontrolleri</h2>
        <table><thead><tr><th>İş</th><th>Kontrol</th><th>Seviye</th><th>Sonuç</th><th>Gösterge</th><th>Dönem</th><th>Mesaj</th></tr></thead>
          <tbody>{dq.map((c, i) => <tr key={i}><td>{c.job_id}</td><td>{c.check}</td><td>{c.severity}</td><td>{c.passed ? "geçti" : "başarısız"}</td><td>{c.metric ?? "—"}</td><td>{c.period_end ?? "—"}</td><td className="note">{c.message}</td></tr>)}</tbody></table>
      </div>
    </>
  );
}
