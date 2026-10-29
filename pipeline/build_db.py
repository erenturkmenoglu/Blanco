"""Build normalized long DB + checks from kap_long.pkl, write DBTR_KAP_DB.xlsx."""
import pandas as pd, numpy as np, re
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

df = pd.read_pickle('/home/claude/dbtr/kap_long.pkl')

# ---------- label normalisation ----------
def norm_label(s):
    s = s.replace('Hise Başına Kar', 'Hisse Başına Kar').replace('Hisse Başın Kar', 'Hisse Başına Kar')
    s = re.sub(r'\(\s*-\s*\)', '(-)', s)
    s = re.sub(r'\(\s*Net\s*\)', '(Net)', s)
    s = re.sub(r'\(\s*\+/-\s*\)', '(+/-)', s)
    s = re.sub(r'\(\s*Zarar\s*\)', '(Zarar)', s)
    s = re.sub(r'\(\s*Kayıpları\s*\)', '(Kayıpları)', s)
    s = re.sub(r'\(\s+', '(', s); s = re.sub(r'\s+\)', ')', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s
df['label'] = df['label'].map(norm_label)

# ---------- indent level & hierarchical path ----------
base = df.groupby('stmt').x0.transform('min')
df['level'] = ((df.x0 - base) / 11.3).round().fillna(0).astype(int)
df.loc[(df.stmt == 'BS') & (df.label == 'YÜKÜMLÜLÜKLER TOPLAMI'), 'level'] = 1
df.loc[(df.stmt == 'PL') & df.label.str.startswith('Hisse Başına'), 'level'] = 1
df.loc[(df.stmt == 'PL') & df.label.str.startswith('Hisse Başına'), 'label'] = 'Hisse Başına Kar'

rows = df.drop_duplicates(['file_id', 'stmt', 'row_order']).sort_values(['file_id', 'stmt', 'row_order'])
paths = {}
for (fid, st), g in rows.groupby(['file_id', 'stmt'], sort=False):
    stack = []
    for _, r in g.iterrows():
        lvl = r.level
        stack = stack[:lvl]
        stack.append(r.label)
        paths[(fid, st, r.row_order)] = ' > '.join(stack)
df['path'] = [paths[(a, b, c)] for a, b, c in zip(df.file_id, df.stmt, df.row_order)]

# duplicate labels inside same parent (e.g. 'Hisse Başına Kar (Zarar)' header x3) -> suffix
dups = df.drop_duplicates(['file_id','stmt','row_order']).groupby(['file_id','stmt','path']).row_order.transform('rank')
# (we keep as-is; only EPS header rows are empty anyway)

# ---------- column parsing ----------
def parse_col(r):
    c = r.col; st = r.stmt
    role = 'Cari' if c.startswith('Cari') else ('Önceki' if c.startswith('Önceki') else None)
    if st in ('BS', 'OBS'):
        m = re.search(r'(\d{2}\.\d{2}\.\d{4}) \| (TP|YP|Toplam)', c)
        return pd.Series(dict(role=role, ccy=m.group(2), p_start=None, p_end=datetime.strptime(m.group(1), '%d.%m.%Y'), basis='POINT'))
    if st in ('PL', 'OCI', 'CF'):
        m = re.search(r'(\d{2}\.\d{2}\.\d{4}) - (\d{2}\.\d{2}\.\d{4})', c)
        basis = 'Q3M' if '3 Aylık' in c else 'YTD'
        return pd.Series(dict(role=role, ccy='Toplam', p_start=datetime.strptime(m.group(1), '%d.%m.%Y'), p_end=datetime.strptime(m.group(2), '%d.%m.%Y'), basis=basis))
    if st == 'EQ':
        b = r.eq_block or ''
        role = 'Cari' if b.startswith('Cari') else 'Önceki'
        m = re.search(r'(\d{2}\.\d{2}\.\d{4}) - (\d{2}\.\d{2}\.\d{4})', b)
        return pd.Series(dict(role=role, ccy='Toplam', p_start=datetime.strptime(m.group(1), '%d.%m.%Y'), p_end=datetime.strptime(m.group(2), '%d.%m.%Y'), basis='YTD'))
df = pd.concat([df, df.apply(parse_col, axis=1)], axis=1)

# equity: component name shortened
EQ_SHORT = {
    'Ödenmiş Sermaye': 'Ödenmiş Sermaye', 'Diğer Sermaye Yedekleri': 'Diğer Sermaye Yedekleri',
    'Kar Yedekleri': 'Kar Yedekleri', 'Geçmiş Dönem Karı / (Zararı)': 'Geçmiş Dönem K/Z',
    'Dönem Net Kar veya Zararı': 'Dönem Net K/Z', 'Azınlık Payları Hariç Toplam Özkaynak': 'Azınlık Hariç Toplam',
    'Azınlık Payları': 'Azınlık Payları', 'Toplam Özkaynak': 'Toplam Özkaynak'}
def eq_comp(c):
    if c in EQ_SHORT: return EQ_SHORT[c]
    if 'Sınıflandırılmayacak' in c: return 'OCI Birikmiş (Yeniden Sınıflandırılmayacak)'
    if 'Sınıflandırılacak' in c: return 'OCI Birikmiş (Yeniden Sınıflandırılacak)'
    return c
df['eq_component'] = np.where(df.stmt == 'EQ', df.col.map(eq_comp), '')

# ---------- units ----------
df['value_mn'] = np.where(df.is_eps, df.value, df.value * df.unit / 1e6)
df['value_unit'] = np.where(df.is_eps, 'TL/hisse', 'mn TL')

# ---------- series key ----------
df['series_key'] = np.where(df.stmt == 'EQ',
                            df.stmt + '|' + df.path + '|' + df.eq_component,
                            df.stmt + '|' + df.ccy + '|' + df.path)
df['period_label'] = df.p_end.dt.strftime('%Y-%m-%d')
df['filing'] = df.year.astype(str) + 'Q' + df.quarter.astype(str)

# ---------- preferred observation (Cari beats Önceki; later filing beats earlier for same role) ----------
df = df.sort_values(['series_key', 'p_end', 'basis', 'role', 'year', 'quarter'])
df['role_rank'] = (df.role == 'Önceki').astype(int)
obs = df[df.value.notna()].copy()
obs = obs.sort_values(['series_key', 'basis', 'p_end', 'role_rank', 'year', 'quarter'])
first = obs.drop_duplicates(['series_key', 'basis', 'p_end'], keep='first')
df['use'] = 0
df.loc[first.index, 'use'] = 1

# ---------- checks ----------
# 1. restatement: Önceki vs original Cari
cari = obs[obs.role == 'Cari'][['series_key', 'basis', 'p_end', 'value_mn', 'filing']].rename(columns={'value_mn': 'orig_cari', 'filing': 'orig_filing'})
onc = obs[obs.role == 'Önceki'][['series_key', 'basis', 'p_end', 'value_mn', 'filing']].rename(columns={'value_mn': 'onceki_val', 'filing': 'later_filing'})
rest = onc.merge(cari, on=['series_key', 'basis', 'p_end'])
rest['diff'] = rest.onceki_val - rest.orig_cari
rest = rest[rest['diff'].abs() > 0.0005]
# 2. BS identity & TP+YP=Toplam
u = df[df.use == 1]
bs = u[(u.stmt == 'BS')]
chk = []
for pe, g in bs.groupby('p_end'):
    def v(path, ccy):
        x = g[(g.path == path) & (g.ccy == ccy)].value_mn
        return float(x.iloc[0]) if len(x) else np.nan
    a = v('VARLIKLAR > VARLIKLAR TOPLAMI', 'Toplam'); l = v('YÜKÜMLÜLÜKLER > YÜKÜMLÜLÜKLER TOPLAMI', 'Toplam')
    chk.append(dict(period=pe.strftime('%Y-%m-%d'), check='Aktif = Pasif (Toplam)', lhs=a, rhs=l, diff=a - l))
    # tp+yp
    g2 = g.pivot_table(index='path', columns='ccy', values='value_mn', aggfunc='first')
    g2 = g2.fillna(0)
    bad = g2[(g2['TP'] + g2['YP'] - g2['Toplam']).abs() > 0.5]
    chk.append(dict(period=pe.strftime('%Y-%m-%d'), check='TP+YP=Toplam, satır sayısı sapan', lhs=len(g2), rhs=len(bad), diff=len(bad)))
pl = u[(u.stmt == 'PL') & (u.basis == 'YTD')]
for pe, g in pl.groupby('p_end'):
    def v(path):
        x = g[g.path == path].value_mn
        return float(x.iloc[0]) if len(x) else np.nan
    ni = v('GELİR VE GİDER KALEMLERİ > DÖNEM NET KARI VEYA ZARARI')
    bsni = bs[(bs.p_end == pe) & (bs.ccy == 'Toplam') & (bs.path.str.endswith('Dönem Net Kâr veya Zararı'))].value_mn
    bsni = float(bsni.iloc[0]) if len(bsni) else np.nan
    chk.append(dict(period=pe.strftime('%Y-%m-%d'), check='K/Z Dönem Net Karı = Bilanço Dönem Net Karı', lhs=ni, rhs=bsni, diff=ni - bsni))
checks = pd.DataFrame(chk)

# 3. PL Q3M reported vs derived from YTD
q3 = u[(u.stmt == 'PL') & (u.basis == 'Q3M')][['series_key', 'p_end', 'value_mn']].rename(columns={'value_mn': 'reported_3m'})
ytd = u[(u.stmt == 'PL') & (u.basis == 'YTD')][['series_key', 'p_end', 'value_mn']]
ytd_prev = ytd.copy(); ytd_prev['p_end'] = ytd_prev.p_end + pd.offsets.QuarterEnd(1)
ytd_prev = ytd_prev[ytd_prev.p_end.dt.month != 3]
der = ytd.merge(ytd_prev.rename(columns={'value_mn': 'prev_ytd'}), on=['series_key', 'p_end'])
der['derived_3m'] = der.value_mn - der.prev_ytd
q3c = q3.merge(der[['series_key', 'p_end', 'derived_3m']], on=['series_key', 'p_end'])
q3c['diff'] = q3c.reported_3m - q3c.derived_3m
q3c = q3c[q3c['diff'].abs() > 0.0005]

df.to_pickle('/home/claude/dbtr/kap_db.pkl')
rest.to_pickle('/home/claude/dbtr/restatements.pkl'); checks.to_pickle('/home/claude/dbtr/checks.pkl'); q3c.to_pickle('/home/claude/dbtr/q3c.pkl')
print('restatements', len(rest)); print(checks.to_string()); print('q3m diffs', len(q3c)); print(q3c.head(20).to_string())
print(rest.head(30).to_string())
