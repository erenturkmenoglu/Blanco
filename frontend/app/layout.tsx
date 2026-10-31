import "@fontsource-variable/archivo/wdth.css";
import "@fontsource-variable/source-serif-4/opsz.css";
import "./globals.css";
import type { Metadata } from "next";
import { CcyProvider } from "@/components/Ccy";

export const metadata: Metadata = { title: "Bilanço ve gölgesi — Deutsche Bank A.Ş. solo finansallar", description: "KAP bildirimleri ve TBB dipnotlarından kurulan Deutsche Bank A.Ş. (konsolide olmayan) finansal veri tabanı: tek sayfalık rapor ve analiz paneli" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body><CcyProvider>{children}</CcyProvider></body>
    </html>
  );
}
