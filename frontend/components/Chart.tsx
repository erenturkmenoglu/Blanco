"use client";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const COLORS = ["#0b4f8a", "#b3541e", "#1f6f3a", "#6b6b6b", "#7b3f9e", "#c9a227", "#2a9d8f", "#9e2a2b"];
export type Series = { key: string; name: string; kind?: "line" | "bar" };
type Props = { title: string; data: any[]; series: Series[]; unit?: string; kind?: "line" | "bar"; stacked?: boolean; pct?: boolean; digits?: number; note?: string; height?: number };

const nice = (v: number) => Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(1)}m` : Math.abs(v) >= 1e3 ? `${(v / 1e3).toFixed(v % 1e3 === 0 ? 0 : 1)}k` : `${Math.round(v * 100) / 100}`;

/** Fonksiyonel grafik: az gridline, köşe yok, legend altta, boş dönem çizilmez (null), her seri adlandırılmış. */
export function Chart({ title, data, series, unit, kind = "line", stacked = false, pct = false, digits, note, height = 260 }: Props) {
  const tickY = (v: number) => pct ? `${(v * 100).toFixed(digits ?? 0)}%` : nice(v);
  const fmtV = (v: any) => v === null || v === undefined ? "—" : pct ? `${(Number(v) * 100).toFixed(digits ?? 2)}%` : Number(v).toLocaleString("tr-TR", { maximumFractionDigits: digits ?? 1 });
  const Wrap: any = kind === "bar" ? BarChart : LineChart;
  const hasNeg = data.some(r => series.some(s => typeof r[s.key] === "number" && r[s.key] < 0));
  return (
    <div className="card chart">
      <h3>{title}{unit ? <span className="unit"> · {unit}</span> : null}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <Wrap data={data} margin={{ top: 6, right: 10, bottom: 0, left: 4 }} barGap={1} barCategoryGap="25%">
          <CartesianGrid stroke="#e6e6e6" vertical={false} />
          <XAxis dataKey="x" tick={{ fontSize: 11 }} interval={data.length > 16 ? 1 : 0} angle={0} height={24} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={tickY} width={54} tickCount={5} />
          {hasNeg && <ReferenceLine y={0} stroke="#999" />}
          <Tooltip formatter={fmtV} labelFormatter={(l: any, p: any) => p?.[0]?.payload?.p ?? l} contentStyle={{ fontSize: 12 }} />
          {series.length > 1 && <Legend verticalAlign="bottom" iconType="plainline" wrapperStyle={{ fontSize: 12 }} />}
          {series.map((s, i) => (s.kind ?? kind) === "bar"
            ? <Bar key={s.key} dataKey={s.key} name={s.name} fill={COLORS[i % COLORS.length]} stackId={stacked ? "a" : undefined} isAnimationActive={false} radius={0} />
            : <Line key={s.key} type="linear" dataKey={s.key} name={s.name} stroke={COLORS[i % COLORS.length]} strokeWidth={1.6} dot={false} connectNulls={false} isAnimationActive={false} />)}
        </Wrap>
      </ResponsiveContainer>
      {note && <div className="note">{note}</div>}
    </div>
  );
}
