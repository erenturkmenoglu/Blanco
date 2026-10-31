"use client";
import "./report.css";
import { useCcy } from "@/components/Ccy";
import { Spine, type Chapter } from "@/components/report/Spine";
import { Anatomy, C, Dumbbell, Ladder, Legend, Mini, TimeChart, Waterfall, big, fmtAxis, fmtNum, fmtPct, fmtPctAxis, type Pt, type S } from "@/components/report/svg";
import { D, LAST, PERIODS, conv, convYtd, dip, flow, item, qlabel, ratio, series, stockPeriods, type Ccy } from "@/lib/data";

const CH: Chapter[] = [
  { id: "ozet", n: "1", title: "Özet" }, { id: "bilanco", n: "2", title: "Bilanço" }, { id: "fonlama", n: "3", title: "Fonlama ve swap" },
  { id: "karlilik", n: "4", title: "Kârlılık" }, { id: "verimlilik", n: "5", title: "Verimlilik ve risk" }, { id: "sermaye", n: "6", title: "Sermaye ve likidite" },
  { id: "kur", n: "7", title: "Kur merceği" }, { id: "veri", n: "8", title: "Veri notu" },
];
const N = ({ v, d, pct, neg }: { v: number | null | undefined; d?: number; pct?: boolean; neg?: boolean }) => <span className={`rp-n${(neg ?? (typeof v === "number" && v < 0)) ? " rp-neg" : ""}`}>{pct ? fmtPct(v, d ?? 1) : fmtNum(v, d ?? 0)}</span>;
const B = ({ v, u }: { v: number | null | undefined; u: string }) => <span className={`rp-n${typeof v === "number" && v < 0 ? " rp-neg" : ""}`}>{big(v, u)}</span>;
const yago = (p: string) => PERIODS[PERIODS.indexOf(p) - 4];
const Fig = ({ title, sub, note, children, bleed, id }: { title: string; sub?: string; note?: React.ReactNode; children: React.ReactNode; bleed?: boolean; id?: string }) => (
  <figure id={id} className={`rp-fig${bleed ? " bleed" : ""}`}><figcaption><p className="rp-figtitle">{title}</p>{sub && <p className="rp-figsub">{sub}</p>}</figcaption>{children}{note && <p className="rp-fignote">{note}</p>}</figure>
);

export default function Report() {
  const { ccy } = useCcy();
  const u = ccy === "TL" ? "TL" : ccy; const U = `mn ${u}`;
  const st = (code: string) => (p: string) => conv(item(code).values[p], p, ccy);
  const q = (code: string) => (p: string) => conv(flow(code).q[p], p, ccy, "q");
  const r = (code: string) => (p: string) => ratio(code).values[p] ?? null;
  const ser = (spec: { key: string; get: (p: string) => number | null }[], ps: string[] = PERIODS) => series(spec, ps) as Pt[];
  const S1 = (code: string, get = st) => ser([{ key: "v", get: get(code) }], stockPeriods);
  const F1 = (code: string) => ser([{ key: "v", get: q(code) }]);
  const v = (code: string, p = LAST) => item(code).values[p] ?? null;
  const fq = (code: string, p = LAST) => flow(code).q[p] ?? null;
  const rr = (code: string, p = LAST) => ratio(code).values[p] ?? null;
  const cv = (x: number | null, p = LAST, k: "stock" | "q" = "stock") => conv(x, p, ccy, k);
  const share = (code: string, p = LAST) => { const a = v("total_assets", p), b = v(code, p); return a && b !== null ? b / a : null; };
  const pq = PERIODS[PERIODS.indexOf(LAST) - 1], py = yago(LAST);
  const d = (code: string) => dip(code)?.values[LAST] ?? null;
  const BIG = (x: number | null) => big(cv(x), u);

  // ---- kilit sayılar
  const ta = v("total_assets"), liqShare = (share("cash_and_central_bank") ?? 0) + (share("due_from_banks") ?? 0) + (share("money_market_receivables") ?? 0);
  const nii = fq("net_interest_income"), trd = fq("trading_income"), np = fq("net_profit");
  const carry = (nii ?? 0) + (trd ?? 0), carryY = (fq("net_interest_income", py) ?? 0) + (fq("trading_income", py) ?? 0);
  const derivX = rr("derivatives_to_assets");
  const fxGap = rr("on_bs_fx_gap");
  const firstStock = stockPeriods[0];

  // ---- bölüm 2 verileri
  const assetParts: [string, string][] = [["cash_and_central_bank", "Nakit ve TCMB"], ["due_from_banks", "Bankalar"], ["securities_portfolio", "Menkul kıymetler"], ["loans_gross", "Krediler"], ["derivative_assets", "Türev varlıklar"], ["other_assets", "Diğer"]];
  const liabParts: [string, string][] = [["total_deposits", "Mevduat"], ["funds_borrowed", "Alınan krediler"], ["total_equity", "Özkaynaklar"], ["derivative_liabilities", "Türev yükümlülükler"], ["provisions", "Karşılıklar"], ["tax_liabilities", "Vergi borcu"], ["other_liabilities", "Diğer"]];
  const shareSeries = (code: string) => ser([{ key: "v", get: (p) => share(code, p) }], stockPeriods);
  const maxShare = Math.max(...[...assetParts, ...liabParts].flatMap(([c]) => stockPeriods.map(p => share(c, p) ?? 0)));
  const sorted = (parts: [string, string][], p: string) => parts.map(([c, n]) => ({ name: n, v: cv(v(c, p), p) ?? 0 })).sort((a, b) => b.v - a.v);
  const anatomy = [
    { label: "Varlıklar", total: cv(ta) ?? 0, parts: sorted(assetParts, LAST) },
    { label: "Yükümlülükler", total: cv(v("total_liabilities")) ?? 0, parts: sorted(liabParts, LAST) },
    { label: "Türev nominal", total: cv(v("derivatives_notional")) ?? 0, parts: [{ name: "Para ve faiz swapları", v: cv(v("swaps_notional")) ?? 0 }, { name: "Vadeli döviz", v: cv(v("fx_forwards_notional")) ?? 0 }, { name: "Futures", v: cv(v("futures_notional")) ?? 0 }] },
  ];
  const tpyp = (tl: string, fx: string, ps = stockPeriods) => ser([{ key: "tp", get: st(tl) }, { key: "yp", get: st(fx) }], ps);
  const TPYP: S[] = [{ key: "tp", name: "TL", kind: "bar", color: C.tp }, { key: "yp", name: "Yabancı para", kind: "bar", color: C.yp }];

  // ---- bölüm 4: köprü
  const bridge = (p: string) => {
    const g = (c: string) => convYtd(c, p, ccy) ?? 0;
    return [
      { label: "NII", v: g("net_interest_income"), kind: "start" as const }, { label: "Net ücret", v: g("net_fee_commission_income"), kind: "delta" as const },
      { label: "Ticari", v: g("trading_income"), kind: "delta" as const }, { label: "Diğer", v: g("other_operating_income"), kind: "delta" as const },
      { label: "Giderler", v: g("operating_expenses"), kind: "delta" as const }, { label: "Karşılık", v: g("provision_expenses"), kind: "delta" as const },
      { label: "Vergi", v: g("tax_provision"), kind: "delta" as const }, { label: "Net kâr", v: g("net_profit"), kind: "total" as const },
    ];
  };
  const carrySeries: S[] = [{ key: "nii", name: "Net faiz geliri", kind: "bar", color: C.tp }, { key: "trd", name: "Ticari K/Z", kind: "bar", color: C.yp, negColor: C.neg }, { key: "sum", name: "NII + ticari", color: C.ink, width: 2.2 }, { key: "np", name: "Net kâr", color: C.gold }];
  const carryData = ser([{ key: "nii", get: q("net_interest_income") }, { key: "trd", get: q("trading_income") }, { key: "sum", get: (p) => { const a = q("net_interest_income")(p), b = q("trading_income")(p); return a !== null && b !== null ? a + b : null; } }, { key: "np", get: q("net_profit") }]);
  const peakP = carryData.reduce((m, x) => (typeof x.trd === "number" && (m === null || (x.trd as number) > (carryData.find(y => y.p === m)!.trd as number))) ? x.p : m, null as string | null);
  const peakTrd = peakP ? (carryData.find(x => x.p === peakP)!.trd as number) : null;

  // ---- bölüm 6: dipnot tabloları
  const dipPeriods = Array.from(new Set(D.dipnot.scalars.flatMap(s => Object.keys(s.values)))).sort().filter(p => D.dipnot.scalars.filter(s => s.values[p] !== undefined).length > 2);
  const rm = D.dipnot.tables.find(t => t.group === "rm")!, dep = D.dipnot.tables.find(t => t.group === "dep")!, rp = D.dipnot.tables.find(t => t.group === "rp")!;
  const rmRow = (code: string) => rm.rows.find(x => x.code === code)?.periods[LAST];
  const ladder = rm.buckets.filter(b => b !== "total").map((b, i) => ({ label: rm.bucket_labels[i], a: cv(rmRow("rm_total_assets")?.[b] ?? null), l: cv(rmRow("rm_total_liabilities")?.[b] ?? null) }));
  const rpRow = rp.rows.find(x => x.code === "rp_total_position")?.periods[LAST];
  const repr = rp.buckets.filter(b => b !== "total").map((b, i) => ({ p: b, x: rp.bucket_labels[i], v: cv(rpRow?.[b] ?? null) })) as Pt[];
  const rateRow = (name: string, codes: string[]) => ({ name, vals: codes.map(c => dip(c)?.values[LAST] ?? null) });
  const rates = [rateRow("Verilen krediler", ["loan_interest_tl", "loan_interest_usd", "loan_interest_eur"]), rateRow("Diğer mevduat", ["deposit_interest_tl", "deposit_interest_usd", "deposit_interest_eur"]), rateRow("Bankalar mevduatı", ["bank_deposit_interest_tl", "", "bank_deposit_interest_eur"]), rateRow("Alınan krediler", ["funds_borrowed_interest_tl", "", "funds_borrowed_interest_eur"]), rateRow("Bankalar (plasman)", ["due_from_banks_interest_tl", "due_from_banks_interest_usd", ""]), rateRow("Nakit ve TCMB", ["cash_cb_interest_tl", "", "cash_cb_interest_eur"])];

  // ---- bölüm 7: kur
  const fx = D.fx.rates;
  const idx = (c: Ccy) => { const b0 = conv(v("total_assets", firstStock), firstStock, c) ?? 1; return (p: string) => { const x = conv(v("total_assets", p), p, c); return x === null ? null : x / b0 * 100; }; };
  const idxData = ser([{ key: "tl", get: idx("TL") }, { key: "usd", get: idx("USD") }, { key: "eur", get: idx("EUR") }], stockPeriods);
  const gUSD = (p: string) => { const y = yago(p); if (!y) return null; const a = conv(v("total_assets", p), p, "USD"), b = conv(v("total_assets", y), y, "USD"); return a && b ? a / b - 1 : null; };
  const growData = ser([{ key: "tl", get: r("assets_growth_yoy") }, { key: "usd", get: gUSD }], stockPeriods.filter(p => yago(p) && yago(p) >= firstStock));
  const fxData = PERIODS.map(p => ({ p, x: qlabel(p), usd: fx[p]?.usd ?? null, eur: fx[p]?.eur ?? null })) as Pt[];
  const usdFirst = fx[firstStock].usd, usdLast = fx[LAST].usd;

  // ---- bölüm 8
  const checksOk = D.checks.every(c => Object.values(c.values).every(x => x === null || x === "n/a" || Math.abs(Number(x)) < 0.5));
  const restN = D.restatements.filter(x => String(x.category).startsWith("restatement")).length;

  const axisMn = (x: number) => fmtAxis(x);
  const tipMn = (x: number) => `${fmtNum(x)} ${U}`;

  return (
    <div className="rp">
      <div className="rp-wrap">
        <Spine chapters={CH} />
        <main className="rp-main">
          <header className="rp-mast">
            <p className="rp-kicker">Deutsche Bank A.Ş.<br />Konsolide olmayan finansallar, 3Ç2020 – 2Ç2026</p>
            <h1 className="rp-title">Bilanço<br />ve gölgesi</h1>
            <p className="rp-dek">Yirmi KAP bildirimi, iki TBB kitabı, altı yıl. Ortaya çıkan portre bir mevduat bankasının değil, yabancı para ile fonlanıp swap ile TL'ye çevrilen bir piyasa defterinin.</p>
            <div className="rp-hero">
              <Fig title={`Bilanço ve bilanço dışı türev defteri, aynı ölçekte (${qlabel(LAST)}, ${U})`} sub="Her çubuk aynı uzunluk ölçeğinde; bölümler büyükten küçüğe. Çubuğa sığmayan etiketler altında.">
                <Anatomy rows={anatomy} fmt={(x) => big(x, u)} annotate={`türev nominali aktifin ${fmtNum(derivX, 1)} katı`} />
              </Fig>
              <p className="rp-fignote">30.06.2026 itibarıyla türev nominali <N v={derivX} d={1} />× aktif. Yükümlülükler toplamı KAP tanımıyla özkaynağı içerir, bu yüzden varlıklara eşittir.</p>
            </div>
          </header>

          {/* 1 */}
          <section id="ozet">
            <h2 className="rp-h"><span>1</span>Özet</h2>
            <p className="rp-lead">Deutsche Bank A.Ş. aktifinin <N v={liqShare} pct d={0} /> kadarı nakit, TCMB ve banka plasmanı; krediler yalnızca <N v={share("loans_gross")} pct d={0} />. Fonlamanın <N v={rr("funds_borrowed_to_assets")} pct d={0} /> kadarı alınan krediler, neredeyse tamamı yabancı para; mevduat <N v={rr("deposits_to_assets")} pct d={0} />. Bilanço dışında <B v={cv(v("derivatives_notional"))} u={u} /> türev nominali duruyor.</p>
            <p>Kârlılık bu yapının iki bacağından birlikte okunmalı. {qlabel(LAST)} çeyreğinde net faiz geliri <B v={cv(nii, LAST, "q")} u={u} /> ile serinin zirvesinde; aynı çeyrekte ticari sonuç <B v={cv(trd, LAST, "q")} u={u} /> zarar, bunun <B v={cv(fq("trading_fx"), LAST, "q")} u={u} /> kadarı kambiyo. İkisinin toplamı <B v={cv(carry, LAST, "q")} u={u} />; bir yıl önce <B v={cv(carryY, py, "q")} u={u} /> idi. Swap-fonlu carry'nin toplam getirisi bir yıldır yatay, yalnızca muhasebe hattı değişti. Net kâr çeyrekte <B v={cv(np, LAST, "q")} u={u} />, yıllık <N v={rr("profit_growth_q_yoy")} pct d={1} />.</p>
            <p>Özkaynak kârlılığı son dört çeyrekte <N v={rr("roe_ttm")} pct d={0} />, aktif kârlılığı <N v={rr("roa_ttm")} pct d={1} />. Tüm tutarlar nominal TL; enflasyon muhasebesi hiçbir dönemde uygulanmamış, dolayısıyla bu oranlar reel getiri değil. Sermaye yeterliliği <N v={d("capital_adequacy_ratio")} d={1} />%, likidite karşılama oranı <N v={d("liquidity_coverage_ratio")} d={0} />%: kısıt sermaye ya da likidite değil, kur ve faiz riskinin iki defter arasındaki dağılımı.</p>
            <div className="rp-stats">
              {[
                { l: `Toplam aktif, ${U}`, v: BIG(ta), d: `çeyrek ${fmtPct(rr("assets_growth_qoq"))}, yıllık ${fmtPct(rr("assets_growth_yoy"))} (TL)`, data: S1("total_assets") },
                { l: `Özkaynak, ${U}`, v: BIG(v("total_equity")), d: `yıllık ${fmtPct(rr("equity_growth_yoy"))} (TL)`, data: S1("total_equity") },
                { l: `Net faiz geliri, çeyrek, ${U}`, v: big(cv(nii, LAST, "q"), u), d: `yıllık ${fmtPct(rr("nii_growth_q_yoy"))} (TL)`, data: F1("net_interest_income") },
                { l: `Net kâr, çeyrek, ${U}`, v: big(cv(np, LAST, "q"), u), d: `yıllık ${fmtPct(rr("profit_growth_q_yoy"))} (TL)`, data: F1("net_profit") },
                { l: "Özkaynak kârlılığı, son 4 çeyrek", v: fmtPct(rr("roe_ttm"), 1), d: `Blanco yöntemi ${fmtPct(rr("roe"), 1)}`, data: ser([{ key: "v", get: r("roe_ttm") }], stockPeriods), fmt: fmtPctAxis(0) },
                { l: "Türev nominal / aktif", v: `${fmtNum(derivX, 2)}×`, d: `${big(cv(v("derivatives_notional")), u)} nominal`, data: ser([{ key: "v", get: r("derivatives_to_assets") }], stockPeriods), fmt: (x: number) => `${fmtNum(x, 1)}×` },
              ].map(t => <div key={t.l} className="rp-stat"><div className="l">{t.l}</div><div className="v">{t.v}</div><div className="d">{t.d}</div><Mini data={t.data} fmt={t.fmt ?? axisMn} height={44} endLabel={false} /></div>)}
            </div>
            <p className="rp-fignote">Çizgiler {qlabel(stockPeriods[0])}'ten itibaren; 2021'in ilk iki çeyreğinde bilanço yok. Akımlar çeyrek, {qlabel(PERIODS[0])}'ten.</p>
          </section>

          {/* 2 */}
          <section id="bilanco">
            <h2 className="rp-h"><span>2</span>Bilanço</h2>
            <p>Aktif {qlabel(firstStock)}'te <B v={cv(v("total_assets", firstStock), firstStock)} u={u} /> idi, {qlabel(LAST)}'de <B v={cv(ta)} u={u} />. Büyümenin biçimi kadar yönü de konu: krediler aktifin <N v={share("loans_gross", firstStock)} pct d={0} />'inden <N v={share("loans_gross")} pct d={0} />'ine indi, nakit ve TCMB <N v={share("cash_and_central_bank", firstStock)} pct d={0} />'den <N v={share("cash_and_central_bank")} pct d={0} />'ye çıktı. Pasifte mevduat bir dönem <N v={Math.max(...stockPeriods.map(p => rr("deposits_to_assets", p) ?? 0))} pct d={0} />'ye kadar yükseldikten sonra <N v={rr("deposits_to_assets")} pct d={0} />'ye geriledi; yerini alınan krediler aldı.</p>
            <p>Kredi/Mevduat oranı 2023'te <N v={Math.max(...stockPeriods.map(p => rr("loan_to_deposit_ratio", p) ?? 0))} d={1} />× iken bugün <N v={rr("loan_to_deposit_ratio")} d={2} />×. Bu bir aracılık bilançosu değil; mevduat ve alınan krediler, TCMB'de ve para piyasasında tutulan TL likiditeyi fonluyor.</p>
            <Fig title={`Toplam aktif: TL ve yabancı para bölümü (${U})`} sub="Dönem sonu; KAP TP/YP ayrımı">
              <Legend series={TPYP} /><TimeChart data={tpyp("assets_tl", "assets_fx")} series={TPYP} stacked fmt={axisMn} tipFmt={tipMn} endLabels={false} />
            </Fig>
            <Fig title="Aktif kalemlerinin toplam aktif içindeki payı" sub="Ortak dikey eksen, tüm panellerde aynı ölçek">
              <div className="rp-grid3">{assetParts.map(([c, n]) => <div key={c}><p className="rp-mini-t">{n}</p><Mini data={shareSeries(c)} fmt={fmtPctAxis(0)} ymax={maxShare} /></div>)}</div>
            </Fig>
            <Fig title="Pasif kalemlerinin toplam pasif içindeki payı" sub="Ortak dikey eksen">
              <div className="rp-grid3">{liabParts.slice(0, 6).map(([c, n]) => <div key={c}><p className="rp-mini-t">{n}</p><Mini data={shareSeries(c)} fmt={fmtPctAxis(0)} ymax={maxShare} /></div>)}</div>
            </Fig>
            <Fig title={`Bilanço payları: ${qlabel(firstStock)} ile ${qlabel(LAST)}`} sub="İçi boş nokta başlangıç, dolu nokta son dönem">
              <Dumbbell labels={[qlabel(firstStock), qlabel(LAST)]} rows={[...assetParts, ...liabParts.slice(0, 4)].map(([c, n]) => ({ label: n, a: share(c, firstStock), b: share(c) }))} />
            </Fig>
            <Fig title={`Dört kalemde TL / yabancı para ayrımı (${U})`} sub="Krediler, mevduat, alınan krediler, nakit ve TCMB">
              <Legend series={TPYP} />
              <div className="rp-grid2">
                {([["loans_tl", "loans_fx", "Krediler"], ["deposits_tl", "deposits_fx", "Mevduat"], ["funds_borrowed_tl", "funds_borrowed_fx", "Alınan krediler"], ["cash_cb_tl", "cash_cb_fx", "Nakit ve TCMB"]] as const).map(([a, b, n]) => <div key={n}><p className="rp-mini-t">{n}</p><TimeChart data={tpyp(a, b)} series={TPYP} stacked height={170} fmt={axisMn} tipFmt={tipMn} endLabels={false} yTicks={3} /></div>)}
              </div>
            </Fig>
            <p className="rp-fignote"><b>Ne söylemez.</b> KAP ana tablosu TCMB bakiyesini kasadan ayırmaz; "Nakit ve TCMB" zorunlu karşılıkları da içerir. Menkul kıymet portföyü GUD K/Z, GUD DKG ve itfa edilmiş maliyet toplamıdır.</p>
          </section>

          {/* 3 */}
          <section id="fonlama">
            <h2 className="rp-h"><span>3</span>Fonlama ve swap</h2>
            <p>Alınan kredilerin <N v={(v("funds_borrowed_fx") ?? 0) / (v("funds_borrowed") ?? 1)} pct d={0} />'i yabancı para: <B v={cv(v("funds_borrowed_fx"))} u={u} />. Bilanço içinde yabancı para pasif, yabancı para aktifi <B v={cv(Math.abs(fxGap ?? 0))} u={u} /> aşıyor. Açık nazımda kapanıyor: swap para alım işlemlerinin TL bacağı <B v={cv(v("ccy_swap_buy_tl"))} u={u} />, satım işlemlerinin YP bacağı <B v={cv(v("ccy_swap_sell_fx"))} u={u} />. Yani YP borçlan, swap ile TL'ye çevir, TL'yi TCMB ve para piyasasında tut; faiz farkı NII'ye, kur farkı ticari K/Z'ye yazılsın.</p>
            <p>Türev nominali {qlabel(pq)}'de <B v={cv(v("derivatives_notional", pq), pq)} u={u} /> iken {qlabel(LAST)}'de <B v={cv(v("derivatives_notional"))} u={u} />; tek çeyrekte <N v={(v("derivatives_notional") ?? 0) / (v("derivatives_notional", pq) ?? 1) - 1} pct d={0} /> artış. Bu tek bir bildirime dayanıyor; kalıcı bir ölçek değişimi mi yoksa dönem sonu pozisyonu mu, {qlabel(PERIODS[PERIODS.length - 1]).replace("Ç2", "Ç3")} bildirimi gösterecek.</p>
            <Fig title={`Türev nominali, araç türüne göre (${U})`} sub="Nazım hesaplar, alım satım amaçlı işlemler, dönem sonu">
              <Legend series={[{ key: "sw", name: "Para ve faiz swapları", kind: "bar", color: C.tp }, { key: "fw", name: "Vadeli döviz", kind: "bar", color: C.yp }, { key: "fu", name: "Futures", kind: "bar", color: C.steps[4] }]} />
              <TimeChart data={ser([{ key: "sw", get: st("swaps_notional") }, { key: "fw", get: st("fx_forwards_notional") }, { key: "fu", get: st("futures_notional") }], stockPeriods)} series={[{ key: "sw", name: "Para ve faiz swapları", kind: "bar", color: C.tp }, { key: "fw", name: "Vadeli döviz", kind: "bar", color: C.yp }, { key: "fu", name: "Futures", kind: "bar", color: C.steps[4] }]} stacked fmt={axisMn} tipFmt={tipMn} endLabels={false} />
            </Fig>
            <Fig title={`YP borçlanma ve swap bacakları (${U})`} sub="Alınan kredilerin YP kısmı ile nazımdaki swap para alım (TL bacak) ve satım (YP bacak) nominalleri">
              <Legend series={[{ key: "fb", name: "Alınan krediler, YP", color: C.tp }, { key: "sell", name: "Swap para satım, YP bacağı", color: C.yp }, { key: "buy", name: "Swap para alım, TL bacağı", color: C.gold }]} />
              <TimeChart data={ser([{ key: "fb", get: st("funds_borrowed_fx") }, { key: "sell", get: st("ccy_swap_sell_fx") }, { key: "buy", get: st("ccy_swap_buy_tl") }], stockPeriods)} series={[{ key: "fb", name: "Alınan krediler YP", color: C.tp }, { key: "sell", name: "Swap satım YP", color: C.yp }, { key: "buy", name: "Swap alım TL", color: C.gold }]} fmt={axisMn} tipFmt={tipMn} />
            </Fig>
            <Fig title={`Bilanço içi yabancı para pozisyonu (${U})`} sub="YP aktif eksi YP pasif; negatif değer YP pasif fazlası">
              <TimeChart data={ser([{ key: "g", get: (p) => cv(rr("on_bs_fx_gap", p), p) }], stockPeriods)} series={[{ key: "g", name: "YP açığı", kind: "bar", color: C.tp }]} fmt={axisMn} tipFmt={tipMn} endLabels={false} />
            </Fig>
            <Fig title="Mevduat dışı kaynak ve kredi/mevduat" sub="Alınan krediler/aktif ve kredi/mevduat, aynı yüzde ekseninde">
              <Legend series={[{ key: "fb", name: "Alınan krediler / aktif", color: C.tp }, { key: "ld", name: "Kredi / mevduat", color: C.gold }]} />
              <TimeChart data={ser([{ key: "fb", get: r("funds_borrowed_to_assets") }, { key: "ld", get: r("loan_to_deposit_ratio") }], stockPeriods)} series={[{ key: "fb", name: "Alınan krediler/aktif", color: C.tp }, { key: "ld", name: "Kredi/mevduat", color: C.gold }]} fmt={fmtPctAxis(0)} tipFmt={(x) => fmtPct(x)} />
            </Fig>
            <p className="rp-fignote"><b>Ne söylemez.</b> Nazım nominalleri brüt; netleşme, vade ve karşı taraf bilgisi ana tabloda yok. Swap bacaklarının vadesi için dipnot (6. bölümde kalan vade tablosu) gerekir.</p>
          </section>

          {/* 4 */}
          <section id="karlilik">
            <h2 className="rp-h"><span>4</span>Kârlılık</h2>
            <p>Bu bilançoda NIM tek başına yanıltır. TL'yi swap ile fonlayan bir defterde faiz farkı net faiz gelirine, kur bacağı ticari sonuca düşer; ikisi aynı işlemin iki yüzüdür. {qlabel(LAST)}'de NII <B v={cv(nii, LAST, "q")} u={u} />, ticari K/Z <B v={cv(trd, LAST, "q")} u={u} />, toplam <B v={cv(carry, LAST, "q")} u={u} />. {peakP ? <>Ticari sonucun zirvesi {qlabel(peakP)}'te <B v={cv(peakTrd, peakP, "q")} u={u} /> idi; o çeyrekte NII yalnızca <B v={cv(fq("net_interest_income", peakP), peakP, "q")} u={u} />.</> : null} Net kâr çeyrekte <B v={cv(np, LAST, "q")} u={u} />; bir yıl önce <B v={cv(fq("net_profit", py), py, "q")} u={u} />.</p>
            <Fig bleed title={`Carry'nin iki bacağı: net faiz geliri, ticari K/Z ve toplamı, çeyrek (${U})`} sub="Sütunlar çeyreklik NII ve ticari K/Z (zarar kırmızı); siyah çizgi ikisinin toplamı, sarı çizgi net kâr">
              <Legend series={carrySeries} />
              <TimeChart data={carryData} series={carrySeries} height={320} fmt={axisMn} tipFmt={tipMn} annotations={[{ p: LAST, key: "trd", text: `ticari ${fmtNum(cv(trd, LAST, "q"))}`, dx: -10, dy: 18 }, ...(peakP ? [{ p: peakP, key: "trd", text: `ticari +${fmtNum(cv(peakTrd, peakP, "q"))}`, dx: -10, dy: -20 }] : [])]} />
            </Fig>
            <Fig title={`Yılın ilk yarısı: gelirden net kâra köprü (${U})`} sub="Yılbaşından 30 Haziran'a kümülatif; mavi başlangıç ve sonuç, açık mavi artı, kırmızı eksi">
              <div className="rp-grid2">
                <div><p className="rp-mini-t">1Y {LAST.slice(0, 4)}</p><Waterfall steps={bridge(LAST)} fmt={(x) => fmtNum(x)} /></div>
                <div><p className="rp-mini-t">1Y {py.slice(0, 4)}</p><Waterfall steps={bridge(py)} fmt={(x) => fmtNum(x)} /></div>
              </div>
            </Fig>
            <Fig title={`Faiz gelirinin kaynakları, çeyrek (${U})`} sub="Her panel kendi ölçeğinde">
              <div className="rp-grid3">{([["interest_on_loans", "Krediler"], ["interest_from_money_market", "Para piyasası"], ["interest_from_banks", "Bankalar"], ["interest_on_securities", "Menkul kıymetler"], ["other_interest_income", "Diğer"], ["net_fee_commission_income", "Net ücret ve komisyon"]] as const).map(([c, n]) => <div key={c}><p className="rp-mini-t">{n}</p><Mini data={F1(c)} fmt={axisMn} /></div>)}</div>
            </Fig>
            <Fig title={`Faiz giderinin kaynakları, çeyrek (${U}, negatif)`} sub="Mevduat, alınan krediler, para piyasası, diğer">
              <div className="rp-grid4">{([["interest_on_deposits", "Mevduat"], ["interest_on_funds_borrowed", "Alınan krediler"], ["interest_on_money_market", "Para piyasası"], ["other_interest_expense", "Diğer"]] as const).map(([c, n]) => <div key={c}><p className="rp-mini-t">{n}</p><Mini data={F1(c)} fmt={axisMn} /></div>)}</div>
            </Fig>
            <Fig title="Net faiz marjı: üç tanım" sub="Faiz getirili aktif üzerinden son 4 çeyrek; toplam aktif üzerinden Blanco yöntemi (YTD×4/q, iki nokta ortalaması); çeyrek×4 / dönem sonu aktif">
              <Legend series={[{ key: "a", name: "Faiz getirili aktif, son 4 çeyrek", color: C.tp }, { key: "b", name: "Toplam aktif, Blanco", color: C.yp }, { key: "c", name: "Çeyrek×4 / dönem sonu aktif", color: C.gold }]} />
              <TimeChart data={ser([{ key: "a", get: r("nim_iea_ttm") }, { key: "b", get: r("nim") }, { key: "c", get: r("nim_q_ann") }], stockPeriods)} series={[{ key: "a", name: "Faiz getirili, TTM", color: C.tp }, { key: "b", name: "Toplam aktif", color: C.yp }, { key: "c", name: "Çeyrek×4", color: C.gold }]} fmt={fmtPctAxis(0)} tipFmt={(x) => fmtPct(x)} padR={130} />
            </Fig>
            <p className="rp-fignote"><b>Ne söylemez.</b> Ticari K/Z içindeki kambiyo ve türev kalemleri swap'ın kur bacağını içerir ama müşteri işlemlerini de; ayrıştırma ana tablodan yapılamaz. NIM paydasındaki faiz getirili aktif KAP ana kalemlerinden türetildi (nakit ve TCMB, bankalar, para piyasası, menkul, brüt krediler).</p>
          </section>

          {/* 5 */}
          <section id="verimlilik">
            <h2 className="rp-h"><span>5</span>Verimlilik ve risk</h2>
            <p>Gider/gelir oranı 2023'te <N v={Math.min(...PERIODS.filter(p => p >= "2023-01-01").map(p => rr("cost_to_income", p) ?? 1))} pct d={0} /> ile dip yaptıktan sonra <N v={rr("cost_to_income")} pct d={0} />'ye çıktı: gelir büyümesi yavaşlarken personel ve diğer faaliyet giderleri nominal olarak iki katından fazla arttı. Kredi riski bu bilançoda konu değil: beklenen zarar karşılığı stoku <B v={cv(v("ecl_total_tfrs9"))} u={u} />, brüt krediler <B v={cv(v("loans_gross"))} u={u} />; donuk alacak dipnotta sıfır. Efektif vergi oranı 2023'ten bu yana <N v={rr("effective_tax_rate")} pct d={0} /> civarında.</p>
            <Fig title="Gider / gelir" sub="Faaliyet giderleri (personel + diğer) / (NII + net ücret + ticari K/Z + diğer gelir)">
              <Legend series={[{ key: "y", name: "Yılbaşından kümülatif", color: C.tp }, { key: "q", name: "Çeyrek", color: C.yp }]} />
              <TimeChart data={ser([{ key: "y", get: r("cost_to_income") }, { key: "q", get: r("cost_to_income_q") }])} series={[{ key: "y", name: "YTD", color: C.tp }, { key: "q", name: "Çeyrek", color: C.yp }]} fmt={fmtPctAxis(0)} tipFmt={(x) => fmtPct(x)} />
            </Fig>
            <Fig title={`Faaliyet giderleri ve toplam gelir, son 4 çeyrek (${U})`} sub="Gider mutlak değer; gelir = NII + net ücret + ticari + diğer">
              <Legend series={[{ key: "rev", name: "Toplam gelir", color: C.tp }, { key: "opx", name: "Faaliyet giderleri", color: C.gold }]} />
              <TimeChart data={ser([{ key: "rev", get: (p) => { const i = PERIODS.indexOf(p); if (i < 3) return null; let s = 0; for (let k = 0; k < 4; k++) { const x = q("total_revenue")(PERIODS[i - k]); if (x === null) return null; s += x; } return s; } }, { key: "opx", get: (p) => { const i = PERIODS.indexOf(p); if (i < 3) return null; let s = 0; for (let k = 0; k < 4; k++) { const x = q("operating_expenses")(PERIODS[i - k]); if (x === null) return null; s += x; } return -s; } }])} series={[{ key: "rev", name: "Toplam gelir", color: C.tp }, { key: "opx", name: "Faaliyet gideri", color: C.gold }]} fmt={axisMn} tipFmt={tipMn} />
            </Fig>
            <div className="rp-grid2">
              <Fig title="Kredi risk maliyeti" sub="Beklenen zarar karşılığı gideri (YTD×4/q) / ortalama brüt kredi">
                <TimeChart data={ser([{ key: "c", get: r("cost_of_risk") }], stockPeriods)} series={[{ key: "c", name: "CoR", color: C.tp }]} fmt={fmtPctAxis(2)} tipFmt={(x) => fmtPct(x, 2)} height={200} endLabels={false} />
              </Fig>
              <Fig title="Efektif vergi oranı" sub="Vergi karşılığı / vergi öncesi kâr, yılbaşından">
                <TimeChart data={ser([{ key: "t", get: r("effective_tax_rate") }])} series={[{ key: "t", name: "Efektif vergi", color: C.tp }]} fmt={fmtPctAxis(0)} tipFmt={(x) => fmtPct(x)} height={200} endLabels={false} />
              </Fig>
            </div>
          </section>

          {/* 6 */}
          <section id="sermaye">
            <h2 className="rp-h"><span>6</span>Sermaye ve likidite</h2>
            <p>Aşağıdaki göstergeler TBB banka kitabından geliyor ve yalnızca son üç dönem için var; KAP ana tablolarında bulunmuyor. Sermaye yeterliliği <N v={d("capital_adequacy_ratio")} d={1} />% ile asgari <span className="rp-n">%12,5</span>'in çok üzerinde; risk ağırlıklı varlıklar <B v={cv(d("risk_weighted_assets"))} u={u} />, aktifin <N v={(d("risk_weighted_assets") ?? 0) / (ta ?? 1)} pct d={0} />'i. Likidite karşılama oranı <N v={d("liquidity_coverage_ratio")} d={0} />%, net istikrarlı fonlama <N v={d("nsfr")} d={0} />%; NSFR'nin 31.12.2025'teki <N v={dip("nsfr")?.values["2025-12-31"]} d={0} />%'den gerilemesi fonlamanın kısalmasıyla tutarlı.</p>
            <div className="rp-facts">
              {[
                { v: fmtNum(d("capital_adequacy_ratio"), 1), s: "%", l: "Sermaye yeterliliği", sub: "Tier-1 " + fmtNum(d("tier_1_ratio"), 1) + "%" },
                { v: fmtNum(d("liquidity_coverage_ratio"), 0), s: "%", l: "Likidite karşılama", sub: "YP " + fmtNum(d("liquidity_coverage_ratio_fx"), 0) + "%" },
                { v: fmtNum(d("nsfr"), 0), s: "%", l: "Net istikrarlı fonlama", sub: "31.12.2025: " + fmtNum(dip("nsfr")?.values["2025-12-31"], 0) + "%" },
                { v: fmtPct(rr("equity_to_assets"), 1), s: "", l: "Özkaynak / aktif", sub: big(cv(v("total_equity")), u) + " özkaynak" },
                { v: big(cv(d("risk_weighted_assets")), u), s: "", l: "Risk ağırlıklı varlıklar", sub: fmtPct((d("risk_weighted_assets") ?? 0) / (ta ?? 1), 0) + " aktif" },
                { v: big(cv(d("hqla_stock")), u), s: "", l: "Yüksek kaliteli likit varlık", sub: "30 gün net çıkış " + big(cv(d("net_cash_outflows")), u) },
                { v: fmtNum(d("employee_count"), 0), s: "", l: "Çalışan", sub: fmtNum(d("branch_count"), 0) + " şube" },
                { v: fmtNum(d("npl_amount"), 0), s: "", l: "Donuk alacak", sub: "III–V. grup, " + U },
              ].map(f => <div key={f.l} className="rp-fact"><div className="v">{f.v}<small>{f.s}</small></div><div className="l">{f.l}</div><div className="s">{f.sub}</div></div>)}
            </div>
            <Fig title="Özkaynak ve aktif kârlılığı" sub="Son 4 çeyrek kâr / son 5 çeyrek sonu ortalaması; karşılaştırma için Blanco yöntemi (YTD×4/q, iki nokta)">
              <Legend series={[{ key: "a", name: "ROE, son 4 çeyrek", color: C.tp }, { key: "b", name: "ROE, Blanco", color: C.yp }, { key: "c", name: "ROA, son 4 çeyrek", color: C.gold }]} />
              <TimeChart data={ser([{ key: "a", get: r("roe_ttm") }, { key: "b", get: r("roe") }, { key: "c", get: r("roa_ttm") }], stockPeriods)} series={[{ key: "a", name: "ROE TTM", color: C.tp }, { key: "b", name: "ROE Blanco", color: C.yp }, { key: "c", name: "ROA TTM", color: C.gold }]} fmt={fmtPctAxis(0)} tipFmt={(x) => fmtPct(x)} />
            </Fig>
            <Fig title={`Kalan vade merdiveni, ${qlabel(LAST)} (${U})`} sub="Likidite riski dipnotu; dağıtılamayan sütunu sabit kıymetler ve özkaynak gibi vadesiz kalemleri taşır">
              <Ladder rows={ladder} fmt={(x) => fmtNum(x)} />
            </Fig>
            <div className="rp-grid2">
              <Fig title={`Faize duyarlılık: toplam pozisyon, ${qlabel(LAST)} (${U})`} sub="Bilanço içi artı nazım, yeniden fiyatlama kovalarına göre">
                <TimeChart data={repr} series={[{ key: "v", name: "Toplam pozisyon", kind: "bar", color: C.tp, negColor: C.neg }]} cat fmt={axisMn} tipFmt={tipMn} endLabels={false} height={220} />
              </Fig>
              <Fig title="Mevduatın vade yapısı" sub={`Son üç dönem, ${U}`}>
                <table className="rp-table"><thead><tr><th>Kova</th>{dipPeriods.map(p => <th key={p} className="n">{qlabel(p)}</th>)}</tr></thead>
                  <tbody>{dep.buckets.map((b, i) => { const row = dep.rows.find(x => x.code === "dep_maturity_total"); if (!row) return null; const vals = dipPeriods.map(p => cv(row.periods[p]?.[b] ?? null, p)); if (vals.every(x => !x)) return null; return <tr key={b} className={b === "total" ? "sum" : ""}><td>{dep.bucket_labels[i]}</td>{vals.map((x, k) => <td key={k} className="n">{fmtNum(x)}</td>)}</tr>; })}</tbody></table>
              </Fig>
            </div>
            <Fig title={`Parasal finansal araçlara uygulanan ortalama faiz oranları, ${qlabel(LAST)}`} sub="Faiz oranı riski dipnotu; stok ortalaması, yeni açılış faizi değil">
              <table className="rp-table"><thead><tr><th>Kalem</th><th className="n">TL</th><th className="n">USD</th><th className="n">EUR</th></tr></thead>
                <tbody>{rates.map(x => <tr key={x.name}><td>{x.name}</td>{x.vals.map((y, k) => <td key={k} className="n">{y === null ? <span className="muted">—</span> : `%${fmtNum(y, 2)}`}</td>)}</tr>)}</tbody></table>
              <p className="rp-fignote">TL kredi–mevduat makası <N v={(d("loan_interest_tl") ?? 0) - (d("deposit_interest_tl") ?? 0)} d={2} /> puan; TL alınan kredi maliyeti <N v={d("funds_borrowed_interest_tl")} d={2} />%, TL plasman getirisi <N v={d("due_from_banks_interest_tl")} d={2} />%.</p>
            </Fig>
          </section>

          {/* 7 */}
          <section id="kur">
            <h2 className="rp-h"><span>7</span>Kur merceği</h2>
            <p>Bu raporun sol üstündeki para birimi seçimi tüm tutarları çevirir: stoklar dönem sonu TCMB döviz alış kuruyla, çeyreklik akımlar dönem başı ve sonu kurunun ortalamasıyla. USD/TRY {qlabel(firstStock)}'te <N v={usdFirst} d={2} />, {qlabel(LAST)}'de <N v={usdLast} d={2} />. Aynı dönemde aktif TL'de <N v={(ta ?? 0) / (v("total_assets", firstStock) ?? 1)} d={1} /> katına çıkarken USD'de <N v={(conv(ta, LAST, "USD") ?? 0) / (conv(v("total_assets", firstStock), firstStock, "USD") ?? 1)} d={1} /> katına çıktı.</p>
            <Fig title="TCMB döviz alış kurları, dönem sonu" sub="Bilanço tarihinde geçerli bülten; geçici vergi değerleme kurlarıyla aynı">
              <Legend series={[{ key: "usd", name: "USD/TRY", color: C.tp }, { key: "eur", name: "EUR/TRY", color: C.gold }]} />
              <TimeChart data={fxData} series={[{ key: "usd", name: "USD/TRY", color: C.tp }, { key: "eur", name: "EUR/TRY", color: C.gold }]} fmt={(x) => fmtNum(x, 0)} tipFmt={(x) => fmtNum(x, 4)} />
            </Fig>
            <Fig title={`Toplam aktif üç para biriminde, endeks (${qlabel(firstStock)} = 100)`} sub="Aynı seri, üç kurla; fark kurun kendisidir">
              <Legend series={[{ key: "tl", name: "TL", color: C.tp }, { key: "usd", name: "USD", color: C.yp }, { key: "eur", name: "EUR", color: C.gold }]} />
              <TimeChart data={idxData} series={[{ key: "tl", name: "TL", color: C.tp }, { key: "usd", name: "USD", color: C.yp }, { key: "eur", name: "EUR", color: C.gold }]} fmt={(x) => fmtNum(x, 0)} tipFmt={(x) => fmtNum(x, 0)} refLine={100} padR={60} />
            </Fig>
            <Fig title="Aktif büyümesi, yıllık: TL ve USD" sub="Aynı çeyrek bir yıl öncesine göre; fark kur katkısı">
              <Legend series={[{ key: "tl", name: "TL", kind: "bar", color: C.tp }, { key: "usd", name: "USD", kind: "bar", color: C.yp }]} />
              <TimeChart data={growData} series={[{ key: "tl", name: "TL", kind: "bar", color: C.tp, negColor: C.neg }, { key: "usd", name: "USD", kind: "bar", color: C.yp, negColor: C.neg }]} fmt={fmtPctAxis(0)} tipFmt={(x) => fmtPct(x)} endLabels={false} />
            </Fig>
            <div className="rp-grid2">
              <Fig title="Çeyreklik net kâr, mn USD" sub="Dönem ortalama kuru">
                <TimeChart data={ser([{ key: "v", get: (p) => conv(fq("net_profit", p), p, "USD", "q") }])} series={[{ key: "v", name: "mn USD", color: C.tp }]} fmt={(x) => fmtNum(x, 0)} tipFmt={(x) => fmtNum(x, 1)} height={200} endLabels={false} />
              </Fig>
              <Fig title="Çeyreklik net kâr, mn EUR" sub="Dönem ortalama kuru">
                <TimeChart data={ser([{ key: "v", get: (p) => conv(fq("net_profit", p), p, "EUR", "q") }])} series={[{ key: "v", name: "mn EUR", color: C.gold }]} fmt={(x) => fmtNum(x, 0)} tipFmt={(x) => fmtNum(x, 1)} height={200} endLabels={false} />
              </Fig>
            </div>
            <p className="rp-fignote"><b>Ne söylemez.</b> USD'ye çevrilmiş TL kalemler, TL'nin değer kaybını da içerir; bu "dolar bazında reel" bir ölçü değildir. Doğru reel karşılaştırma için TÜFE ile düzeltme gerekir, banka TMS 29 uygulamamıştır.</p>
          </section>

          {/* 8 */}
          <section id="veri">
            <h2 className="rp-h"><span>8</span>Veri notu</h2>
            <p>Ana tablolar {D.meta.filings.length} KAP bildiriminden ayrıştırıldı ({String(D.meta.filings[0].filing).replace("Q", "Ç")}–{String(D.meta.filings[D.meta.filings.length - 1].filing).replace("Q", "Ç")}); her bildirimin önceki dönem sütunu da alındı, seri böylece {qlabel(PERIODS[0])}'e uzanıyor. Son bildirim milyon TL, öncekiler bin TL birimiyle yayımlandı; hepsi milyon TL'ye getirildi. Tutarlılık kontrolleri (aktif = pasif, TL + YP = toplam, K/Z net kârı = bilanço dönem kârı, özkaynak tablosu = bilanço özkaynağı) {checksOk ? "tüm dönemlerde tutuyor" : "bazı dönemlerde sapma gösteriyor"}. Sonraki bildirimlerde önceki döneme ait {restN} gerçek yeniden sınıflama var; hepsi küçük ve notlandı.</p>
            <p>Dipnot göstergeleri (sermaye yeterliliği, likidite oranları, ortalama faizler, vade ve yeniden fiyatlama tabloları, donuk alacak) TBB Ortak Veri Gönderim Seti banka kitaplarından geliyor; yalnızca 31.12.2025, 31.03.2026 ve 30.06.2026 için. Şube ve çalışan sayısı TBB'nin Haziran 2026 tablosundan.</p>
            <p>Bilinen boşluklar: 31.03.2021 ve 30.06.2021 bilançosu KAP'ta yok; hisse başına kâr bankanın bildirdiği gibi bırakıldı ve kendi içinde tutarsız olduğu için kullanılmadı; tüm tutarlar nominal.</p>
            <Fig title="Bildirimler" sub="KAP, Banka Finansal Rapor, konsolide olmayan">
              <table className="rp-table"><thead><tr><th>Dönem</th><th>Bildirim</th><th>Yayın</th><th>Birim</th><th>Denetim</th></tr></thead>
                <tbody>{D.meta.filings.map(f => <tr key={f.file_id}><td>{String(f.filing).replace("Q", "Ç")}</td><td><a href={f.url} target="_blank" rel="noreferrer">{f.file_id}</a></td><td className="muted">{f.pub_date ?? "—"}</td><td className="muted">{Number(f.unit).toLocaleString("tr-TR")} TL</td><td className="muted">{f.audit_type}, {f.audit_result}</td></tr>)}</tbody></table>
            </Fig>
            <Fig title="Kurlar" sub="TCMB döviz alış, bilanço tarihinde geçerli bülten">
              <table className="rp-table"><thead><tr><th>Dönem</th><th className="n">USD/TRY</th><th className="n">EUR/TRY</th><th className="n">EUR/USD</th></tr></thead>
                <tbody>{PERIODS.map(p => <tr key={p}><td>{qlabel(p)} <span className="muted">{p}</span></td><td className="n">{fmtNum(fx[p]?.usd, 4)}</td><td className="n">{fmtNum(fx[p]?.eur, 4)}</td><td className="n">{fx[p] ? fmtNum(fx[p].eur / fx[p].usd, 4) : "—"}</td></tr>)}</tbody></table>
              <p className="rp-fignote">30.09.2021 kuru ikincil kaynaktan, iki ondalık. Kaynaklar: {Object.values(D.fx.sources).join("; ")}.</p>
            </Fig>
            <div className="rp-colophon">
              <div><p>Deutsche Bank A.Ş. konsolide olmayan finansalları üzerine tek sayfalık rapor. Veri tabanı ve bu sayfa aynı kaynaktan üretilir; üretim {D.meta.generated}.</p><p>Tipografi: Archivo (başlıklar ve sayılar), Source Serif 4 (metin). Grafikler elle çizilmiş SVG; miktarlar mavi, kelimeler siyah, zarar kırmızı.</p></div>
              <div><p>Kaynaklar: {D.meta.sources.slice(0, 3).join("; ")}.</p><p>Ayrıntılı veri, oran tanımları ve ham tablolar için panel; Excel karşılığı DBTR_KAP_DB.xlsx.</p></div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
