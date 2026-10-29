"""Parse Deutsche Bank A.Ş. KAP 'Banka Finansal Rapor' PDFs into a long-format table."""
import pdfplumber, glob, re, os, sys, json
import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/dbtr/kap_long.pkl'

STMT_MAP = [
    ('Bilanço (Finansal Durum', 'BS'),
    ('NAZIM HESAPLAR', 'OBS'),
    ('Kar veya Zarar ve Diğer Kapsamlı', 'OCI'),
    ('Kar veya Zarar Tablosu', 'PL'),
    ('Nakit Akış Tablosu', 'CF'),
    ('Özkaynaklar Değişim', 'EQ'),
]
TS = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}

def stmt_of(first_line):
    for k, v in STMT_MAP:
        if first_line.startswith(k):
            return v
    return None

def to_num(s):
    if s is None: return None
    s = s.strip().replace(' ', '')
    if s in ('', '-'): return None
    neg = s.startswith('-') or (s.startswith('(') and s.endswith(')'))
    s = s.strip('()').lstrip('-')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace('.', '')
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v

def clean(s):
    if s is None: return ''
    return re.sub(r'\s+', ' ', s.replace('\n', ' ')).strip()

def parse_file(path):
    fid = os.path.basename(path).replace('.pdf', '')
    recs = []
    with pdfplumber.open(path) as pdf:
        p0 = pdf.pages[0].extract_text()
        m = re.search(r'(\d{4}) - (\d)\. 3 Aylık', p0)
        year, q = int(m.group(1)), int(m.group(2))
        m2 = re.search(r'yayınlanma tarihi ve saati: (\d{2}\.\d{2}\.\d{4})', p0)
        pubdate = m2.group(1) if m2 else None
        unit = None
        # audit
        p1 = pdf.pages[1].extract_text() or ''
        audit_firm = re.search(r'Bağımsız Denetim Kuruluşu (.+)', p1)
        audit_type = re.search(r'Denetim Türü (.+)', p1)
        audit_res = re.search(r'Denetim Sonucu (.+)', p1)
        meta = dict(file_id=fid, year=year, quarter=q, pub_date=pubdate,
                    audit_firm=audit_firm.group(1).strip() if audit_firm else None,
                    audit_type=audit_type.group(1).strip() if audit_type else None,
                    audit_result=audit_res.group(1).strip() if audit_res else None)
        stmt = None; cols = None; row_order = 0; eq_block = None
        x0_levels = {}
        for pi, page in enumerate(pdf.pages):
            text = page.extract_text() or ''
            first = text.split('\n')[0] if text else ''
            s = stmt_of(first)
            if s:
                stmt = s; cols = None; row_order = 0; eq_block = None
                mu = re.search(r'Sunum Para Birimi ([\d\.]+) TL', text)
                unit = int(mu.group(1).replace('.', '')) if mu else unit
            if stmt is None:
                continue
            tables = page.find_tables(TS)
            for tb in tables:
                rows = tb.extract()
                for ri, row in enumerate(rows):
                    cells = [clean(c) if c is not None else None for c in row]
                    nonempty = [c for c in cells if c]
                    if not nonempty:
                        continue
                    # header rows
                    if any(c and ('Dipnot' in c) for c in cells) or (cells[0] is None and stmt != 'EQ' and all((c is None) or c in ('TP','YP','Toplam') for c in cells)):
                        if cols is None:
                            cols = [c or '' for c in cells]
                        else:
                            # merge second header row (TP/YP/Toplam) under period headers
                            cur = ''
                            merged = []
                            for a, b in zip(cols, cells):
                                if a: cur = a
                                merged.append((cur + ' | ' + b) if b else a)
                            cols = merged
                        continue
                    if stmt == 'EQ' and cells[0] is None and all((c is None) for c in cells[:3]):
                        # sub-header row of equity table (second header line)
                        cur = ''
                        merged = []
                        for a, b in zip(cols, cells):
                            if a: cur = a
                            merged.append((cur + ' | ' + b) if b else a)
                        cols = merged
                        continue
                    if cols is None:
                        continue
                    # label
                    if stmt == 'EQ':
                        if cells[0]:
                            eq_block = cells[0]
                        label = cells[1] or ''
                        label_idx = 1
                        note = cells[2] or ''
                        vals = cells[3:]
                        vcols = cols[3:]
                    else:
                        label = cells[0] or ''
                        label_idx = 0
                        note = cells[1] or ''
                        vals = cells[2:]
                        vcols = cols[2:]
                    if not label:
                        continue
                    # indent from word positions in the label cell
                    cell_bbox = tb.rows[ri].cells[label_idx]
                    x0 = None
                    if cell_bbox:
                        cx0, cy0, cx1, cy1 = cell_bbox
                        ws = [w for w in page.extract_words() if w['x0'] >= cx0 - 1 and w['x1'] <= cx1 + 1 and w['top'] >= cy0 - 1 and w['bottom'] <= cy1 + 1]
                        if ws:
                            x0 = min(w['x0'] for w in ws)
                    # skip title repeats
                    if stmt_of(label) or label.startswith('Nazım Hesaplar') or label.startswith('Özkaynaklar Değişim'):
                        continue
                    row_order += 1
                    is_eps = label.startswith('Hisse Başına')
                    for c, v in zip(vcols, vals):
                        num = to_num(v)
                        recs.append(dict(**meta, stmt=stmt, eq_block=eq_block, row_order=row_order,
                                         label=label, note=note, x0=round(x0, 1) if x0 else None,
                                         col=c, raw=v, value=num, unit=unit, is_eps=is_eps, page=pi))
    return recs

all_recs = []
for f in sorted(glob.glob(os.path.join(SRC, '*.pdf'))):
    r = parse_file(f)
    print(f, len(r))
    all_recs += r
df = pd.DataFrame(all_recs)
df.to_pickle(OUT)
print(df.shape)
