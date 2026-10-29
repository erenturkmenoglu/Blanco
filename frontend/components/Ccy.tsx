"use client";
import { createContext, useContext, useEffect, useState } from "react";
import type { Ccy } from "@/lib/data";

const Ctx = createContext<{ ccy: Ccy; setCcy: (c: Ccy) => void }>({ ccy: "TL", setCcy: () => {} });

export function CcyProvider({ children }: { children: React.ReactNode }) {
  const [ccy, set] = useState<Ccy>("TL");
  useEffect(() => { try { const s = localStorage.getItem("dbtr.ccy") as Ccy | null; if (s === "TL" || s === "USD" || s === "EUR") set(s); } catch {} }, []);
  const setCcy = (c: Ccy) => { set(c); try { localStorage.setItem("dbtr.ccy", c); } catch {} };
  return <Ctx.Provider value={{ ccy, setCcy }}>{children}</Ctx.Provider>;
}
export const useCcy = () => useContext(Ctx);

export function CcyToggle() {
  const { ccy, setCcy } = useCcy();
  return (
    <span className="ccy">
      {(["TL", "USD", "EUR"] as Ccy[]).map(c => <button key={c} className={c === ccy ? "on" : ""} onClick={() => setCcy(c)}>{c}</button>)}
    </span>
  );
}
