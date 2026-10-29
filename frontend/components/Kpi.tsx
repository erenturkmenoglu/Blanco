export function Kpi({ label, value, delta, note }: { label: string; value: string; delta?: string; note?: string }) {
  return <div className="card"><div className="lbl">{label}</div><div className="kpi">{value}</div>{delta && <div className="dlt">{delta}</div>}{note && <div className="dlt">{note}</div>}</div>;
}
