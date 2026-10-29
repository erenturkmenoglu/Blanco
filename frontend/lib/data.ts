import raw from "@/public/data/dbtr.json";

export type Ccy = "TL" | "USD" | "EUR";
export type Item = { code: string; name: string; section: string; kind: string; status: string; source: string; note: string; values: Record<string, number | null> };
export type FlowQ = { code: string; name: string; q: Record<string, number | null>; ttm: Record<string, number | null> };
export type Ratio = { code: string; name: string; method: string; formula: string; unit: "pct" | "x" | "mn"; values: Record<string, number | null> };
export type StmtRow = { key: string; label: string; level?: number; component?: string; values: Record<string, number | null> };
export type Stmt = { title: string; note: string; periods: string[]; rows: StmtRow[] };
export type DipScalar = { code: string; name: string; unit: string; source: string; files: string[]; note: string; values: Record<string, number | null> };
export type DipTable = { group: string; title: string; buckets: string[]; bucket_labels: string[]; rows: { code: string; name: string; periods: Record<string, Record<string, number | null>> }[] };

export const D = raw as unknown as {
  meta: { bank: string; scope: string; generated: string; unit: string; filings: any[]; sources: string[]; gaps: string[] };
  periods: string[];
  fx: { rates: Record<string, { usd: number; eur: number }>; sources: Record<string, string>; method: Record<string, string> };
  items: Item[]; flows_q: FlowQ[]; ratios: Ratio[]; statements: Record<string, Stmt>;
  checks: { name: string; values: Record<string, number | string | null> }[];
  restatements: any[]; dipnot: { scalars: DipScalar[]; tables: DipTable[] };
};

export const PERIODS = D.periods;
export const LAST = PERIODS[PERIODS.length - 1];
export const item = (code: string) => D.items.find(i => i.code === code)!;
export const flow = (code: string) => D.flows_q.find(i => i.code === code)!;
export const ratio = (code: string) => D.ratios.find(i => i.code === code)!;
export const dip = (code: string) => D.dipnot.scalars.find(i => i.code === code);

export function qlabel(p: string) { const [y, m] = p.split("-"); return `${y.slice(2)}Ç${Math.ceil(Number(m) / 3)}`; }
export function prevQ(p: string) { const i = PERIODS.indexOf(p); return i > 0 ? PERIODS[i - 1] : null; }

/** Kur: stok → dönem sonu; çeyrek akım → (önceki dönem sonu + dönem sonu)/2. */
export function fxRate(p: string, ccy: Ccy, kind: "stock" | "q" = "stock"): number | null {
  if (ccy === "TL") return 1;
  const r = D.fx.rates[p]; if (!r) return null;
  const v = ccy === "USD" ? r.usd : r.eur;
  if (kind === "stock") return v;
  const pp = prevQ(p); const rp = pp ? D.fx.rates[pp] : null;
  if (!rp) return null;
  return (v + (ccy === "USD" ? rp.usd : rp.eur)) / 2;
}
export function conv(v: number | null | undefined, p: string, ccy: Ccy, kind: "stock" | "q" = "stock"): number | null {
  if (v === null || v === undefined) return null;
  const r = fxRate(p, ccy, kind); return r ? v / r : null;
}
/** YTD akımı seçilen para biriminde: çeyreklik dönüşümlerin toplamı. */
export function convYtd(code: string, p: string, ccy: Ccy): number | null {
  const f = flow(code); if (!f) return null;
  if (ccy === "TL") return item(code)?.values[p] ?? null;
  const y = p.slice(0, 4); let s = 0;
  for (const q of PERIODS) { if (q.slice(0, 4) !== y || q > p) continue; const v = conv(f.q[q], q, ccy, "q"); if (v === null) return null; s += v; }
  return s;
}

export const fmt = (v: number | null | undefined, d = 0) => v === null || v === undefined ? "—" : v.toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtPct = (v: number | null | undefined, d = 1) => v === null || v === undefined ? "—" : `${(v * 100).toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d })}%`;
export const ccyUnit = (c: Ccy) => c === "TL" ? "mn TL" : c === "USD" ? "mn USD" : "mn EUR";

/** Grafik verisi: kodlar → [{x, k1, k2…}] ; boş dönemler null (0 çizilmez), baştaki/sondaki tamamen boş dönemler atılır. */
export function series(spec: { key: string; get: (p: string) => number | null }[], periods: string[] = PERIODS) {
  const rows = periods.map(p => { const o: Record<string, any> = { x: qlabel(p), p }; for (const s of spec) o[s.key] = s.get(p); return o; });
  const has = (r: any) => spec.some(s => r[s.key] !== null && r[s.key] !== undefined);
  let a = 0, b = rows.length - 1; while (a < b && !has(rows[a])) a++; while (b > a && !has(rows[b])) b--;
  return rows.slice(a, b + 1);
}
export const STOCK_FROM = "2021-09-30";     // 2021Ç1-Ç2 bilançosu yok → stok grafikler buradan
export const stockPeriods = PERIODS.filter(p => p >= STOCK_FROM);
