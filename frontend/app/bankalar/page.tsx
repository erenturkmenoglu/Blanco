"use client";
import { useEffect, useMemo, useState } from "react";
import { api, Bank, DerivedMetric, Obs, SECTIONS, fmt } from "@/lib/api";
import Provenance from "@/components/Provenance";
import { SeriesChart } from "@/components/SeriesChart";

type Dict = { metrics: { code: string; name_tr: string; unit: string }[]; derived: { code: string; name_tr?: string; unit: string }[] };

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
    if (!bank || !period) { setDerived([]); setMaturity(null); return; }
    api<any>("/api/derived", { bank, period_end: period, scope }).then(r => setDerived(r.metrics)).catch(() => setDerived([]));
    api<any>("/api/maturity", { bank, period_end: period, item: "total_assets", scope }).then(setMaturity).catch(() => setMaturity(null));
  }, [bank, period, scope]);

  const names = useMemo(() => { const m: Record<string, string> = {}; dict?.metrics.forEach(x => m[x.code] = x.name_tr); dict?.derived.forEach(x => m[x.code] = x.name_tr ?? x.code); return m; }, [dict]);
  const units = useMemo(() => { const m: Record<string, string> = {}; dict?.metrics.forEach(x => m[x.code] = x.unit); dict?.derived.forEach(x => m[x.code] = x.unit); return m; }, [dict]);
  const visible = (code: string) => currency === "ALL" || !(series[code]?.[0]?.currency) || series[code][0].currency === currency || series[code][0].currency === "ALL";
  const chartData = (codes: string[]) => {
    const xs = Array.from(new Set(codes.flatMap(c => (series[c] ?? []).map(o => o.period_end)))).sort();
    return xs.map(x => ({ x, ...Object.fromEntries(codes.map(c => [c, series[c]?.find(o => o.period_end === x)?.value ?? null])) }));
  };
  const dmap = Object.fromEntries(derived.map(d => [d.metric, d]));
  const latest = (code: string) => series[code]?.filter(o => o.period_end === period)[0];

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
                  <tbody>{codes.map(c => { const o = latest(c); return <tr key={c}><td>{names[c] ?? c}</td><td className="num">{fmt(o?.value, units[c])}</td><td><span className={`status ${o?.status ?? "UNAVAILABLE"}`}>{o?.status ?? "UNAVAILABLE"}</span></td></tr>; })}</tbody></table>
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
        {maturity?.buckets && Object.keys(maturity.buckets).length ? (
          <>
            <table><thead><tr><th>Kova (kaynak etiketi)</th><th className="num">Tutar</th><th className="num">Pay</th></tr></thead>
              <tbody>{Object.entries(maturity.buckets).map(([k, v]: any) => <tr key={k}><td>{maturity.bucket_labels?.[k] ?? k}</td><td className="num">{fmt(v, "TRY")}</td><td className="num">{maturity.shares?.[k] != null ? `${(maturity.shares[k] * 100).toFixed(1)}%` : "—"}</td></tr>)}</tbody></table>
            <Provenance period={period} unit="TL" method={`${maturity.item} / ${maturity.basis} vade`} limitations={maturity.limitations ?? maturity.note} />
          </>
        ) : <p className="note">Bu dönem için vade gözlemi yok. Not: TBB 'Kalan Vade' tablosu toplam aktif/pasif verir; kredi ve mevduatın ayrı vade dağılımı kaynakta doğrulanmadıkça gösterilmez.</p>}
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
