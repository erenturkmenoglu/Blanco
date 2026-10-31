"use client";
import { Chart } from "@/components/Chart";
import { Kpi } from "@/components/Kpi";
import { useCcy } from "@/components/Ccy";
import { D, LAST, PERIODS, ccyUnit, conv, dip, flow, fmt, fmtPct, item, prevQ, qlabel, ratio, series, stockPeriods } from "@/lib/data";

export default function Home() {
  const { ccy } = useCcy();
  const u = ccyUnit(ccy);
  const st = (code: string) => (p: string) => conv(item(code).values[p], p, ccy, "stock");
  const q = (code: string) => (p: string) => conv(flow(code).q[p], p, ccy, "q");
  const r = (code: string) => (p: string) => ratio(code).values[p] ?? null;
  const pq = prevQ(LAST)!; const yq = PERIODS[PERIODS.indexOf(LAST) - 4];
  const ta = item("total_assets").values, ni = flow("net_profit").q, nii = flow("net_interest_income").q;
  const syr = dip("capital_adequacy_ratio")?.values[LAST], lko = dip("liquidity_coverage_ratio")?.values[LAST], nsfr = dip("nsfr")?.values[LAST];
  const dlt = (a: number | null | undefined, b: number | null | undefined) => a && b ? `${b < 0 ? "" : ""}${fmtPct(a / b - 1, 1)}` : "—";
  return (
    <>
      <h1>Genel bakış — {qlabel(LAST)} ({LAST})</h1>
      <div className="kpis">
        <Kpi label={`Toplam aktif (${u})`} value={fmt(conv(ta[LAST], LAST, ccy))} delta={`ÇoÇ ${dlt(ta[LAST], ta[pq])} · YoY ${dlt(ta[LAST], ta[yq])} (TL)`} />
        <Kpi label={`Net kâr, çeyrek (${u})`} value={fmt(conv(ni[LAST], LAST, ccy, "q"))} delta={`YoY ${dlt(ni[LAST], ni[yq])} (TL)`} />
        <Kpi label={`NII, çeyrek (${u})`} value={fmt(conv(nii[LAST], LAST, ccy, "q"))} delta={`YoY ${dlt(nii[LAST], nii[yq])} (TL)`} />
        <Kpi label="Ticari K/Z, çeyrek" value={fmt(conv(flow("trading_income").q[LAST], LAST, ccy, "q"))} delta={`kambiyo ${fmt(conv(flow("trading_fx").q[LAST], LAST, ccy, "q"))} · türev ${fmt(conv(flow("trading_derivatives").q[LAST], LAST, ccy, "q"))}`} />
        <Kpi label="ROE (TTM / 5Ç ort.)" value={fmtPct(ratio("roe_ttm").values[LAST])} delta={`Blanco yöntemi ${fmtPct(ratio("roe").values[LAST])}`} />
        <Kpi label="NIM (faiz getirili aktif, TTM)" value={fmtPct(ratio("nim_iea_ttm").values[LAST])} delta={`çeyrek×4 / aktif ${fmtPct(ratio("nim_q_ann").values[LAST])}`} />
        <Kpi label="Gider/Gelir (YTD)" value={fmtPct(ratio("cost_to_income").values[LAST])} />
        <Kpi label="Kredi/Mevduat" value={fmtPct(ratio("loan_to_deposit_ratio").values[LAST], 0)} delta={`Kredi/Aktif ${fmtPct(ratio("loans_to_assets").values[LAST], 0)}`} />
        <Kpi label="Türev nominal / Aktif" value={`${fmt(ratio("derivatives_to_assets").values[LAST], 2)}x`} delta={`${fmt(conv(item("derivatives_notional").values[LAST], LAST, ccy))} ${u}`} />
        <Kpi label="SYR / Tier-1" value={syr ? `${fmt(syr, 1)}%` : "—"} delta={`Tier-1 ${fmt(dip("tier_1_ratio")?.values[LAST], 1)}% · RWA ${fmt(conv(dip("risk_weighted_assets")?.values[LAST], LAST, ccy))} ${u}`} note="TBB dipnot, 30.06.2026" />
        <Kpi label="LKO / NSFR" value={lko ? `${fmt(lko, 0)}%` : "—"} delta={`NSFR ${fmt(nsfr, 0)}% · YP LKO ${fmt(dip("liquidity_coverage_ratio_fx")?.values[LAST], 0)}%`} note="TBB dipnot" />
        <Kpi label="Özkaynak / Aktif" value={fmtPct(ratio("equity_to_assets").values[LAST])} delta={`Özkaynak ${fmt(conv(item("total_equity").values[LAST], LAST, ccy))} ${u}`} />
      </div>

      <div className="grid2">
        <Chart title="Toplam aktifler ve özkaynak" unit={u} data={series([{ key: "a", get: st("total_assets") }, { key: "e", get: st("total_equity") }], stockPeriods)} series={[{ key: "a", name: "Toplam aktifler" }, { key: "e", name: "Özkaynaklar" }]} />
        <Chart title="Çeyreklik NII, ticari K/Z ve net kâr" unit={u} kind="bar" data={series([{ key: "nii", get: q("net_interest_income") }, { key: "tr", get: q("trading_income") }, { key: "np", get: q("net_profit") }])} series={[{ key: "nii", name: "Net faiz geliri" }, { key: "tr", name: "Ticari K/Z" }, { key: "np", name: "Net kâr" }]} note="Akımlar çeyrek ortalama kurla çevrilir (önceki dönem sonu + dönem sonu)/2." />
        <Chart title="NII + Ticari K/Z (carry'nin iki bacağı) vs net kâr, çeyrek" unit={u} data={series([{ key: "s", get: (p) => conv(ratio("nii_plus_trading_q").values[p], p, ccy, "q") }, { key: "np", get: q("net_profit") }])} series={[{ key: "s", name: "NII + Ticari K/Z" }, { key: "np", name: "Net kâr" }]} />
        <Chart title="Türev nominal (nazım) ve bilanço içi YP açığı" unit={u} data={series([{ key: "d", get: st("derivatives_notional") }, { key: "g", get: (p) => conv(ratio("on_bs_fx_gap").values[p], p, ccy) }], stockPeriods)} series={[{ key: "d", name: "Türev nominal" }, { key: "g", name: "YP aktif − YP pasif (bilanço içi)" }]} />
        <Chart title="ROE ve ROA" pct data={series([{ key: "roe", get: r("roe_ttm") }, { key: "roeB", get: r("roe") }, { key: "roa", get: r("roa_ttm") }], stockPeriods)} series={[{ key: "roe", name: "ROE TTM / 5Ç ort." }, { key: "roeB", name: "ROE Blanco (YTD×4/q, 2 nokta)" }, { key: "roa", name: "ROA TTM" }]} />
        <Chart title="Net faiz marjı ve gider/gelir" pct digits={1} data={series([{ key: "nim", get: r("nim_iea_ttm") }, { key: "nimq", get: r("nim_q_ann") }, { key: "cir", get: r("cost_to_income_q") }], stockPeriods)} series={[{ key: "nim", name: "NIM faiz getirili aktif TTM" }, { key: "nimq", name: "NIM çeyrek×4 / dönem sonu aktif" }, { key: "cir", name: "Gider/Gelir çeyrek" }]} />
      </div>
      <section>
        <h2>Okuma notları</h2>
        <ul className="note">
          <li>Mevduat bankasından çok swap-fonlu bir TL piyasa defteri: Kredi/Mevduat 2023'te ~3x iken {fmtPct(ratio("loan_to_deposit_ratio").values[LAST], 0)}; aktifin büyük kısmı nakit+TCMB+bankalar; NII'nin ana kaynağı para piyasası ve plasman faizi.</li>
          <li>Türev defteri {fmt(ratio("derivatives_to_assets").values[LAST], 1)}x aktif; bilanço içi YP açığı nazım swap alım TP / satım YP ile kapatılıyor. Karlılık okuması için NII ve ticari K/Z birlikte bakılmalı (NII+ticari serisi).</li>
          <li>Tüm tutarlar nominal; TMS 29 enflasyon muhasebesi hiçbir dönemde uygulanmamış. USD/EUR görünümü dönem sonu (stok) ve çeyrek ortalama (akım) TCMB alış kurlarıyla.</li>
          <li>Veri boşlukları: 31.03.2021 ve 30.06.2021 bilançosu yok; dipnot kalemleri (SYR, LKO, vade, faiz) yalnızca 2025Ç4–2026Ç2.</li>
        </ul>
      </section>
    </>
  );
}
