import "./globals.css";
import type { Metadata } from "next";
import Nav from "@/components/Nav";
import { CcyProvider, CcyToggle } from "@/components/Ccy";
import { D } from "@/lib/data";

export const metadata: Metadata = { title: "DBTR — Deutsche Bank A.Ş. finansallar", description: "KAP bildirimleri + TBB dipnotlarından kurulan Deutsche Bank A.Ş. (solo) finansal veri tabanı ve analiz paneli" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <CcyProvider>
          <header>
            <span className="brand">DBTR</span>
            <span className="sub">Deutsche Bank A.Ş. · solo · {D.periods[0].slice(0, 4)}–{D.periods[D.periods.length - 1]}</span>
            <Nav />
            <span className="spacer" />
            <CcyToggle />
          </header>
          <main>{children}</main>
          <footer className="note">Kaynak: KAP bildirimleri (ana tablolar), TBB Ortak Veri Seti banka kitapları (dipnotlar), TCMB kurları. Nominal TL; TMS 29 uygulanmamış. Üretim: {D.meta.generated}.</footer>
        </CcyProvider>
      </body>
    </html>
  );
}
