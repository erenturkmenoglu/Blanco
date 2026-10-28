/** Her grafik/tablo altında: veri dönemi, birim, kaynak, son güncelleme, hesaplama yöntemi (§11). */
export default function Provenance({ period, unit, source, sourceUrl, updated, method, status, limitations }:
  { period?: string; unit?: string; source?: string; sourceUrl?: string | null; updated?: string | null; method?: string; status?: string; limitations?: string | null }) {
  return (
    <div className="prov">
      {period && <>Dönem: {period} · </>}
      {unit && <>Birim: {unit} · </>}
      {source && <>Kaynak: {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer">{source}</a> : source} · </>}
      {updated && <>Son güncelleme: {new Date(updated).toLocaleString("tr-TR")} · </>}
      {method && <>Yöntem: {method} · </>}
      {status && <span className={`status ${status}`}>{status}</span>}
      {limitations && <div>Sınırlama: {limitations}</div>}
    </div>
  );
}
