"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  ["/", "Genel Bakış"], ["/bankalar", "Bankalar"], ["/karsilastirmalar", "Karşılaştırmalar"],
  ["/veri-kaynaklari", "Veri Kaynakları"], ["/veri-guncelleme-durumu", "Veri Güncelleme Durumu"],
];

export default function Nav() {
  const p = usePathname();
  return (
    <nav>
      {ITEMS.map(([href, label]) => (
        <Link key={href} href={href} className={p === href ? "active" : ""}>{label}</Link>
      ))}
    </nav>
  );
}
