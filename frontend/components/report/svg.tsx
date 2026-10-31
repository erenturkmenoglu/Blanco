"use client";
/**
 * Rapor grafik ilkelleri — elle çizilmiş SVG.
 * Kurallar: tek y ekseni, en fazla 3 yardımcı çizgi, doğrudan uç etiketleri, boş dönem çizilmez (null → kesik),
 * negatif değer için ayrılmış renk, metin asla seri rengini giymez (eksen/etiketler mürekkep tonlarında).
 */
import { useEffect, useRef, useState } from "react";

export const C = {
  ink: "#1c1c1e", ink2: "#5c5c60", ink3: "#9a9a9e", rule: "#dcdce2", surface: "#f9f9fb",
  tp: "#1d3fbf", yp: "#6b84e3", gold: "#b8860b", neg: "#d2452b", ctx: "#a7a7ad",
  steps: ["#1d3fbf", "#3f5bd0", "#6b84e3", "#93a5ec", "#b7c2f2", "#d6dcf7"],
};

export type Pt = { p: string; x: string; [k: string]: number | string | null | undefined };
export type S = { key: string; name: string; color?: string; kind?: "line" | "bar"; negColor?: string; width?: number };

export function useWidth<T extends HTMLElement>(initial = 720) {
  const ref = useRef<T>(null);
  const [w, setW] = useState(initial);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(es => { for (const e of es) { const cw = Math.round(e.contentRect.width); if (cw > 0) setW(cw); } });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

export function niceTicks(min: number, max: number, n = 4): number[] {
  if (!isFinite(min) || !isFinite(max)) return [0];
  if (min === max) { max = min === 0 ? 1 : min * 1.1; min = min === 0 ? 0 : min * 0.9; }
  const raw = (max - min) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => raw <= s) ?? 10 * mag;
  const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step;
  const out: number[] = []; for (let v = lo; v <= hi + step / 2; v += step) out.push(Math.round(v * 1e6) / 1e6);
  return out;
}
export const fmtAxis = (v: number) => Math.abs(v) >= 10000 ? `${(v / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 1 })} mlr` : Math.abs(v) >= 100 ? v.toLocaleString("tr-TR", { maximumFractionDigits: 0 }) : v.toLocaleString("tr-TR", { maximumFractionDigits: 2 });
export const fmtPctAxis = (d = 0) => (v: number) => `%${(v * 100).toLocaleString("tr-TR", { maximumFractionDigits: d })}`;
export const fmtNum = (v: number | null | undefined, d = 0) => v === null || v === undefined ? "—" : v.toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
export const fmtPct = (v: number | null | undefined, d = 1) => v === null || v === undefined ? "—" : `%${(v * 100).toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
/** mn → "46,0 mlr" / "894 mn" */
export const big = (v: number | null | undefined, unit = "") => v === null || v === undefined ? "—" : Math.abs(v) >= 1000 ? `${(v / 1000).toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} mlr${unit ? " " + unit : ""}` : `${v.toLocaleString("tr-TR", { maximumFractionDigits: 0 })} mn${unit ? " " + unit : ""}`;

const F = "'Archivo Variable', system-ui, sans-serif";
const T = { fontFamily: F, fontSize: 11, fill: C.ink2 } as const;

/** x ekseni etiketleri: ilk nokta, her yılın Ç1'i (yıl), son nokta (çakışmıyorsa). */
function xLabels(data: Pt[]) {
  const out: { i: number; t: string }[] = [];
  data.forEach((d, i) => { if (d.p.slice(5, 7) === "03") out.push({ i, t: d.p.slice(0, 4) }); });
  if (!out.length || out[0].i > 1) out.unshift({ i: 0, t: data[0].x });
  const last = data.length - 1;
  if (last - (out[out.length - 1]?.i ?? -9) > 2) out.push({ i: last, t: data[last].x });
  return out;
}

type Annot = { p: string; key: string; text: string; dx?: number; dy?: number };
type TimeProps = {
  data: Pt[]; series: S[]; height?: number; fmt?: (v: number) => string; tipFmt?: (v: number) => string;
  stacked?: boolean; yZero?: boolean; endLabels?: boolean; annotations?: Annot[]; padR?: number; yTicks?: number; refLine?: number; cat?: boolean;
};

/** Zaman serisi: çizgi ve/veya sütun, tek eksen. */
export function TimeChart({ data, series, height = 240, fmt = fmtAxis, tipFmt, stacked = false, yZero = true, endLabels = true, annotations = [], padR, yTicks = 4, refLine, cat = false }: TimeProps) {
  const [ref, W] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const bars = series.filter(s => s.kind === "bar"), lines = series.filter(s => s.kind !== "bar");
  const pl = 48, pr = padR ?? (endLabels && lines.length ? 118 : 16), pt = 14, pb = 28;
  const pw = Math.max(80, W - pl - pr), ph = height - pt - pb;
  const n = data.length, step = n > 1 ? pw / (n - 1) : pw;
  // y extent
  let lo = yZero ? 0 : Infinity, hi = yZero ? 0 : -Infinity;
  data.forEach(d => {
    let sp = 0, sn = 0;
    for (const s of series) { const v = d[s.key]; if (typeof v !== "number") continue; if (stacked && s.kind === "bar") { if (v >= 0) sp += v; else sn += v; } else { lo = Math.min(lo, v); hi = Math.max(hi, v); } }
    lo = Math.min(lo, sn); hi = Math.max(hi, sp);
  });
  if (refLine !== undefined) { lo = Math.min(lo, refLine); hi = Math.max(hi, refLine); }
  const ticks = niceTicks(lo, hi, yTicks); const y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const X = (i: number) => pl + i * step, Y = (v: number) => pt + ph - (v - y0) / (y1 - y0) * ph;
  const bw = Math.min(22, Math.max(3, (stacked || bars.length <= 1 ? step * 0.62 : step * 0.7 / bars.length)));
  const xl = cat ? data.map((d, i) => ({ i, t: d.x })) : xLabels(data);
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => { const r = e.currentTarget.getBoundingClientRect(); const i = Math.round((e.clientX - r.left - pl) / step); setHover(i >= 0 && i < n ? i : null); };
  const tf = tipFmt ?? fmt;
  // end label positions with simple collision avoidance
  const ends = lines.map(s => { let i = n - 1; while (i >= 0 && typeof data[i][s.key] !== "number") i--; return i >= 0 ? { s, i, y: Y(data[i][s.key] as number) } : null; }).filter(Boolean) as { s: S; i: number; y: number }[];
  ends.sort((a, b) => a.y - b.y); for (let k = 1; k < ends.length; k++) if (ends[k].y - ends[k - 1].y < 13) ends[k].y = ends[k - 1].y + 13;
  return (
    <div ref={ref} className="rp-svgwrap" onPointerLeave={() => setHover(null)}>
      <svg width="100%" viewBox={`0 0 ${W} ${height}`} style={{ display: "block", overflow: "visible" }} onPointerMove={onMove}>
        {ticks.map(t => <g key={t}><line x1={pl} x2={pl + pw} y1={Y(t)} y2={Y(t)} stroke={t === 0 ? C.ink3 : C.rule} strokeWidth={1} /><text x={pl - 8} y={Y(t) + 3.5} textAnchor="end" style={T}>{fmt(t)}</text></g>)}
        {refLine !== undefined && <line x1={pl} x2={pl + pw} y1={Y(refLine)} y2={Y(refLine)} stroke={C.ink3} strokeWidth={1} />}
        {!cat && data.map((d, i) => <line key={i} x1={X(i)} x2={X(i)} y1={pt + ph} y2={pt + ph + (d.p.slice(5, 7) === "03" ? 6 : 3)} stroke={C.ink3} strokeWidth={1} />)}
        {xl.map(l => <text key={l.i} x={X(l.i)} y={pt + ph + 20} textAnchor="middle" style={T}>{l.t}</text>)}
        {/* bars */}
        {data.map((d, i) => {
          let up = 0, dn = 0; const g = bars.length; const x0 = X(i) - (stacked ? bw / 2 : (bw * g) / 2);
          return bars.map((s, k) => {
            const v = d[s.key]; if (typeof v !== "number" || v === 0) return null;
            let yA: number, yB: number;
            if (stacked) { if (v >= 0) { yA = Y(up + v); yB = Y(up); up += v; } else { yA = Y(dn); yB = Y(dn + v); dn += v; } }
            else { yA = Y(Math.max(v, 0)); yB = Y(Math.min(v, 0)); }
            const h = Math.max(1, Math.abs(yB - yA) - (stacked ? 1.5 : 0));
            const col = v < 0 && s.negColor ? s.negColor : (s.color ?? C.tp);
            return <rect key={s.key} x={stacked ? x0 : x0 + k * bw + 0.5} y={Math.min(yA, yB)} width={Math.max(1, (stacked ? bw : bw - 1))} height={h} fill={col} opacity={hover === null || hover === i ? 1 : 0.55} />;
          });
        })}
        {/* lines */}
        {lines.map(s => {
          const segs: string[] = []; let cur = "";
          data.forEach((d, i) => { const v = d[s.key]; if (typeof v === "number") { cur += `${cur ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; } else if (cur) { segs.push(cur); cur = ""; } });
          if (cur) segs.push(cur);
          return segs.map((p, k) => <path key={s.key + k} d={p} fill="none" stroke={s.color ?? C.tp} strokeWidth={s.width ?? 2} strokeLinejoin="round" strokeLinecap="round" />);
        })}
        {endLabels && ends.map(e => <text key={e.s.key} x={X(e.i) + 8} y={e.y + 3.5} style={{ ...T, fill: C.ink }}>{e.s.name}</text>)}
        {annotations.map((a, k) => {
          const i = data.findIndex(d => d.p === a.p); if (i < 0) return null; const v = data[i][a.key]; if (typeof v !== "number") return null;
          const x = X(i), y = Y(v), dx = a.dx ?? -8, dy = a.dy ?? -22;
          return <g key={k}><line x1={x} y1={y} x2={x + dx} y2={y + dy + 4} stroke={C.ink2} strokeWidth={1} /><text x={x + dx} y={y + dy} textAnchor={dx < 0 ? "end" : "start"} style={{ ...T, fill: C.ink, fontSize: 11.5 }}>{a.text}</text></g>;
        })}
        {hover !== null && <g>
          <line x1={X(hover)} x2={X(hover)} y1={pt} y2={pt + ph} stroke={C.ink3} strokeWidth={1} />
          {lines.map(s => { const v = data[hover][s.key]; return typeof v === "number" ? <circle key={s.key} cx={X(hover)} cy={Y(v)} r={4} fill={s.color ?? C.tp} stroke={C.surface} strokeWidth={2} /> : null; })}
        </g>}
      </svg>
      {hover !== null && <div className="rp-tip" style={{ left: `${(X(hover) / W) * 100}%`, transform: X(hover) > W * 0.7 ? "translateX(-100%)" : "none" }}>
        <div className="rp-tip-h">{data[hover].x} <span>{data[hover].p}</span></div>
        {series.map(s => { const v = data[hover][s.key]; return <div key={s.key}><i style={{ background: typeof v === "number" && v < 0 && s.negColor ? s.negColor : (s.color ?? C.tp) }} />{s.name}<b>{typeof v === "number" ? tf(v) : "—"}</b></div>; })}
      </div>}
    </div>
  );
}

/** Seri açıklaması (legend): ≥2 seri için başlığın altında. */
export function Legend({ series }: { series: S[] }) {
  if (series.length < 2) return null;
  return <div className="rp-legend">{series.map(s => <span key={s.key}><i style={{ background: s.color ?? C.tp, height: s.kind === "bar" ? 10 : 2, marginBottom: s.kind === "bar" ? 0 : 3 }} />{s.name}{s.negColor ? <> <i style={{ background: s.negColor, height: 10 }} />negatif</> : null}</span>)}</div>;
}

/** Küçük çoklu: küçük çizgi, son değer etiketi. */
export function Mini({ data, fmt = fmtAxis, height = 64, color = C.tp, yZero = true, ymax, ymin, endLabel = true }: { data: Pt[]; fmt?: (v: number) => string; height?: number; color?: string; yZero?: boolean; ymax?: number; ymin?: number; endLabel?: boolean }) {
  const [ref, W] = useWidth<HTMLDivElement>(220);
  const vals = data.map(d => d.v).filter((v): v is number => typeof v === "number");
  if (!vals.length) return <div ref={ref} className="rp-mini-empty">veri yok</div>;
  let lo = Math.min(yZero ? 0 : Infinity, ...vals), hi = Math.max(yZero ? 0 : -Infinity, ...vals);
  if (ymax !== undefined) hi = ymax; if (ymin !== undefined) lo = ymin; if (hi === lo) hi = lo + 1;
  const pl = 2, pr = endLabel ? 46 : 8, pt = 6, pb = 4, pw = Math.max(40, W - pl - pr), ph = height - pt - pb, n = data.length, step = n > 1 ? pw / (n - 1) : pw;
  const X = (i: number) => pl + i * step, Y = (v: number) => pt + ph - (v - lo) / (hi - lo) * ph;
  const segs: string[] = []; let cur = "";
  data.forEach((d, i) => { const v = d.v; if (typeof v === "number") cur += `${cur ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; else if (cur) { segs.push(cur); cur = ""; } });
  if (cur) segs.push(cur);
  let li = n - 1; while (li >= 0 && typeof data[li].v !== "number") li--;
  const lv = data[li].v as number;
  return (
    <div ref={ref} className="rp-mini">
      <svg width="100%" viewBox={`0 0 ${W} ${height}`} style={{ display: "block", overflow: "visible" }}>
        {lo <= 0 && hi >= 0 && <line x1={pl} x2={pl + pw} y1={Y(0)} y2={Y(0)} stroke={C.rule} />}
        {segs.map((p, k) => <path key={k} d={p} fill="none" stroke={color} strokeWidth={1.6} strokeLinejoin="round" />)}
        <circle cx={X(li)} cy={Y(lv)} r={3} fill={color} />
        {endLabel && <text x={X(li) + 7} y={Y(lv) + 3.5} style={{ ...T, fill: C.ink, fontSize: 11, fontWeight: 500 }}>{fmt(lv)}</text>}
      </svg>
    </div>
  );
}

/** Anatomi: ortak ölçekte yatay bölümlü çubuklar; bölüm listesi çubuğun altında HTML olarak (sarar).
 *  annotate: son çubuğun üstünde, ilk çubuğun ucundan son çubuğun ucuna ölçü çizgisi ve metin. */
export function Anatomy({ rows, fmt = (v: number) => big(v), annotate }: { rows: { label: string; total: number; parts: { name: string; v: number }[] }[]; fmt?: (v: number) => string; annotate?: string }) {
  const [ref, W] = useWidth<HTMLDivElement>(600);
  const max = Math.max(...rows.map(r => Math.max(r.total, r.parts.reduce((a, b) => a + Math.max(0, b.v), 0))));
  const bh = 30, charW = 6.4;
  const xOf = (r: typeof rows[number]) => r.parts.filter(p => p.v > 0).reduce((a, b) => a + b.v, 0) / max * W;
  return (
    <div className="rp-anatomy">
      {rows.map((r, ri) => {
        const parts = r.parts.filter(p => p.v > 0); let x = 0;
        const last = ri === rows.length - 1 && !!annotate; const top = last ? 32 : 0;
        return <div key={r.label} className="rp-anat-row">
          <div className="rp-anat-lab" style={{ paddingTop: top }}><b>{r.label}</b><span>{fmt(r.total)}</span></div>
          <div ref={ri === 0 ? ref : undefined}>
            <svg width="100%" viewBox={`0 0 ${W} ${bh + top}`} style={{ display: "block", overflow: "visible" }}>
              {last && (() => { const a = xOf(rows[0]), b = xOf(r); return <g>
                <line x1={a} x2={b} y1={20} y2={20} stroke={C.ink2} strokeWidth={1} />
                <line x1={a} x2={a} y1={15} y2={25} stroke={C.ink2} strokeWidth={1} /><line x1={b} x2={b} y1={15} y2={25} stroke={C.ink2} strokeWidth={1} />
                <text x={(a + b) / 2} y={11} textAnchor="middle" style={{ ...T, fill: C.ink, fontSize: 11.5, fontWeight: 500 }}>{annotate}</text>
              </g>; })()}
              {parts.map((p, k) => {
                const w = p.v / max * W; const x0 = x; x += w;
                const txt = `${p.name} ${fmt(p.v)}`; const fits = txt.length * charW + 14 < w;
                return <g key={k}><rect x={x0} y={top} width={Math.max(0.5, w - 1.5)} height={bh} fill={C.steps[Math.min(k, C.steps.length - 1)]} />
                  {fits && <text x={x0 + 7} y={top + 19} style={{ ...T, fontSize: 11.5, fill: k < 2 ? "#fff" : C.ink, fontWeight: 500 }}>{txt}</text>}</g>;
              })}
            </svg>
            <ul className="rp-anat-list">{parts.map((p, k) => <li key={k}><i style={{ background: C.steps[Math.min(k, C.steps.length - 1)] }} />{p.name} <b>{fmt(p.v)}</b></li>)}</ul>
          </div>
        </div>;
      })}
    </div>
  );
}

/** Şelale: başlangıç → deltalar → toplam. */
export function Waterfall({ steps, fmt = (v: number) => fmtNum(v), height = 230 }: { steps: { label: string; v: number; kind: "start" | "delta" | "total" }[]; fmt?: (v: number) => string; height?: number }) {
  const [ref, W] = useWidth<HTMLDivElement>(420);
  let run = 0; const bars = steps.map(s => { if (s.kind === "delta") { const a = run; run += s.v; return { ...s, a, b: run }; } run = s.v; return { ...s, a: 0, b: s.v }; });
  const lo = Math.min(0, ...bars.flatMap(b => [b.a, b.b])), hi = Math.max(0, ...bars.flatMap(b => [b.a, b.b]));
  const ticks = niceTicks(lo, hi, 4), y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const pl = 44, pr = 8, pt = 22, pb = 40, pw = W - pl - pr, ph = height - pt - pb, n = bars.length, slot = pw / n, bw = Math.min(40, slot * 0.6);
  const Y = (v: number) => pt + ph - (v - y0) / (y1 - y0) * ph, X = (i: number) => pl + slot * i + slot / 2;
  return (
    <div ref={ref}>
      <svg width="100%" viewBox={`0 0 ${W} ${height}`} style={{ display: "block", overflow: "visible" }}>
        {ticks.map(t => <g key={t}><line x1={pl} x2={pl + pw} y1={Y(t)} y2={Y(t)} stroke={t === 0 ? C.ink3 : C.rule} /><text x={pl - 6} y={Y(t) + 3.5} textAnchor="end" style={T}>{fmtAxis(t)}</text></g>)}
        {bars.map((b, i) => {
          const top = Math.min(Y(b.a), Y(b.b)), hgt = Math.max(1, Math.abs(Y(b.a) - Y(b.b)));
          const col = b.kind !== "delta" ? C.tp : b.v >= 0 ? C.yp : C.neg;
          const words = b.label.split(" ");
          return <g key={i}>
            {i > 0 && <line x1={X(i - 1) + bw / 2} x2={X(i) - bw / 2} y1={Y(bars[i - 1].b)} y2={Y(bars[i - 1].b)} stroke={C.ink3} strokeWidth={1} />}
            <rect x={X(i) - bw / 2} y={top} width={bw} height={hgt} fill={col} />
            <text x={X(i)} y={top - 6} textAnchor="middle" style={{ ...T, fill: C.ink, fontWeight: 500 }}>{b.kind === "delta" && b.v > 0 ? "+" : ""}{fmt(b.v)}</text>
            {words.map((w, k) => <text key={k} x={X(i)} y={pt + ph + 14 + k * 12} textAnchor="middle" style={{ ...T, fontSize: 10.5 }}>{w}</text>)}
          </g>;
        })}
      </svg>
    </div>
  );
}

/** Vade merdiveni: sol pasif, sağ aktif, ortada kova adı. */
export function Ladder({ rows, fmt = (v: number) => fmtNum(v) }: { rows: { label: string; a: number | null; l: number | null }[]; fmt?: (v: number) => string }) {
  const [ref, W] = useWidth<HTMLDivElement>();
  const max = Math.max(...rows.flatMap(r => [Math.abs(r.a ?? 0), Math.abs(r.l ?? 0)]), 1);
  const mid = W / 2, lab = 92, half = (W - lab) / 2 - 56, rh = 26, gap = 10, h = rows.length * (rh + gap);
  const sx = (v: number) => Math.abs(v) / max * half;
  return (
    <div ref={ref}>
      <svg width="100%" viewBox={`0 0 ${W} ${h + 20}`} style={{ display: "block", overflow: "visible" }}>
        <text x={mid - lab / 2 - 4} y={10} textAnchor="end" style={{ ...T, fontWeight: 600, fill: C.ink }}>Yükümlülükler</text>
        <text x={mid + lab / 2 + 4} y={10} style={{ ...T, fontWeight: 600, fill: C.ink }}>Varlıklar</text>
        {rows.map((r, i) => {
          const y = 20 + i * (rh + gap);
          return <g key={r.label}>
            <text x={mid} y={y + rh / 2 + 4} textAnchor="middle" style={{ ...T, fill: C.ink }}>{r.label}</text>
            {r.l !== null && <><rect x={mid - lab / 2 - 4 - sx(r.l)} y={y} width={sx(r.l)} height={rh} fill={C.yp} /><text x={mid - lab / 2 - 8 - sx(r.l)} y={y + rh / 2 + 4} textAnchor="end" style={{ ...T, fill: C.ink }}>{fmt(r.l)}</text></>}
            {r.a !== null && <><rect x={mid + lab / 2 + 4} y={y} width={sx(r.a)} height={rh} fill={C.tp} /><text x={mid + lab / 2 + 8 + sx(r.a)} y={y + rh / 2 + 4} style={{ ...T, fill: C.ink }}>{fmt(r.a)}</text></>}
          </g>;
        })}
      </svg>
    </div>
  );
}

/** Halter: iki dönem arası pay değişimi. */
export function Dumbbell({ rows, fmt = fmtPctAxis(0), labels }: { rows: { label: string; a: number | null; b: number | null }[]; fmt?: (v: number) => string; labels: [string, string] }) {
  const [ref, W] = useWidth<HTMLDivElement>();
  const max = Math.max(...rows.flatMap(r => [r.a ?? 0, r.b ?? 0]), 0.01);
  const pl = 190, pr = 60, pw = W - pl - pr, rh = 30, h = rows.length * rh + 24;
  const X = (v: number) => pl + v / max * pw;
  return (
    <div ref={ref}>
      <svg width="100%" viewBox={`0 0 ${W} ${h}`} style={{ display: "block", overflow: "visible" }}>
        <text x={pl} y={10} style={T}>0</text><text x={pl + pw} y={10} textAnchor="end" style={T}>{fmt(max)}</text>
        {rows.map((r, i) => {
          const y = 24 + i * rh + rh / 2;
          return <g key={r.label}>
            <text x={pl - 12} y={y + 4} textAnchor="end" style={{ ...T, fill: C.ink, fontSize: 12 }}>{r.label}</text>
            <line x1={pl} x2={pl + pw} y1={y} y2={y} stroke={C.rule} />
            {r.a !== null && r.b !== null && <line x1={X(r.a)} x2={X(r.b)} y1={y} y2={y} stroke={C.ink3} strokeWidth={2} />}
            {r.a !== null && <circle cx={X(r.a)} cy={y} r={5} fill={C.surface} stroke={C.ink3} strokeWidth={2} />}
            {r.b !== null && <circle cx={X(r.b)} cy={y} r={5.5} fill={C.tp} />}
            {r.b !== null && <text x={X(Math.max(r.a ?? 0, r.b)) + 10} y={y + 4} style={{ ...T, fill: C.ink }}>{fmt(r.b)}</text>}
          </g>;
        })}
      </svg>
      <div className="rp-legend"><span><i style={{ background: C.surface, border: `2px solid ${C.ink3}`, height: 8, width: 8, borderRadius: 8 }} />{labels[0]}</span><span><i style={{ background: C.tp, height: 10, width: 10, borderRadius: 10 }} />{labels[1]}</span></div>
    </div>
  );
}
