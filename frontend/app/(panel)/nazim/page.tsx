"use client";
import { Chart } from "@/components/Chart";
import { Table } from "@/components/Table";
import { useCcy } from "@/components/Ccy";
import { D, ccyUnit, conv, item, ratio, series, stockPeriods } from "@/lib/data";

export default function Nazim() {
  const { ccy } = useCcy(); const u = ccyUnit(ccy);
  const st = (code: string) => (p: string) => conv(item(code).values[p], p, ccy);
  const S = (codes: [string, string][]) => series(codes.map(([c]) => ({ key: c, get: st(c) })), stockPeriods);
  const N = (codes: [string, string][]) => codes.map(([c, n]) => ({ key: c, name: n }));
  const der: [string, string][] = [["fx_forwards_notional", "Vadeli döviz"], ["swaps_notional", "Para + faiz swap"], ["futures_notional", "Futures"]];
  const obs = D.items.filter(i => i.section === "off_balance_sheet");
  return (
    <>
      <h1>Nazım hesaplar ve türev defteri</h1>
      <div className="grid2">
        <Chart title="Türev nominal (alım-satım amaçlı)" unit={u} kind="bar" stacked data={S(der)} series={N(der)} />
        <Chart title="Türev nominal / toplam aktif" data={series([{ key: "x", get: (p) => ratio("derivatives_to_assets").values[p] ?? null }], stockPeriods)} series={[{ key: "x", name: "x aktif" }]} digits={2} />
        <Chart title="Swap bacakları ve YP borçlanma" unit={u} data={S([["ccy_swap_buy_tl", ""], ["ccy_swap_sell_fx", ""], ["funds_borrowed_fx", ""]])} series={N([["ccy_swap_buy_tl", "Swap para alım – TP bacak"], ["ccy_swap_sell_fx", "Swap para satım – YP bacak"], ["funds_borrowed_fx", "Alınan krediler – YP"]])} note="Swap para alım TP / satım YP = TL fonlama swap'ı (YP ver, TL al). Bilanço içi YP açığı ile birlikte okunmalı." />
        <Chart title="Vadeli döviz alım / satım ve IRS" unit={u} data={S([["fx_forward_buy", ""], ["fx_forward_sell", ""], ["irs_notional", ""]])} series={N([["fx_forward_buy", "Vadeli döviz alım"], ["fx_forward_sell", "Vadeli döviz satım"], ["irs_notional", "Faiz swap (IRS)"]])} />
        <Chart title="Garanti, taahhüt, müşteri portföyü" unit={u} data={S([["guarantees", ""], ["commitments", ""], ["client_funds_portfolio", ""]])} series={N([["guarantees", "Garanti ve kefaletler"], ["commitments", "Taahhütler"], ["client_funds_portfolio", "Müşteri fon ve portföy mevcutları"]])} />
        <Chart title="Bilanço içi YP pozisyonu (YP aktif − YP pasif)" unit={u} kind="bar" data={series([{ key: "g", get: (p) => conv(ratio("on_bs_fx_gap").values[p], p, ccy) }], stockPeriods)} series={[{ key: "g", name: "Bilanço içi YP açığı" }]} note="Negatif = YP pasif fazlası; nazımdaki swap alım TP/satım YP pozisyonuyla kapatılır (dipnot: Madde 11 kur riski toplam pozisyon)." />
      </div>
      <section>
        <h2>Nazım kalemleri · {u}</h2>
        <Table unit={u} periods={stockPeriods} rows={obs.map(i => ({ label: i.name, status: i.status, tip: `${i.code} · ${i.source}`, values: stockPeriods.map(p => conv(i.values[p], p, ccy)) }))} />
      </section>
    </>
  );
}
