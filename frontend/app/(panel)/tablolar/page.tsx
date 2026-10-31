"use client";
import { useState } from "react";
import { Table } from "@/components/Table";
import { useCcy } from "@/components/Ccy";
import { D, ccyUnit, conv } from "@/lib/data";

const NAMES: Record<string, string> = { BS_TOT: "Bilanço – Toplam", BS_TP: "Bilanço – TP", BS_YP: "Bilanço – YP", OBS_TOT: "Nazım – Toplam", OBS_TP: "Nazım – TP", OBS_YP: "Nazım – YP", PL_YTD: "K/Z – YTD", PL_Q: "K/Z – Çeyrek", OCI_YTD: "Kapsamlı gelir – YTD", CF_YTD: "Nakit akış – YTD", CF_Q: "Nakit akış – Çeyrek", EQ: "Özkaynak değişim" };

export default function Tablolar() {
  const { ccy } = useCcy(); const u = ccyUnit(ccy);
  const [sh, setSh] = useState("BS_TOT");
  const s = D.statements[sh];
  const isFlow = sh.endsWith("_Q") || sh.endsWith("YTD") || sh === "EQ";
  const kind = sh.endsWith("_Q") ? "q" : "stock";
  const canFx = !(sh.endsWith("YTD") || sh === "EQ") || ccy === "TL";
  return (
    <>
      <h1>Finansal tablolar (KAP ana tabloları, tam ayrıntı)</h1>
      <div className="controls">
        <label>Tablo<select value={sh} onChange={e => setSh(e.target.value)}>{Object.keys(D.statements).map(k => <option key={k} value={k}>{NAMES[k] ?? k}</option>)}</select></label>
        <span className="note">{s.note}</span>
      </div>
      {!canFx && <div className="note" style={{ color: "var(--warn)" }}>YTD/kümülatif tablolar yalnızca TL gösterilir (kümülatif akım için tek bir kur yok); USD/EUR için çeyreklik tabloları veya Gelir Tablosu sekmesini kullanın.</div>}
      <Table unit={canFx ? u : "mn TL"} periods={s.periods} rows={s.rows.map(r => ({
        label: sh === "EQ" ? `${r.label} · ${r.component}` : r.label, level: Math.min((r.level ?? 0) + 1, 4), tip: r.key,
        digits: r.label === "Hisse Başına Kar" ? 4 : 0,
        values: s.periods.map(p => canFx ? conv(r.values[p], p, ccy, kind as any) : r.values[p] ?? null),
      }))} />
      <div className="note">Satır hiyerarşisi PDF girintisinden; değerler bildirildiği gibi (giderler negatif). Birim mn TL (1.000 TL bildirimleri /1000). 31.03.2021 ve 30.06.2021 bilançosu yok.</div>
    </>
  );
}
