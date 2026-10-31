"use client";
import { D, PERIODS, fmt, qlabel } from "@/lib/data";

export default function Veri() {
  const st = (s: string) => D.items.filter(i => i.status === s);
  const rst = D.restatements.filter(r => r.category.startsWith("restatement"));
  const rounding = D.restatements.length - rst.length;
  return (
    <>
      <h1>Veri ve kalite</h1>
      <section><h2>Kaynaklar</h2>
        <ul>{D.meta.sources.map((s, i) => <li key={i}>{s}</li>)}</ul>
        <h3>Bilinen boşluklar</h3><ul className="note">{D.meta.gaps.map((s, i) => <li key={i}>{s}</li>)}</ul>
      </section>
      <section><h2>KAP bildirimleri ({D.meta.filings.length})</h2>
        <div className="tbl-wrap"><table><thead><tr><th>Dönem</th><th>Bildirim</th><th>Yayın</th><th>Birim</th><th>Denetim</th><th>Sonuç</th><th className="num">DB satırı</th></tr></thead>
          <tbody>{D.meta.filings.map(f => <tr key={f.file_id}><td>{f.filing}</td><td><a href={f.url} target="_blank" rel="noreferrer">{f.file_id}</a></td><td>{f.pub_date ?? "—"}</td><td>{f.unit?.toLocaleString("tr-TR")} TL</td><td>{f.audit_type}</td><td>{f.audit_result}</td><td className="num">{f.rows}</td></tr>)}</tbody></table></div>
      </section>
      <section><h2>Tutarlılık kontrolleri (0 = tutarlı)</h2>
        <div className="tbl-wrap"><table><thead><tr><th>Kontrol</th>{Object.keys(D.checks[0].values).map(p => <th key={p} className="num">{qlabel(p)}</th>)}</tr></thead>
          <tbody>{D.checks.map((c, i) => <tr key={i}><td>{c.name}</td>{Object.values(c.values).map((v, j) => <td key={j} className="num">{typeof v === "number" ? fmt(v, 3) : v ?? "—"}</td>)}</tr>)}</tbody></table></div>
      </section>
      <section><h2>Yeniden sınıflamalar ({rst.length}; ayrıca {rounding} satır 2026Ç2 mn TL yuvarlaması / HBK)</h2>
        <div className="tbl-wrap"><table><thead><tr><th>Seri</th><th>Dönem</th><th>Orijinal</th><th className="num">mn</th><th>Sonraki</th><th className="num">mn</th><th className="num">Fark</th></tr></thead>
          <tbody>{rst.map((r, i) => <tr key={i}><td style={{ fontSize: 11 }}>{r.series_key}</td><td>{r.p_end}</td><td>{r.orig_filing}</td><td className="num">{fmt(r.orig, 1)}</td><td>{r.later_filing}</td><td className="num">{fmt(r.later, 1)}</td><td className="num">{fmt(r.diff, 1)}</td></tr>)}</tbody></table></div>
      </section>
      <section><h2>Kur tablosu (TCMB döviz alış, dönem sonunda geçerli)</h2>
        <div className="tbl-wrap"><table><thead><tr><th>Dönem</th><th className="num">USD/TRY</th><th className="num">EUR/TRY</th><th>Kaynak</th></tr></thead>
          <tbody>{PERIODS.map(p => <tr key={p}><td>{p}</td><td className="num">{fmt(D.fx.rates[p]?.usd, 4)}</td><td className="num">{fmt(D.fx.rates[p]?.eur, 4)}</td><td className="note">{D.fx.sources[p] ?? D.fx.sources.default}</td></tr>)}</tbody></table></div>
        <div className="note">Stoklar dönem sonu kuruyla; çeyreklik akımlar (önceki dönem sonu + dönem sonu)/2 ile çevrilir. 30.09.2021 kuru 2 ondalık (ikincil kaynak).</div>
      </section>
      <section><h2>Blanco veri sözlüğü kalem durumu</h2>
        <p className="note">VERIFIED {st("VERIFIED").length} · DERIVED {st("DERIVED").length} · UNAVAILABLE (KAP ana tablosunda yok) {st("UNAVAILABLE").length} — UNAVAILABLE olanların çoğu Dipnotlar sekmesinde TBB kitabından 2025Ç4–2026Ç2 için mevcut.</p>
        <div className="tbl-wrap"><table><thead><tr><th>Kod</th><th>Kalem</th><th>Bölüm</th><th>Durum</th><th>Kaynak / formül</th><th>Not</th></tr></thead>
          <tbody>{D.items.map(i => <tr key={i.code}><td style={{ fontSize: 11 }}>{i.code}</td><td>{i.name}</td><td>{i.section}</td><td><span className={`status ${i.status}`}>{i.status}</span></td><td style={{ fontSize: 11 }}>{i.source}</td><td className="note">{i.note}</td></tr>)}</tbody></table></div>
      </section>
    </>
  );
}
