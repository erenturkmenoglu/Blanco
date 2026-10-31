import Nav from "@/components/Nav";
import { CcyToggle } from "@/components/Ccy";
import { D } from "@/lib/data";

export default function PanelLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="panel">
      <header>
        <span className="brand">DBTR</span>
        <span className="sub">Deutsche Bank A.Ş., solo, {D.periods[0].slice(0, 4)}–{D.periods[D.periods.length - 1]}</span>
        <Nav />
        <span className="spacer" />
        <CcyToggle />
      </header>
      <main>{children}</main>
      <footer className="note">Kaynak: KAP bildirimleri (ana tablolar), TBB Ortak Veri Seti banka kitapları (dipnotlar), TCMB kurları. Nominal TL; TMS 29 uygulanmamış. Üretim: {D.meta.generated}.</footer>
    </div>
  );
}
