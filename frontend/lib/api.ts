/**
 * Veri erişim katmanı. İki mod:
 *  - API modu: NEXT_PUBLIC_API_BASE_URL tanımlıysa FastAPI'ye gider (Docker / yerel).
 *  - Statik mod (Vercel): ortam değişkeni yoksa public/data/*.json snapshot'ı okunur (backend gerekmez).
 *    Snapshot, backend/scripts/export_static.py ile aynı API fonksiyonlarından üretilir → şekiller birebir aynıdır.
 */
export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "";
export const STATIC_MODE = !API;

type Params = Record<string, string | number | undefined>;
const bankCache = new Map<string, Promise<any>>();

async function fetchJson(path: string) {
  const r = await fetch(path, { cache: "force-cache" });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

function bankFile(bank: string, scope: string): Promise<any> {
  const key = `${bank}_${scope}`;
  if (!bankCache.has(key)) bankCache.set(key, fetchJson(`/data/bank/${key}.json`).catch(() => ({ bank, scope, series: {}, derived: {}, rates: null, maturity: {} })));
  return bankCache.get(key)!;
}

async function staticApi(path: string, params: Params = {}): Promise<any> {
  const p = params;
  const scope = String(p.scope ?? "solo");
  switch (path) {
    case "/api/banks": return fetchJson("/data/banks.json");
    case "/api/periods": return fetchJson("/data/periods.json");
    case "/api/sources": return fetchJson("/data/sources.json");
    case "/api/verification": return fetchJson("/data/verification.json");
    case "/api/jobs": return fetchJson("/data/jobs.json").then((j: any[]) => j.slice(0, Number(p.limit ?? 50)));
    case "/api/quality": return fetchJson("/data/quality.json");
    case "/api/documents": return fetchJson("/data/documents.json");
    case "/api/dictionary": return fetchJson("/data/dictionary.json");
    case "/api/observations": {
      const b = await bankFile(String(p.bank), scope);
      return { bank: p.bank, metric: p.metric, scope, series: b.series?.[String(p.metric)] ?? [] };
    }
    case "/api/derived": {
      const b = await bankFile(String(p.bank), scope);
      return { bank: p.bank, period_end: p.period_end, scope, status: "DERIVED", metrics: b.derived?.[String(p.period_end)] ?? [] };
    }
    case "/api/rates": {
      const b = await bankFile(String(p.bank), scope);
      return b.rates ?? { bank: p.bank, scope, series: [], spreads: [] };
    }
    case "/api/maturity": {
      const b = await bankFile(String(p.bank), scope);
      const r = b.maturity?.[String(p.period_end)]?.[String(p.item ?? "total_assets")];
      if (!r) return { bank: p.bank, period_end: p.period_end, item: p.item, basis: null, buckets: {}, shares: null, limitations: null, bases: {} };
      const want = p.basis ? r.bases?.[String(p.basis)] : null;         // istenen temel varsa üst düzey alanlar onunla değiştirilir
      return want ? { ...r, ...want } : r;
    }
    case "/api/maturity/items": {
      const b = await bankFile(String(p.bank), scope);
      const per = b.maturity?.[String(p.period_end)] ?? {};
      const items: Record<string, any[]> = {};
      for (const [item, r] of Object.entries<any>(per)) {
        const bases = Object.values<any>(r.bases ?? {}).filter(x => Object.values(x.buckets ?? {}).some(v => v !== null));
        if (bases.length) items[item] = bases.map(x => ({ basis: x.basis, basis_label: x.basis_label, observations: Object.keys(x.buckets ?? {}).length }));
      }
      return { bank: p.bank, period_end: p.period_end, items };
    }
    case "/api/compare": {
      const codes = String(p.banks).split(",").map(s => s.trim()).filter(Boolean);
      const banks: Bank[] = await fetchJson("/data/banks.json");
      const rows: any[] = [];
      for (const c of codes) {
        const b = await bankFile(c, scope);
        const o = (b.series?.[String(p.metric)] ?? []).filter((x: Obs) => x.period_end === String(p.period_end) && (x.currency ?? "ALL") === "ALL")
          .sort((a: Obs, b2: Obs) => (a.period_start ?? "").localeCompare(b2.period_start ?? ""))[0];   // akışta YTD satırı
        rows.push({ bank: c, name: banks.find(x => x.code === c)?.name ?? c, value: o?.value ?? null, unit: o?.unit ?? null, status: o?.status ?? "UNAVAILABLE", revision: o?.revision ?? null });
      }
      rows.filter(r => r.value !== null).sort((a, b) => b.value - a.value).forEach((r, i) => (r.rank = i + 1));
      return { metric: p.metric, period_end: p.period_end, scope, rows };
    }
    default: throw new Error(`statik modda desteklenmeyen uç nokta: ${path}`);
  }
}

export async function api<T>(path: string, params?: Params): Promise<T> {
  if (STATIC_MODE) return staticApi(path, params);
  const url = new URL(API + path);
  if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && url.searchParams.set(k, String(v)));
  const r = await fetch(url.toString(), { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

export type Bank = { code: string; name: string; short_name?: string; type?: string; ownership?: string; observations: number; latest_total_assets?: number | null; latest_total_assets_period?: string | null };
export type Obs = {
  period_end: string; value: number | null; unit: string; status: string; source: string; source_url?: string | null;
  retrieved_at?: string | null; revision: number; scope: string; frequency: string; currency?: string | null; period_start?: string | null; flags?: string[] | null;
};
export type DerivedMetric = { metric: string; value: number | null; unit: string; method: string; limitations?: string | null; inputs?: any };

export const fmt = (v: number | null | undefined, unit?: string) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";          // eksik veri 0 olarak GÖSTERİLMEZ
  if (unit === "pct") return `${v.toFixed(2)}%`;
  if (unit === "ratio") return v.toFixed(3);
  if (unit === "count") return v.toLocaleString("tr-TR");
  if (Math.abs(v) >= 1e9) return `${(v / 1e9).toLocaleString("tr-TR", { maximumFractionDigits: 1 })} mlr TL`;
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toLocaleString("tr-TR", { maximumFractionDigits: 1 })} mn TL`;
  return v.toLocaleString("tr-TR", { maximumFractionDigits: 0 });
};

export const SECTIONS: { title: string; metrics: string[]; derived?: string[] }[] = [
  { title: "1. Genel Finansal Görünüm", metrics: ["total_assets", "loans_gross", "total_deposits", "total_equity", "net_profit"] },
  { title: "2. Bilanço Analizi", metrics: ["cash_and_central_bank", "due_from_banks", "securities_fvtpl", "securities_fvoci", "securities_amortized_total", "loans_tl", "loans_fx", "funds_borrowed", "money_market_funds", "securities_issued", "subordinated_debt", "non_deposit_funding", "other_liabilities"] },
  { title: "3. Gelir Tablosu (yıl başından kümülatif)", metrics: ["interest_income", "interest_on_loans", "interest_on_securities", "interest_expense", "interest_on_deposits", "net_interest_income", "fee_commission_income", "fee_commission_expense", "net_fee_commission_income", "trading_income", "other_operating_income", "personnel_expenses", "other_operating_expenses", "expected_credit_loss_expense", "profit_before_tax", "net_profit"] },
  { title: "4. Kârlılık", metrics: [], derived: ["roa", "roe", "nim", "cost_to_income"] },
  { title: "5. Büyüme", metrics: [], derived: ["assets_growth_qoq", "assets_growth_yoy", "loans_growth_qoq", "loans_growth_yoy", "deposits_growth_qoq", "deposits_growth_yoy", "equity_growth_yoy", "profit_growth_yoy"] },
  { title: "6. Kredi Kalitesi", metrics: ["npl_amount", "npl_provisions", "stage_1_loans", "stage_2_loans_not_restructured", "stage_2_restructured_modified", "stage_2_restructured_refinanced", "ecl_stage1", "ecl_stage2", "ecl_stage3"], derived: ["npl_ratio", "npl_coverage_ratio", "cost_of_risk"] },
  { title: "7. Sermaye Yeterliliği", metrics: ["capital_adequacy_ratio", "risk_weighted_assets", "regulatory_equity"], derived: ["equity_to_assets"] },
  { title: "8. Likidite", metrics: ["nsfr", "available_stable_funding", "required_stable_funding"], derived: ["loan_to_deposit_ratio", "liquid_assets_ratio", "cash_to_assets"] },
  { title: "11. Operasyonel Verimlilik", metrics: ["employee_count", "branch_count"], derived: ["assets_per_employee", "profit_per_employee", "deposits_per_branch", "loans_per_branch"] },
];
