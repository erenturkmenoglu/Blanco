"use client";
import { useEffect, useMemo, useState } from "react";
import { api, Bank, DerivedMetric, Obs, SECTIONS, fmt } from "@/lib/api";
import Provenance from "@/components/Provenance";
import { SeriesChart } from "@/components/SeriesChart";

type Dict = { metrics: { code: string; name_tr: string; unit: string }[]; derived: { code: string; name_tr?: string; unit: string }[] };

const MATURITY_ITEM_ORDER = ["loans", "deposits_other", "deposits_total", "deposits_banks", "deposits_savings", "deposits_fx", "deposits_commercial", "deposits_official",
  "deposits_other_institutions", "deposits_precious_metal", "total_assets", "total_liabilities", "liquidity_gap", "securities_fvoci", "securities_amortized", "securities_issued",
  "money_market_funds", "funds_borrowed", "due_from_banks", "cash"];
const MATURITY_ITEM_NAMES: Record<string, string> = {
  loans: "Verilen krediler (kalan vade)", deposits_other: "Diğer mevduat — bankalar hariç (kalan vade)", deposits_total: "Toplam mevduat", deposits_banks: "Bankalar mevduatı",
  deposits_savings: "Tasarruf mevduatı", deposits_fx: "Döviz tevdiat hesabı", deposits_fx_resident: "DTH — yurtiçi yerleşik", deposits_fx_nonresident: "DTH — yurtdışı yerleşik",
  deposits_commercial: "Ticari kuruluşlar mevduatı", deposits_official: "Resmi kuruluşlar mevduatı", deposits_other_institutions: "Diğer kuruluşlar mevduatı",
  deposits_precious_metal: "Kıymetli maden depo hesabı", deposits_banks_cbrt: "Bankalar mevduatı — TCMB", deposits_banks_domestic: "Bankalar mevduatı — yurtiçi bankalar",
  deposits_banks_foreign: "Bankalar mevduatı — yurtdışı bankalar", deposits_banks_participation: "Bankalar mevduatı — katılım bankaları", deposits_banks_other: "Bankalar mevduatı — diğer",
  total_assets: "Toplam varlıklar (kalan vade)", total_liabilities: "Toplam yükümlülükler (kalan vade)", liquidity_gap: "Likidite açığı", net_off_balance_sheet: "Net bilanço dışı pozisyon",
  non_cash_loans: "Gayrinakdi krediler", securities_fvoci: "GUD farkı DKG'ye yansıtılan FV", securities_amortized: "İtfa edilmiş maliyetle ölçülen FV", securities_issued: "İhraç edilen menkul kıymetler",
  money_market_funds: "Para piyasalarına borçlar", money_market_receivables: "Para piyasalarından alacaklar", funds_borrowed: "Diğer mali kuruluşlardan sağlanan fonlar", funds: "Fonlar",
  due_from_banks: "Bankalar", cash: "Nakit değerler ve TCMB", other_assets: "Diğer varlıklar", other_liabilities: "Diğer yükümlülükler", sundry_payables: "Muhtelif borçlar",
};
/** Kalite bayrakları: kaynaklar arası fark (DT20 ≠ bankanın kendi tablosu) veya ölçek kuşkusu — gizlenmez, işaretlenir. */
function flagMark(o?: Obs) {
  const fl = o?.flags ?? [];
  if (!fl.length) return null;
  const txt = fl.map(f => f.startsWith("source_conflict") ? `Kaynaklar arasında fark (${f.replace("source_conflict:", "").replace("->", " → ")}); gösterilen değer son işlenen (birincil) kaynaktandır, önceki değer revizyon geçmişinde`
    : f.startsWith("DQ01") ? "Ölçek (Bin/Milyon TL) kuşkusu — DQ01" : f).join(" · ");
  return <span title={txt} style={{ cursor: "help", marginLeft: 4 }}>⚑</span>;
}
const MATURITY_BUCKET_ORDER = ["demand", "notice_7d", "demand_7d", "0_1m", "1_3m", "3_6m", "6_12m", "3_12m", "over_3m", "6_12m_plus", "over_1y", "1_5y", "over_5y", "accumulating", "unallocated", "total"];

export default function Bankalar() {
  const [banks, setBanks] = useState<Bank[]>([]);
  const [dict, setDict] = useState<Dict | null>(null);
  const [bank, setBank] = useState("");
  const [scope, setScope] = useState("solo");
  const [currency, setCurrency] = useState("ALL");
  const [periods, setPeriods] = useState<string[]>([]);
  const [period, setPeriod] = useState("");
  const [series, setSeries] = useState<Record<string, Obs[]>>({});
  const [derived, setDerived] = useState<DerivedMetric[]>([]);
  const [rates, setRates] = useState<any>(null);
  const [maturity, setMaturity] = useState<any>(null);
  const [matItems, setMatItems] = useState<Record<string, { basis: string; basis_label: string; observations: number }[]>>({});
  const [matItem, setMatItem] = useState("loans");
  const [matBasis, setMatBasis] = useState<string>("");

  useEffect(() => { api<Bank[]>("/api/banks").then(b => { setBanks(b); setBank(b.find(x => x.observations > 0)?.code ?? b[0]?.code ?? ""); }); api<Dict>("/api/dictionary").then(setDict); }, []);
  useEffect(() => { api<any[]>("/api/periods").then(p => { const ps = Array.from(new Set(p.filter(x => x.scope === scope).map(x => x.period_end as string))); setPeriods(ps); setPeriod(ps[0] ?? ""); }); }, [scope]);

  useEffect(() => {
    if (!bank) return;
    const codes = Array.from(new Set(SECTIONS.flatMap(s => s.metrics)));
    Promise.all(codes.map(c => api<any>("/api/observations", { bank, metric: c, scope }).then(r => [c, r.series] as const).catch(() => [c, []] as const)))
      .then(rs => setSeries(Object.fromEntries(rs)));
    api<any>("/api/rates", { bank, scope }).then(setRates).catch(() => setRates(null));
  }, [bank, scope]);
  useEffect(() => {
    if (!bank || !period) { setDerived([]); setMatItems({}); return; }
    api<any>("/api/derived", { bank, period_end: period, scope }).then(r => setDerived(r.metrics)).catch(() => setDerived([]));
    api<any>("/api/maturity/items", { bank, period_end: period, scope }).then(r => {
      setMatItems(r.items ?? {});
      const keys = Object.keys(r.items ?? {});
      if (keys.length && !keys.includes(matItem)) setMatItem(MATURITY_ITEM_ORDER.find(k => keys.includes(k)) ?? keys[0]);
    }).catch(() => setMatItems({}));
  }, [bank, period, scope]);
  useEffect(() => {
    if (!bank || !period || !matItem) { setMaturity(null); return; }
    api<any>("/api/maturity", { bank, period_end: period, item: matItem, scope, basis: matBasis || undefined }).then(setMaturity).catch(() => setMaturity(null));
  }, [bank, period, scope, matItem, matBasis]);

  const names = useMemo(() => { const m: Record<string, string> = {}; dict?.metrics.forEach(x => m[x.code] = x.name_tr); dict?.derived.forEach(x => m[x.code] = x.name_tr ?? x.code); return m; }, [dict]);
  const units = useMemo(() => { const m: Record<string, string> = {}; dict?.metrics.forEach(x => m[x.code] = x.unit); dict?.derived.forEach(x => m[x.code] = x.unit); return m; }, [dict]);
  // Para birimi filtresi: 'Tümü' = kaynağın Toplam sütunu (currency ALL); TL/YP = TP/YP sütunları. Karıştırılmaz, toplanmaz.
  const pick = (code: string) => {
    const rows = (series[code] ?? []).filter(o => (o.currency ?? "ALL") === currency);
    const byPe = new Map<string, Obs>();           // akış kalemlerinde aynı dönem için YTD (en erken period_start) tercih edilir; çeyrek satırı ayrıca gösterilmez
    for (const o of rows) { const cur = byPe.get(o.period_end); if (!cur || (o.period_start ?? "") < (cur.period_start ?? "")) byPe.set(o.period_end, o); }
    return Array.from(byPe.values()).sort((a, b) => a.period_end.localeCompare(b.period_end));
  };
  const visible = (code: string) => pick(code).length > 0;
  const chartData = (codes: string[]) => {
    const xs = Array.from(new Set(codes.flatMap(c => pick(c).map(o => o.period_end)))).sort();
    return xs.map(x => ({ x, ...Object.fromEntries(codes.map(c => [c, pick(c).find(o => o.period_end === x)?.value ?? null])) }));
  };
  const dmap = Object.fromEntries(derived.map(d => [d.metric, d]));
  const latest = (code: string) => pick(code).find(o => o.period_end === period);   // en güncel revizyon API'de zaten önde
  const matKeys = MATURITY_ITEM_ORDER.filter(k => matItems[k]).concat(Object.keys(matItems).filter(k => !MATURITY_ITEM_ORDER.includes(k)).sort());

  return (
    <>
      <h1>Bankalar</h1>
      <div className="controls">
        <label>Banka<select value={bank} onChange={e => setBank(e.target.value)}>{banks.map(b => <option key={b.code} value={b.code}>{b.name}{b.observations ? "" : " (veri yok)"}</option>)}</select></label>
        <label>Dönem<select value={period} onChange={e => setPeriod(e.target.value)}>{periods.map(p => <option key={p}>{p}</option>)}</select></label>
        <label>Kapsam<select value={scope} onChange={e => setScope(e.target.value)}><option value="solo">Solo</option><option value="consolidated">Konsolide</option></select></label>
        <label>Para birimi<select value={currency} onChange={e => setCurrency(e.target.value)}><option value="ALL">Tümü</option><option value="TRY">TL</option><option value="FX">YP</option></select></label>
      </div>
      {!periods.length && <p className="note">Bu kapsam için henüz doğrulanmış gözlem yok. Veri toplama motoru çalıştığında dönemler burada listelenir; eksik veri 0 olarak gösterilmez.</p>}

      {SECTIONS.map(sec => {
        const codes = sec.metrics.filter(visible).filter(c => (series[c] ?? []).length);
        const ders = (sec.derived ?? []).map(c => dmap[c]).filter(Boolean);
        if (!codes.length && !ders.length) return null;
        const any = codes.map(latest).find(Boolean);
        return (
          <section key={sec.title} className="card" style={{ marginBottom: 12 }}>
            <h2 style={{ marginTop: 0 }}>{sec.title}</h2>
            {codes.length > 0 && (
              <>
                <table><thead><tr><th>Gösterge</th><th className="num">{period}</th><th>Durum</th></tr></thead>
                  <tbody>{codes.map(c => { const o = latest(c); return <tr key={c}><td>{names[c] ?? c}</td><td className="num">{fmt(o?.value, units[c])}{flagMark(o)}</td><td><span className={`status ${o?.status ?? "UNAVAILABLE"}`}>{o?.status ?? "UNAVAILABLE"}</span>{o && o.revision > 1 && <span className="note"> rev {o.revision}</span>}</td></tr>; })}</tbody></table>
                <SeriesChart data={chartData(codes.slice(0, 4))} series={codes.slice(0, 4).map(c => ({ key: c, name: names[c] ?? c }))} unit={units[codes[0]]} />
                <Provenance period={period} unit={units[codes[0]] === "TRY" ? "TL (kaynak ölçeği normalize)" : units[codes[0]]} source={any?.source} sourceUrl={any?.source_url} updated={any?.retrieved_at} status={any?.status} />
              </>
            )}
            {ders.length > 0 && (
              <>
                <h3>Hesaplanan göstergeler</h3>
                <table><thead><tr><th>Gösterge</th><th className="num">Değer</th><th>Yöntem</th></tr></thead>
                  <tbody>{ders.map(d => <tr key={d.metric}><td>{names[d.metric] ?? d.metric}</td><td className="num">{fmt(d.value, d.unit)}</td><td className="note">{d.method}{d.limitations && <div>Sınırlama: {d.limitations}</div>}</td></tr>)}</tbody></table>
                <Provenance period={period} status="DERIVED" method="Formüller veri sözlüğünde; kümülatif gelir tablosu YTD×4/q ile yıllıklandırılır." />
              </>
            )}
          </section>
        );
      })}

      <section className="card" style={{ marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>9. Kredi ve Mevduat Vadeleri</h2>
        <div className="controls">
          <label>Kalem<select value={matItem} onChange={e => { setMatItem(e.target.value); setMatBasis(""); }}>
            {matKeys.map(k => <option key={k} value={k}>{MATURITY_ITEM_NAMES[k] ?? k}</option>)}</select></label>
          <label>Vade temeli<select value={matBasis || (maturity?.basis ?? "")} onChange={e => setMatBasis(e.target.value)}>
            {(matItems[matItem] ?? []).map(b => <option key={b.basis} value={b.basis}>{b.basis_label}</option>)}</select></label>
        </div>
        {maturity?.buckets && Object.keys(maturity.buckets).length ? (
          <>
            <table><thead><tr><th>Kova (kaynak etiketi)</th><th className="num">Tutar</th><th className="num">Pay</th></tr></thead>
              <tbody>{MATURITY_BUCKET_ORDER.filter(k => k in maturity.buckets).map(k => { const v = maturity.buckets[k]; return <tr key={k}><td>{maturity.bucket_labels?.[k] ?? k}</td><td className="num">{fmt(v, "TRY")}</td><td className="num">{maturity.shares?.[k] != null ? `${(maturity.shares[k] * 100).toFixed(1)}%` : "—"}</td></tr>; })}</tbody></table>
            {maturity.illustrative_midpoint_wam_months != null && <p className="note">Orta nokta ağırlıklı gösterge vade: {maturity.illustrative_midpoint_wam_months.toFixed(1)} ay (kova orta noktalarıyla; kesin ağırlıklı ortalama vade DEĞİLDİR).</p>}
            <Provenance period={period} unit="TL" source="TBB" sourceUrl={maturity.source_url} updated={maturity.retrieved_at} status={maturity.status}
              method={`${MATURITY_ITEM_NAMES[maturity.item] ?? maturity.item} · ${maturity.basis_label ?? maturity.basis}${maturity.source_sheet ? ` · sayfa: ${maturity.source_sheet}` : ""}`} limitations={maturity.limitations} />
            {Object.keys(maturity.bases ?? {}).length > 1 && <p className="note">Bu kalem için {Object.keys(maturity.bases).length} farklı kova kümesi var ({Object.values(maturity.bases).map((b: any) => b.basis_label).join(" | ")}); birleştirilmez, seçerek görüntülenir.</p>}
          </>
        ) : <p className="note">Bu kalem/dönem için vade gözlemi yok. Not: TBB 'Kalan Vade' tablosu toplam aktif/pasif verir; kredi ve mevduatın ayrı vade dağılımı yalnızca bankanın kendi dipnotundan (malibünye1 / pasif1) alınır.</p>}
      </section>

      <section className="card" style={{ marginBottom: 12 }}>
        <h2 style={{ marginTop: 0 }}>10. Faiz Analizi</h2>
        {rates?.series?.length ? (
          <>
            <table><thead><tr><th>Dönem</th><th>Para birimi</th><th>Araç</th><th className="num">Oran</th><th>Tanım</th></tr></thead>
              <tbody>{rates.series.map((s: any, i: number) => <tr key={i}><td>{s.period_end}</td><td>{s.currency}</td><td>{s.instrument === "loan" ? "Kredi" : "Mevduat"}</td><td className="num">{fmt(s.value, "pct")}</td><td className="note">{s.rate_definition}</td></tr>)}</tbody></table>
            <h3>Faiz makası (yalnızca aynı tanım/dönem/para birimi)</h3>
            <table><thead><tr><th>Dönem</th><th>Para birimi</th><th className="num">Kredi − Mevduat</th><th>Sınırlama</th></tr></thead>
              <tbody>{rates.spreads.map((s: any, i: number) => <tr key={i}><td>{s.period_end}</td><td>{s.currency}</td><td className="num">{fmt(s.spread, "pct")}</td><td className="note">{s.limitations}</td></tr>)}</tbody></table>
            <Provenance source={rates.series[0].source} sourceUrl={rates.series[0].source_url} updated={rates.series[0].retrieved_at} status={rates.series[0].status} method={rates.definition_note} />
          </>
        ) : <p className="note">Faiz gözlemi yok. Kaynak: TBB DT20/DT21 "Verilen Kredilere ve Diğer Mevduata Uygulanan Ortalama Faiz Oranları" (stok ortalama uygulanan oran).</p>}
      </section>
    </>
  );
}
