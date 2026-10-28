"use client";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Bar, BarChart } from "recharts";

type Point = { x: string; [k: string]: number | string | null };

/** Fonksiyonel grafik: az gridline, köşe yok, legend altta, eksik dönem 0 çizilmez (connectNulls=false), her seri adlandırılmış. */
export function SeriesChart({ data, series, unit, kind = "line" }: { data: Point[]; series: { key: string; name: string }[]; unit?: string; kind?: "line" | "bar" }) {
  const tick = (v: number) => unit === "pct" ? `${v.toFixed(1)}%` : Math.abs(v) >= 1e9 ? `${(v / 1e9).toFixed(0)}mlr` : Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(0)}mn` : `${v}`;
  const Chart: any = kind === "bar" ? BarChart : LineChart;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <Chart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 8 }}>
        <CartesianGrid stroke="#e4e4e4" vertical={false} />
        <XAxis dataKey="x" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={28} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={tick} width={56} tickCount={5} />
        <Tooltip formatter={(v: any) => (v === null || v === undefined ? "—" : unit === "pct" ? `${Number(v).toFixed(2)}%` : Number(v).toLocaleString("tr-TR"))} />
        <Legend verticalAlign="bottom" wrapperStyle={{ fontSize: 12 }} />
        {series.map((s, i) => kind === "bar"
          ? <Bar key={s.key} dataKey={s.key} name={s.name} fill={["#0b4f8a", "#8a4b0b", "#1f6f3a", "#555"][i % 4]} isAnimationActive={false} radius={0} />
          : <Line key={s.key} type="linear" dataKey={s.key} name={s.name} stroke={["#0b4f8a", "#8a4b0b", "#1f6f3a", "#555"][i % 4]} dot={false} connectNulls={false} isAnimationActive={false} />)}
      </Chart>
    </ResponsiveContainer>
  );
}
