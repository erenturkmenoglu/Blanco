"""Extract footnote metrics (SYR, LCR, NSFR, avg interest rates, remaining maturity, repricing, deposit maturity, NPL,
branches/employees) from the TBB bank workbooks for Deutsche Bank A.Ş. (Mart 2026, Haziran 2026) + DT13."""
import xlrd, glob, re, json, openpyxl
import pandas as pd
from datetime import datetime

OUT = '/home/claude/dbtr/dipnot.pkl'
recs = []
def add(pe, code, value, unit, table, src, bucket=None, note=''):
    if value is None or value == '': return
    try: v = float(value)
    except: return
    recs.append(dict(p_end=pe, code=code, bucket=bucket, value=v, unit=unit, table=table, source=src, note=note))

def rows_of(s):
    return [[s.cell_value(r, c) for c in range(s.ncols)] for r in range(s.nrows)]

for f in sorted(glob.glob('/home/claude/dbtr/tbb/*/*.xls')):
    wb = xlrd.open_workbook(f)
    cov = wb.sheet_by_name('kapak-cover')
    pe = datetime.strptime(cov.cell_value(1, 11), '%d.%m.%Y')
    unit_txt = cov.cell_value(3, 11)
    scale = 1e-3 if 'Bin' in unit_txt else 1.0   # -> mn TL
    src = f'TBB banka kitabı {pe:%d.%m.%Y} ({unit_txt})'
    prev = datetime(pe.year - 1, 12, 31)
    M = rows_of(wb.sheet_by_name('malibünye1'))
    def find(label, start=0, col=0):
        for i in range(start, len(M)):
            if str(M[i][col]).strip().startswith(label): return i
        return None
    # --- SYR (cari only)
    i = find('Toplam Özkaynak ( Ana sermaye'); add(pe, 'regulatory_equity', M[i][1] * scale, 'mn TL', 'Madde 7 Özkaynak', src)
    i = find('Toplam Risk Ağırlıklı Tutarlar'); add(pe, 'risk_weighted_assets', M[i][1] * scale, 'mn TL', 'Madde 7 Özkaynak', src)
    i = find('Çekirdek Sermaye Yeterliliği Oranı'); add(pe, 'cet1_ratio', M[i][1], '%', 'Madde 7 Özkaynak', src)
    i = find('Ana Sermaye Yeterliliği Oranı'); add(pe, 'tier_1_ratio', M[i][1], '%', 'Madde 7 Özkaynak', src)
    i = find('Sermaye Yeterliliği Oranı (%)'); add(pe, 'capital_adequacy_ratio', M[i][1], '%', 'Madde 7 Özkaynak', src)
    i = find('Çekirdek Sermaye Toplamı'); add(pe, 'cet1_capital', M[i][1] * scale, 'mn TL', 'Madde 7 Özkaynak', src)
    # --- avg interest rates (cari / önceki) columns EURO USD Yen TL
    i0 = find('Parasal Finansal Araçlara Uygulanan Ortalama Faiz')
    for blk, per in ((i0, pe), (find('Parasal Finansal Araçlara Uygulanan Ortalama Faiz', i0 + 1), prev)):
        for lab, code in (('Verilen Krediler', 'loan_interest'), ('Diğer Mevduat', 'deposit_interest'), ('Bankalar Mevduatı', 'bank_deposit_interest'),
                          ('Diğer Mali Kuruluşlardan', 'funds_borrowed_interest'), ('Bankalar', 'due_from_banks_interest'),
                          ('Gerçeğe Uygun Değer Farkı Kar', 'securities_fvtpl_interest'), ('Gerçeğe Uygun Değer Farkı Diğer', 'securities_fvoci_interest'),
                          ('Nakit Değerler', 'cash_cb_interest')):
            j = find(lab, blk)
            if j is None or j > blk + 25: continue
            for ci, ccy in ((1, 'eur'), (2, 'usd'), (4, 'tl')):
                add(per, f'{code}_{ccy}', M[j][ci], '%', 'Madde 11 Faiz oranı riski – ortalama faiz', src, note='stok ortalama uygulanan oran')
    # --- LCR (cari / önceki): rows after 'Cari Dönem ' header with TP+YP / YP
    i0 = find('Likidite karşılama oranı')
    for hdr, per in (('Cari Dönem', pe), ('Önceki Dönem', prev)):
        h = find(hdr, i0)
        j = find('LİKİDİTE KARŞILAMA ORANI', h)
        add(per, 'liquidity_coverage_ratio', M[j][3], '%', 'Madde 13 LKO', src, note='3 aylık basit ortalama, TP+YP')
        add(per, 'liquidity_coverage_ratio_fx', M[j][4], '%', 'Madde 13 LKO', src, note='YP')
        k = find('TOPLAM YÜKSEK KALİTELİ', h); add(per, 'hqla_stock', M[k][3] * scale, 'mn TL', 'Madde 13 LKO', src)
        k = find('TOPLAM NET NAKİT ÇIKIŞLARI', h); add(per, 'net_cash_outflows', M[k][3] * scale, 'mn TL', 'Madde 13 LKO', src)
        i0 = j
    # --- remaining maturity (liquidity): header row with 'Vadesiz' then Cari block
    i0 = find('Aktif ve Pasif Kalemlerin Kalan Vadelerine')
    buckets = ['demand', '0_1m', '1_3m', '3_12m', '1_5y', 'over_5y', 'unallocated', 'total']
    cur = find('Cari Dönem', i0)
    for lab, code in (('Toplam Varlıklar', 'rm_total_assets'), ('Toplam Yükümlülükler', 'rm_total_liabilities'), ('Likidite Açığı', 'rm_liquidity_gap'),
                      ('Verilen Krediler', 'rm_loans'), ('Diğer Mevduat', 'rm_other_deposits'), ('Bankalar Mevduatı', 'rm_bank_deposits'),
                      ('Diğer Mali Kuruluşlar', 'rm_funds_borrowed'), ('Nakit Değerler', 'rm_cash_cb'), ('Bankalar ', 'rm_due_from_banks'),
                      ('Net Bilanço Dışı', 'rm_net_off_bs'), ('Türev Finansal Araçlardan Alacaklar', 'rm_deriv_receivables'), ('Türev Finansal Araçlardan Borçlar', 'rm_deriv_payables')):
        j = find(lab, cur)
        if j is None or j > cur + 30: continue
        for bi, b in enumerate(buckets):
            add(pe, code, (M[j][bi + 1] or 0) * scale, 'mn TL', 'Madde 13 Kalan vade', src, bucket=b)
    pr = find('Önceki Dönem', cur)
    for lab, code in (('Toplam Aktifler', 'rm_total_assets'), ('Toplam Yükümlülükler', 'rm_total_liabilities'), ('Likidite Açığı', 'rm_liquidity_gap')):
        j = find(lab, pr)
        if j is None or j > pr + 10: continue
        for bi, b in enumerate(buckets):
            add(prev, code, (M[j][bi + 1] or 0) * scale, 'mn TL', 'Madde 13 Kalan vade', src, bucket=b)
    # --- NSFR
    i0 = find('Net İstikrarlı Fonlama Oranı:')
    j = find('Net İstikrarlı Fonlama Oranı (%)', i0); add(pe, 'nsfr', M[j][5], '%', 'Madde 13 NSFR', src)
    k = find('Mevcut İstikrarlı Fon Toplamı', i0) or find('Toplam Mevcut İstikrarlı Fon', i0)
    j2 = find('Net İstikrarlı Fonlama Oranı (%)', j + 1); add(prev, 'nsfr', M[j2][5], '%', 'Madde 13 NSFR', src)
    # --- repricing (faize duyarlılık): header 'Cari Dönem Sonu' with '1 Aya Kadar'
    rb = ['0_1m', '1_3m', '3_12m', '1_5y', 'over_5y', 'non_interest', 'total']
    for hdr, per in (('Cari Dönem Sonu', pe), ('Önceki Dönem Sonu', prev)):
        h = None
        for i in range(len(M)):
            if str(M[i][0]).strip() == hdr and '1 Aya Kadar' in str(M[i][1]): h = i; break
        if h is None: continue
        for lab, code in (('Toplam Varlıklar', 'rp_total_assets'), ('Toplam Yükümlülükler', 'rp_total_liabilities'), ('Verilen Krediler', 'rp_loans'),
                          ('Diğer Mevduat', 'rp_other_deposits'), ('Bankalar Mevduatı', 'rp_bank_deposits'), ('Diğer Mali Kuruluşlar', 'rp_funds_borrowed'),
                          ('Bilanço İçi Uzun Pozisyon', 'rp_on_bs_long'), ('Bilanço İçi Kısa Pozisyon', 'rp_on_bs_short'), ('Toplam Pozisyon', 'rp_total_position'),
                          ('Nazım Hesaplardaki Uzun', 'rp_off_bs_long'), ('Nazım Hesaplardaki Kısa', 'rp_off_bs_short')):
            j = find(lab, h)
            if j is None or j > h + 30: continue
            for bi, b in enumerate(rb):
                add(per, code, (M[j][bi + 1] or 0) * scale, 'mn TL', 'Madde 11 Faize duyarlılık (yeniden fiyatlama)', src, bucket=b)
    # --- deposit maturity structure (pasif1)
    P = rows_of(wb.sheet_by_name('pasif1'))
    db = ['demand', 'notice_7d', '0_1m', '1_3m', '3_6m', '6_12m', 'over_1y', 'accumulating', 'total']
    for hdr, per in (('Cari Dönem', pe), ('Önceki Dönem', prev)):
        h = None
        for i in range(len(P)):
            if str(P[i][0]).strip() == hdr and 'Vadesiz' in str(P[i][1]): h = i; break
        j = None
        for i in range(h, h + 25):
            if str(P[i][0]).strip() == 'Toplam': j = i; break
        for bi, b in enumerate(db):
            add(per, 'dep_maturity_total', (P[j][bi + 1] or 0) * scale, 'mn TL', 'Pasif 2.a.1.i Mevduat vade yapısı', src, bucket=b)
        for lab, code in (('Döviz Tevdiat', 'dep_maturity_fx'), ('Tic. Kur.', 'dep_maturity_commercial'), ('Bankalar Mevduatı', 'dep_maturity_banks')):
            for i in range(h, j):
                if str(P[i][0]).strip().startswith(lab):
                    for bi, b in enumerate(db):
                        add(per, code, (P[i][bi + 1] or 0) * scale, 'mn TL', 'Pasif 2.a.1.i Mevduat vade yapısı', src, bucket=b)
        # derived demand/time
        tot = [(P[j][bi + 1] or 0) * scale for bi in range(9)]
        add(per, 'demand_deposits', tot[0] + tot[1], 'mn TL', 'Pasif 2.a.1.i (vadesiz + 7 gün ihbarlı)', src)
        add(per, 'time_deposits', sum(tot[2:8]), 'mn TL', 'Pasif 2.a.1.i (1 aya kadar … birikimli)', src)
    # --- NPL (aktif1 2.f.10.ii Dönem Sonu Bakiyesi)
    A = rows_of(wb.sheet_by_name('aktif1'))
    for i in range(len(A)):
        if str(A[i][0]).startswith('2.f.10.ii'):
            for k in range(i, i + 25):
                if str(A[k][0]).strip() == 'Dönem Sonu Bakiyesi':
                    add(pe, 'npl_amount', sum((A[k][c] or 0) for c in (1, 2, 3)) * scale, 'mn TL', 'Aktif 2.f.10.ii Donuk alacak hareketleri', src)
                if str(A[k][0]).strip() == 'Önceki Dönem Sonu Bakiyesi':
                    add(prev, 'npl_amount', sum((A[k][c] or 0) for c in (1, 2, 3)) * scale, 'mn TL', 'Aktif 2.f.10.ii Donuk alacak hareketleri', src)
                if str(A[k][0]).strip() == 'Karşılık (-)':
                    add(pe, 'loan_loss_provisions', sum((A[k][c] or 0) for c in (1, 2, 3)) * scale, 'mn TL', 'Aktif 2.f.10.ii', src)
            break

# --- DT13 branches/employees
wb = openpyxl.load_workbook('/home/claude/dbtr/tbb/dt13.xlsx', data_only=True)
ws = wb['şube ve çalışan']
hdr = None
for row in ws.iter_rows(values_only=True):
    if row[0] and 'Deutsche' in str(row[0]):
        # columns: branches (Dec-2025, Mar-2026, Jun-2026), employees (Dec-2025, Mar-2026, Jun-2026) -- verify with header row
        vals = list(row[1:7])
        for pe, b, e in zip((datetime(2025, 6, 30), datetime(2025, 12, 31), datetime(2026, 6, 30)), vals[:3], vals[3:]):
            add(pe, 'branch_count', b, 'adet', 'TBB DT13 Tablo 4', 'TBB Banka, Şube ve Çalışan Sayıları Haziran 2026')
            add(pe, 'employee_count', e, 'adet', 'TBB DT13 Tablo 4', 'TBB Banka, Şube ve Çalışan Sayıları Haziran 2026')
# header check
for row in ws.iter_rows(min_row=1, max_row=8, values_only=True):
    if any(isinstance(c, (int, float, str)) and ('2025' in str(c) or 'Aralık' in str(c) or 'Haziran' in str(c)) for c in row[1:]): print('DT13 header:', row)

df = pd.DataFrame(recs)
df = df.drop_duplicates(['p_end', 'code', 'bucket'], keep='first')
df.to_pickle(OUT)
pd.set_option('display.width', 220)
print(df[df.bucket.isna()].pivot_table(index='code', columns='p_end', values='value', aggfunc='first').to_string())
print(df[df.bucket.notna()].groupby(['code', 'p_end']).size().to_string())
