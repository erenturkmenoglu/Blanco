"use client";
import { Chart } from "@/components/Chart";
import { Table } from "@/components/Table";
import { useCcy } from "@/components/Ccy";
import { D, ccyUnit, conv, fmt, qlabel } from "@/lib/data";

export default function Dipnot() {
  const { ccy } = useCcy(); const u = ccyUnit(ccy);
  const sc = D.dipnot.scalars;
  const periods = Array.from(new Set(sc.flatMap(s => Object.keys(s.values)))).sort().filter(p => sc.filter(s => s.values[p] !== undefined).length > 2);
  const get = (code: string) => sc.find(s => s.code === code);
  const grp = (codes: string[]) => sc.filter(s => codes.includes(s.code));
  const rateRows = (codes: string[]) => grp(codes).map(s => ({ label: s.name, tip: `${s.code} · ${s.source}`, values: periods.map(p => s.values[p] ?? null), digits: 2 }));
  const mnRows = (codes: string[]) => grp(codes).map(s => ({ label: `${s.name}`, tip: `${s.code} · ${s.source}`, values: periods.map(p => s.unit === "mn TL" ? conv(s.values[p], p, ccy) : s.values[p] ?? null) }));
  const bucketChart = (group: string, rowCode: string, title: string) => {
    const t = D.dipnot.tables.find(x => x.group === group)!; const row = t.rows.find(r => r.code === rowCode); if (!row) return null;
    const ps = Object.keys(row.periods).sort();
    const data = t.buckets.filter(b => b !== "total").map((b, i) => { const o: any = { x: t.bucket_labels[i] }; for (const p of ps) o[p] = conv(row.periods[p][b], p, ccy); return o; });
    return <Chart key={rowCode} title={title} unit={u} kind="bar" data={data} series={ps.map(p => ({ key: p, name: qlabel(p) }))} />;
  };
  const tableFor = (group: string) => {
    const t = D.dipnot.tables.find(x => x.group === group)!;
    return t.rows.flatMap(r => Object.keys(r.periods).sort().map(p => ({ label: `${r.name} · ${qlabel(p)}`, values: t.buckets.map(b => conv(r.periods[p][b], p, ccy)) })));
  };
  const bucketsTable = (group: string) => {
    const t = D.dipnot.tables.find(x => x.group === group)!;
    const rows = tableFor(group);
    return (
      <div className="tbl-wrap"><table><thead><tr><th>{u}</th>{t.bucket_labels.map(b => <th key={b} className="num">{b}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}><td>{r.label}</td>{r.values.map((v, j) => <td key={j} className={`num${(v ?? 0) < 0 ? " neg" : ""}`}>{fmt(v)}</td>)}</tr>)}</tbody></table></div>
    );
  };
  return (
    <>
      <h1>Dipnotlar (TBB banka kitabı, 31.03.2026 ve 30.06.2026 · önceki dönem 31.12.2025)</h1>
      <div className="note" style={{ marginBottom: 10 }}>Kaynak: TBB Ortak Veri Gönderim Seti — Deutsche Bank A.Ş. solo kitapları (Mart 2026 Bin TL, Haziran 2026 Milyon TL). KAP bildirimlerinde bulunmayan kalemler buradan; yalnızca bu üç dönem için mevcut. Şube/çalışan: TBB DT13 Haziran 2026.</div>

      <section><h2>Sermaye yeterliliği</h2>
        <Table periods={periods} rows={[...rateRows(["capital_adequacy_ratio", "tier_1_ratio", "cet1_ratio"]), ...mnRows(["regulatory_equity", "cet1_capital", "risk_weighted_assets"])]} unit={`% / ${u}`} />
        <div className="note">SYR yalnızca cari dönem için raporlanır; 31.12.2025 kolonu boş. Tamponlar dahil asgari: SYR %12.5 (8 + 2.5 koruma + ~0 döngüsel + D-SIB yok) → 30.06.2026 SYR %{fmt(get("capital_adequacy_ratio")?.values["2026-06-30"], 1)}.</div>
      </section>
      <section><h2>Likidite: LKO ve NSFR</h2>
        <Table periods={periods} rows={[...rateRows(["liquidity_coverage_ratio", "liquidity_coverage_ratio_fx", "nsfr"]), ...mnRows(["hqla_stock", "net_cash_outflows"])]} unit={`% / ${u}`} />
      </section>
      <section><h2>Parasal finansal araçlara uygulanan ortalama faiz oranları (stok, %)</h2>
        <Table periods={periods} rows={rateRows(["loan_interest_tl", "loan_interest_usd", "loan_interest_eur", "deposit_interest_tl", "deposit_interest_usd", "deposit_interest_eur", "bank_deposit_interest_tl", "bank_deposit_interest_eur", "funds_borrowed_interest_tl", "funds_borrowed_interest_eur", "due_from_banks_interest_tl", "due_from_banks_interest_usd", "securities_fvtpl_interest_tl", "securities_fvoci_interest_tl", "cash_cb_interest_tl", "cash_cb_interest_eur"])} unit="%" />
        <div className="note">Faiz oranı riski dipnotu: stok ortalama uygulanan oranlar; yeni açılış faizleri veya muhasebesel getiri değildir. TL kredi−mevduat makası 30.06.2026: {fmt((get("loan_interest_tl")?.values["2026-06-30"] ?? 0) - (get("deposit_interest_tl")?.values["2026-06-30"] ?? 0), 2)} puan.</div>
      </section>
      <section><h2>Kalan vade (likidite riski)</h2>
        <div className="grid2">{bucketChart("rm", "rm_total_assets", "Toplam varlıklar – kalan vade")}{bucketChart("rm", "rm_total_liabilities", "Toplam yükümlülükler – kalan vade")}{bucketChart("rm", "rm_liquidity_gap", "Likidite açığı")}{bucketChart("rm", "rm_loans", "Verilen krediler – kalan vade")}{bucketChart("rm", "rm_funds_borrowed", "Alınan krediler – kalan vade")}{bucketChart("rm", "rm_other_deposits", "Diğer mevduat – kalan vade")}</div>
        {bucketsTable("rm")}
      </section>
      <section><h2>Mevduat vade yapısı</h2>
        <div className="grid2">{bucketChart("dep", "dep_maturity_total", "Toplam mevduat – vade yapısı")}{bucketChart("dep", "dep_maturity_fx", "Döviz tevdiat – vade yapısı")}</div>
        {bucketsTable("dep")}
        <Table periods={periods} rows={mnRows(["demand_deposits", "time_deposits"])} unit={u} />
      </section>
      <section><h2>Yeniden fiyatlama (faize duyarlılık)</h2>
        <div className="grid2">{bucketChart("rp", "rp_total_assets", "Faize duyarlı varlıklar")}{bucketChart("rp", "rp_total_liabilities", "Faize duyarlı yükümlülükler")}{bucketChart("rp", "rp_total_position", "Toplam pozisyon (bilanço içi + nazım)")}</div>
        {bucketsTable("rp")}
      </section>
      <section><h2>Kredi kalitesi ve operasyon</h2>
        <Table periods={periods} rows={[...mnRows(["npl_amount", "loan_loss_provisions"]), ...grp(["branch_count", "employee_count"]).map(s => ({ label: s.name, values: periods.map(p => s.values[p] ?? null) }))]} unit={u} />
        <div className="note">Donuk alacak 0 (III-V. grup hareket tablosu dönem sonu bakiyesi). Çalışan sayısı TBB DT13 (Haziran 2025: 116, Aralık 2025: 118, Haziran 2026: 121); 1 şube.</div>
      </section>
    </>
  );
}
