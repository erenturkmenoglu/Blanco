"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useCcy } from "@/components/Ccy";
import type { Ccy } from "@/lib/data";

export type Chapter = { id: string; n: string; title: string };

export function Spine({ chapters }: { chapters: Chapter[] }) {
  const [active, setActive] = useState(chapters[0]?.id);
  const { ccy, setCcy } = useCcy();
  useEffect(() => {
    const els = chapters.map(c => document.getElementById(c.id)).filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver(es => {
      const vis = es.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (vis[0]) setActive(vis[0].target.id);
    }, { rootMargin: "-20% 0px -65% 0px", threshold: 0 });
    els.forEach(el => io.observe(el));
    return () => io.disconnect();
  }, [chapters]);
  return (
    <aside className="rp-spine">
      <div className="rp-spine-in">
        <div className="rp-spine-brand">Deutsche Bank A.Ş.<small>Konsolide olmayan finansallar</small></div>
        <ol>
          {chapters.map(c => <li key={c.id} className={active === c.id ? "on" : ""}><a href={`#${c.id}`}><span>{c.n}</span>{c.title}</a></li>)}
        </ol>
        <div className="rp-spine-tools">
          <div className="rp-seg" role="group" aria-label="Para birimi">
            {(["TL", "USD", "EUR"] as Ccy[]).map(c => <button key={c} className={c === ccy ? "on" : ""} onClick={() => setCcy(c)} aria-pressed={c === ccy}>{c}</button>)}
          </div>
          <button className="rp-btn" onClick={() => window.print()}>PDF olarak kaydet</button>
          <Link className="rp-link" href="/panel">Ayrıntılı panel</Link>
        </div>
      </div>
    </aside>
  );
}
