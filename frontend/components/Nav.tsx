"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [["/", "Genel Bakış"], ["/bilanco", "Bilanço"], ["/gelir-tablosu", "Gelir Tablosu"], ["/nazim", "Nazım & Türev"], ["/oranlar", "Oranlar"], ["/dipnot", "Dipnotlar"], ["/tablolar", "Tablolar"], ["/veri", "Veri & Kalite"]];

export default function Nav() {
  const p = usePathname();
  return <nav>{ITEMS.map(([href, label]) => <Link key={href} href={href} className={p === href ? "active" : ""}>{label}</Link>)}</nav>;
}
