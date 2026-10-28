import "./globals.css";
import type { Metadata } from "next";
import Nav from "@/components/Nav";

export const metadata: Metadata = { title: "Bilanço", description: "Otomatik finansal analiz platformu — Bankalar modülü" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <header>
          <span className="brand">Bilanço</span>
          <Nav />
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
