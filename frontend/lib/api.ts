export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function api<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(API + path);
  if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && url.searchParams.set(k, String(v)));
  const r = await fetch(url.toString(), { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

export type Bank = { code: string; name: string; short_name?: string; type?: string; ownership?: string; observations: number };
export type Obs = {
  period_end: string; value: number | null; unit: string; status: string; source: string; source_url?: string | null;
  retrieved_at?: string | null; revision: number; scope: string; frequency: string; currency?: string | null;
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
  { title: "2. Bilanço Analizi", metrics: ["cash_and_cash_equivalents", "balances_with_central_bank", "loans_tl", "loans_fx", "securities_portfolio", "deposits_tl", "deposits_fx", "demand_deposits", "time_deposits", "funds_borrowed", "securities_issued"] },
  { title: "3. Gelir Tablosu (yıl başından kümülatif)", metrics: ["interest_income", "interest_expense", "net_interest_income", "net_fee_commission_income", "trading_income", "operating_expenses", "personnel_expenses", "provision_expenses", "profit_before_tax", "net_profit"] },
  { title: "4. Kârlılık", metrics: [], derived: ["roa", "roe", "nim", "cost_to_income"] },
  { title: "5. Büyüme", metrics: [], derived: ["assets_growth_qoq", "assets_growth_yoy", "loans_growth_qoq", "loans_growth_yoy", "deposits_growth_qoq", "deposits_growth_yoy", "equity_growth_yoy", "profit_growth_yoy"] },
  { title: "6. Kredi Kalitesi", metrics: ["npl_amount", "loan_loss_provisions", "stage_2_loans", "stage_3_loans"], derived: ["npl_ratio", "npl_coverage_ratio", "cost_of_risk"] },
  { title: "7. Sermaye Yeterliliği", metrics: ["capital_adequacy_ratio", "tier_1_ratio", "cet1_ratio", "risk_weighted_assets"], derived: ["equity_to_assets"] },
  { title: "8. Likidite", metrics: ["liquidity_coverage_ratio"], derived: ["loan_to_deposit_ratio", "liquid_assets_ratio", "cash_to_assets"] },
  { title: "11. Operasyonel Verimlilik", metrics: ["employee_count", "branch_count"], derived: ["assets_per_employee", "profit_per_employee", "deposits_per_branch", "loans_per_branch"] },
];
