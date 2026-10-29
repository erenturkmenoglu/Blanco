"""Add Blanco-dictionary item layer (Kalemler), quarterly flows (Kalemler_Q), ratios (Oranlar) and charts (Grafikler)
to DBTR_KAP_DB.xlsx. Everything formula-driven off the DB sheet."""
import pandas as pd, numpy as np, math
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.chart import LineChart, BarChart, Reference, Series
from openpyxl.chart.text import RichText
from openpyxl.drawing.text import Paragraph, ParagraphProperties, CharacterProperties, Font as DFont
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties

SRC = '/home/claude/dbtr/DBTR_KAP_DB.xlsx'
OUT = '/home/claude/dbtr/DBTR_KAP_DB.xlsx'
df = pd.read_pickle('/home/claude/dbtr/kap_db.pkl')
u = df[df.use == 1]

F = 'Arial'
fn = Font(name=F, size=9); fb = Font(name=F, size=9, bold=True); fh = Font(name=F, size=9, bold=True, color='FFFFFF')
fgrey = Font(name=F, size=8, color='808080'); fblue = Font(name=F, size=9, color='0000FF')
hfill = PatternFill('solid', fgColor='1F3864'); sfill = PatternFill('solid', fgColor='D9E1F2')
rfill = PatternFill('solid', fgColor='F2F2F2'); ufill = PatternFill('solid', fgColor='FCE4D6')
NUM = '#,##0.0;-#,##0.0;"-"'; PCT = '0.00%;-0.00%;"-"'; PCT1 = '0.0%;-0.0%;"-"'

wb = load_workbook(SRC)
for n in ('Kalemler', 'Kalemler_Q', 'Oranlar', 'Grafikler'):
    if n in wb.sheetnames: del wb[n]

# DB column letters
dbh = [c.value for c in wb['DB'][1]]
NDB = wb['DB'].max_row
CI = {h: L(j) for j, h in enumerate(dbh, 1)}
def rng(h): return f"DB!${CI[h]}$2:${CI[h]}${NDB}"

# ------------------------------------------------------------------ periods (union)
per_point = sorted(u[u.basis == 'POINT'].p_end.unique())
per_flow = sorted(u[(u.basis == 'YTD') & (u.stmt == 'PL')].p_end.unique())
periods = sorted(set(per_point) | set(per_flow))
periods = [pd.Timestamp(p) for p in periods]
def qlab(p): return f"{p.year}Ç{(p.month - 1) // 3 + 1}"
PC0 = 8  # first period column in Kalemler
pcol = {p: PC0 + i for i, p in enumerate(periods)}

# ------------------------------------------------------------------ item definitions
# (code, name_tr, section, kind, status, spec, note)
# spec: list of (sign, stmt, ccy, path_suffix, basis) summed; or ('DERIVED', [codes with sign]) ; or None (UNAVAILABLE)
BS = lambda path, ccy='Toplam', sign=1: (sign, 'BS', ccy, path, 'POINT')
OB = lambda path, ccy='Toplam', sign=1: (sign, 'OBS', ccy, path, 'POINT')
PL = lambda path, sign=1: (sign, 'PL', 'Toplam', path, 'YTD')
A = 'VARLIKLAR > '; LI = 'YÜKÜMLÜLÜKLER > '; G = 'GELİR VE GİDER KALEMLERİ > '
FV = A + 'FİNANSAL VARLIKLAR (Net) > '; NN = FV + 'Nakit ve Nakit Benzerleri > '
AM = A + 'İTFA EDİLMİŞ MALİYETİ İLE ÖLÇÜLEN FİNANSAL VARLIKLAR (Net) > '
EQ = LI + 'ÖZKAYNAKLAR > '
OBD = 'BİLANÇO DIŞI YÜKÜMLÜLÜKLER > TÜREV FİNANSAL ARAÇLAR > Alım Satım Amaçlı İşlemler > '

items = [
 # ---- Aktifler
 ('total_assets', 'Toplam aktifler', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'VARLIKLAR TOPLAMI')], ''),
 ('financial_assets', 'Finansal varlıklar (Net)', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'FİNANSAL VARLIKLAR (Net)')], ''),
 ('cash_and_cash_equivalents', 'Nakit ve nakit benzerleri', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(FV + 'Nakit ve Nakit Benzerleri')], 'KAP: Nakit Değerler+TCMB + Bankalar + Para piyasası − BZK'),
 ('cash_and_central_bank', 'Nakit Değerler ve TCMB', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(NN + 'Nakit Değerler ve Merkez Bankası')], ''),
 ('balances_with_central_bank', 'Merkez bankasından alacaklar', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(NN + 'Nakit Değerler ve Merkez Bankası')], 'KAP ana tabloda kasa ile TCMB ayrılmaz; = cash_and_central_bank (dipnot gerekir)'),
 ('due_from_banks', 'Bankalar (alacak)', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(NN + 'Bankalar')], ''),
 ('money_market_receivables', 'Para piyasalarından alacaklar', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(NN + 'Para Piyasalarından Alacaklar')], ''),
 ('ecl_allowance_liquid_assets', 'Beklenen zarar karşılığı (likit aktifler)', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(NN + 'Beklenen Zarar Karşılıkları (-)')], 'negatif'),
 ('securities_fvtpl', "GUD farkı K/Z'a yansıtılan FV", 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(FV + 'Gerçeğe Uygun Değer Farkı Kâr Zarara Yansıtılan Finansal Varlıklar')], ''),
 ('securities_fvoci', 'GUD farkı diğer kapsamlı gelire yansıtılan FV', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(FV + 'Gerçeğe Uygun Değer Farkı Diğer Kapsamlı Gelire Yansıtılan Finansal Varlıklar')], ''),
 ('derivative_assets', 'Türev finansal varlıklar', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(FV + 'Türev Finansal Varlıklar')], ''),
 ('amortized_cost_assets_total', 'İtfa edilmiş maliyetle ölçülen FV (net) toplam', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'İTFA EDİLMİŞ MALİYETİ İLE ÖLÇÜLEN FİNANSAL VARLIKLAR (Net)')], ''),
 ('loans_gross', 'Brüt krediler', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(AM + 'Krediler')], 'KAP "Krediler" satırı (BZK öncesi)'),
 ('loans_tl', 'TL krediler', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(AM + 'Krediler', 'TP')], ''),
 ('loans_fx', 'Yabancı para krediler', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(AM + 'Krediler', 'YP')], ''),
 ('ecl_allowance_loans', 'Beklenen zarar karşılığı (krediler)', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(AM + 'Beklenen Zarar Karşılıkları (-)')], 'negatif'),
 ('loans_net', 'Net krediler', 'balance_sheet_assets', 'stock', 'DERIVED', ('D', [('loans_gross', 1), ('ecl_allowance_loans', 1)]), '= brüt krediler + BZK(−)'),
 ('lease_receivables', 'Kiralama alacakları', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(AM + 'Kiralama İşlemlerinden Alacaklar')], ''),
 ('securities_amortized_total', 'İtfa edilmiş maliyetle diğer FV toplam', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(AM + 'İtfa Edilmiş Maliyeti ile Ölçülen Diğer Finansal Varlıklar')], ''),
 ('securities_amortized_government', 'İtfa edilmiş maliyetle DİBS', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(AM + 'İtfa Edilmiş Maliyeti ile Ölçülen Diğer Finansal Varlıklar > Devlet Borçlanma Senetleri')], ''),
 ('securities_portfolio', 'Menkul kıymet portföyü', 'balance_sheet_assets', 'stock', 'DERIVED', ('D', [('securities_fvtpl', 1), ('securities_fvoci', 1), ('securities_amortized_total', 1)]), '= GUD K/Z + GUD DKG + itfa edilmiş diğer FV'),
 ('equity_investments', 'Ortaklık yatırımları', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'ORTAKLIK YATIRIMLARI')], ''),
 ('fixed_assets', 'Maddi duran varlıklar', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'MADDİ DURAN VARLIKLAR (Net)')], ''),
 ('intangible_assets', 'Maddi olmayan duran varlıklar', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'MADDİ OLMAYAN DURAN VARLIKLAR (Net)')], ''),
 ('investment_property', 'Yatırım amaçlı gayrimenkuller', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'YATIRIM AMAÇLI GAYRİMENKULLER (Net)')], ''),
 ('non_current_assets_total', 'Duran varlıklar toplamı', 'balance_sheet_assets', 'stock', 'DERIVED', ('D', [('equity_investments', 1), ('fixed_assets', 1), ('intangible_assets', 1), ('investment_property', 1)]), '= ortaklık + MDV + MODV + YAG'),
 ('current_tax_asset', 'Cari vergi varlığı', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'CARİ VERGİ VARLIĞI')], ''),
 ('deferred_tax_asset', 'Ertelenmiş vergi varlığı', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'ERTELENMİŞ VERGİ VARLIĞI')], ''),
 ('other_assets', 'Diğer aktifler (Net)', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'DİĞER AKTİFLER (Net)')], ''),
 ('assets_tl', 'Toplam aktifler – TP', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'VARLIKLAR TOPLAMI', 'TP')], 'KAP TP/YP ayrımı'),
 ('assets_fx', 'Toplam aktifler – YP', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(A + 'VARLIKLAR TOPLAMI', 'YP')], ''),
 ('cash_cb_fx', 'Nakit Değerler ve TCMB – YP', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(NN + 'Nakit Değerler ve Merkez Bankası', 'YP')], ''),
 ('cash_cb_tl', 'Nakit Değerler ve TCMB – TP', 'balance_sheet_assets', 'stock', 'VERIFIED', [BS(NN + 'Nakit Değerler ve Merkez Bankası', 'TP')], ''),
 # ---- Pasifler
 ('total_liabilities', 'Toplam pasifler (özkaynak dahil)', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'YÜKÜMLÜLÜKLER TOPLAMI')], 'KAP/TBB "Yükümlülükler Toplamı" özkaynağı içerir (= aktif toplamı)'),
 ('total_liabilities_ex_equity', 'Toplam yükümlülükler (özkaynak hariç)', 'balance_sheet_liabilities', 'stock', 'DERIVED', ('D', [('total_liabilities', 1), ('total_equity', -1)]), ''),
 ('total_deposits', 'Toplam mevduat', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'MEVDUAT')], ''),
 ('deposits_tl', 'TL mevduat', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'MEVDUAT', 'TP')], ''),
 ('deposits_fx', 'Yabancı para mevduat', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'MEVDUAT', 'YP')], ''),
 ('demand_deposits', 'Vadesiz mevduat', 'balance_sheet_liabilities', 'stock', 'UNAVAILABLE', None, 'KAP ana tabloda yok; mevduat dipnotu / TBB DT20 Mevd.Vade'),
 ('time_deposits', 'Vadeli mevduat', 'balance_sheet_liabilities', 'stock', 'UNAVAILABLE', None, 'KAP ana tabloda yok; mevduat dipnotu / TBB DT20 Mevd.Vade'),
 ('funds_borrowed', 'Alınan krediler', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'ALINAN KREDİLER')], ''),
 ('funds_borrowed_tl', 'Alınan krediler – TP', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'ALINAN KREDİLER', 'TP')], ''),
 ('funds_borrowed_fx', 'Alınan krediler – YP', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'ALINAN KREDİLER', 'YP')], ''),
 ('money_market_funds', 'Para piyasalarına borçlar', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'PARA PİYASALARINA BORÇLAR')], ''),
 ('securities_issued', 'İhraç edilen menkul kıymetler', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'İHRAÇ EDİLEN MENKUL KIYMETLER (Net)')], ''),
 ('funds', 'Fonlar', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'FONLAR')], ''),
 ('subordinated_debt', 'Sermaye benzeri borçlanma araçları', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'SERMAYE BENZERİ BORÇLANMA ARAÇLARI')], ''),
 ('non_deposit_funding', 'Mevduat dışı kaynaklar toplamı', 'balance_sheet_liabilities', 'stock', 'DERIVED', ('D', [('funds_borrowed', 1), ('money_market_funds', 1), ('securities_issued', 1), ('funds', 1), ('subordinated_debt', 1)]), '= alınan krediler + para piyasası + ihraç + fonlar + sermaye benzeri'),
 ('fvtpl_liabilities', "GUD farkı K/Z'a yansıtılan FY", 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'GERÇEĞE UYGUN DEĞER FARKI KAR ZARARA YANSITILAN FİNANSAL YÜKÜMLÜLÜKLER')], ''),
 ('derivative_liabilities', 'Türev finansal yükümlülükler', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'TÜREV FİNANSAL YÜKÜMLÜLÜKLER')], ''),
 ('lease_liabilities', 'Kiralama işlemlerinden yükümlülükler', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'KİRALAMA İŞLEMLERİNDEN YÜKÜMLÜLÜKLER (Net)')], ''),
 ('provisions', 'Karşılıklar', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'KARŞILIKLAR')], ''),
 ('current_tax_liability', 'Cari vergi borcu', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'CARİ VERGİ BORCU')], ''),
 ('deferred_tax_liability', 'Ertelenmiş vergi borcu', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'ERTELENMİŞ VERGİ BORCU')], ''),
 ('tax_liabilities', 'Cari ve ertelenmiş vergi borcu', 'balance_sheet_liabilities', 'stock', 'DERIVED', ('D', [('current_tax_liability', 1), ('deferred_tax_liability', 1)]), ''),
 ('other_liabilities', 'Diğer yükümlülükler', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'DİĞER YÜKÜMLÜLÜKLER')], ''),
 ('total_equity', 'Toplam özkaynaklar', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'ÖZKAYNAKLAR')], ''),
 ('total_equity_parent', 'Ana ortaklığa ait özkaynaklar', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'ÖZKAYNAKLAR')], 'solo → total_equity ile aynı'),
 ('minority_interests', 'Azınlık payları', 'balance_sheet_liabilities', 'stock', 'UNAVAILABLE', None, 'solo bilançoda kalem yok'),
 ('paid_in_capital', 'Ödenmiş sermaye', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(EQ + 'Ödenmiş Sermaye')], ''),
 ('capital_reserves', 'Sermaye yedekleri', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(EQ + 'Sermaye Yedekleri')], ''),
 ('oci_accumulated', 'Birikmiş diğer kapsamlı gelir (toplam)', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(EQ + 'Kâr veya Zararda Yeniden Sınıflandırılmayacak Birikmiş Diğer Kapsamlı Gelirler veya Giderler'), BS(EQ + 'Kâr veya Zararda Yeniden Sınıflandırılacak Birikmiş Diğer Kapsamlı Gelirler veya Giderler')], 'iki birikmiş OCI satırının toplamı'),
 ('profit_reserves', 'Kâr yedekleri', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(EQ + 'Kar Yedekleri')], ''),
 ('profit_loss_total', 'Kâr/zarar toplamı (bilanço)', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(EQ + 'Kar veya Zarar')], ''),
 ('retained_earnings', 'Geçmiş yıl kârları', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(EQ + 'Kar veya Zarar > Geçmiş Yıllar Kar veya Zararı')], ''),
 ('net_profit_bs', 'Dönem net kârı (bilanço)', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(EQ + 'Kar veya Zarar > Dönem Net Kâr veya Zararı')], ''),
 ('liabilities_tl', 'Toplam pasifler – TP', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'YÜKÜMLÜLÜKLER TOPLAMI', 'TP')], ''),
 ('liabilities_fx', 'Toplam pasifler – YP', 'balance_sheet_liabilities', 'stock', 'VERIFIED', [BS(LI + 'YÜKÜMLÜLÜKLER TOPLAMI', 'YP')], ''),
 # ---- Nazım (KAP'a özgü ek kalemler)
 ('guarantees', 'Garanti ve kefaletler', 'off_balance_sheet', 'stock', 'VERIFIED', [OB('BİLANÇO DIŞI YÜKÜMLÜLÜKLER > GARANTİ VE KEFALETLER')], ''),
 ('commitments', 'Taahhütler', 'off_balance_sheet', 'stock', 'VERIFIED', [OB('BİLANÇO DIŞI YÜKÜMLÜLÜKLER > TAAHHÜTLER')], ''),
 ('fwd_asset_purchase_commitments', 'Vadeli aktif değer alım-satım taahhütleri', 'off_balance_sheet', 'stock', 'VERIFIED', [OB('BİLANÇO DIŞI YÜKÜMLÜLÜKLER > TAAHHÜTLER > Cayılamaz Taahhütler > Vadeli Aktif Değerler Alım Satım Taahhütleri')], ''),
 ('derivatives_notional', 'Türev finansal araçlar (nominal)', 'off_balance_sheet', 'stock', 'VERIFIED', [OB('BİLANÇO DIŞI YÜKÜMLÜLÜKLER > TÜREV FİNANSAL ARAÇLAR')], ''),
 ('fx_forwards_notional', 'Vadeli döviz alım-satım (nominal)', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Vadeli Döviz Alım-Satım İşlemleri')], ''),
 ('fx_forward_buy', 'Vadeli döviz alım', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Vadeli Döviz Alım-Satım İşlemleri > Vadeli Döviz Alım İşlemleri')], ''),
 ('fx_forward_sell', 'Vadeli döviz satım', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Vadeli Döviz Alım-Satım İşlemleri > Vadeli Döviz Satım İşlemleri')], ''),
 ('swaps_notional', 'Para ve faiz swap (nominal)', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Para ve Faiz Swap İşlemleri')], ''),
 ('ccy_swap_buy', 'Swap para alım', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Para ve Faiz Swap İşlemleri > Swap Para Alım İşlemleri')], ''),
 ('ccy_swap_sell', 'Swap para satım', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Para ve Faiz Swap İşlemleri > Swap Para Satım İşlemleri')], ''),
 ('ccy_swap_buy_tl', 'Swap para alım – TP bacak', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Para ve Faiz Swap İşlemleri > Swap Para Alım İşlemleri', 'TP')], ''),
 ('ccy_swap_sell_fx', 'Swap para satım – YP bacak', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Para ve Faiz Swap İşlemleri > Swap Para Satım İşlemleri', 'YP')], ''),
 ('irs_notional', 'Swap faiz alım (IRS nominal)', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Para ve Faiz Swap İşlemleri > Swap Faiz Alım İşlemleri')], ''),
 ('futures_notional', 'Futures para (nominal)', 'off_balance_sheet', 'stock', 'VERIFIED', [OB(OBD + 'Futures Para İşlemleri')], ''),
 ('custody_assets', 'Emanet kıymetler', 'off_balance_sheet', 'stock', 'VERIFIED', [OB('EMANET VE REHİNLİ KIYMETLER > EMANET KIYMETLER')], ''),
 ('client_funds_portfolio', 'Müşteri fon ve portföy mevcutları', 'off_balance_sheet', 'stock', 'VERIFIED', [OB('EMANET VE REHİNLİ KIYMETLER > EMANET KIYMETLER > Müşteri Fon ve Portföy Mevcutları')], ''),
 # ---- Gelir tablosu (YTD)
 ('interest_income', 'Faiz gelirleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GELİRLERİ')], ''),
 ('interest_on_loans', 'Kredilerden alınan faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GELİRLERİ > Kredilerden Alınan Faizler')], ''),
 ('interest_on_reserves', 'Zorunlu karşılıklardan alınan faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GELİRLERİ > Zorunlu Karşılıklardan Alınan Faizler')], 'satır yalnızca sıfırdan farklı dönemlerde bildirilmiş'),
 ('interest_from_banks', 'Bankalardan alınan faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GELİRLERİ > Bankalardan Alınan Faizler')], ''),
 ('interest_from_money_market', 'Para piyasası işlemlerinden alınan faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GELİRLERİ > Para Piyasası İşlemlerinden Alınan Faizler')], ''),
 ('interest_on_securities', 'Menkul değerlerden alınan faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GELİRLERİ > Menkul Değerlerden Alınan Faizler')], ''),
 ('other_interest_income', 'Diğer faiz gelirleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GELİRLERİ > Diğer Faiz Gelirleri'), PL(G + 'FAİZ GELİRLERİ > Finansal Kiralama Faiz Gelirleri')], 'KAP "Diğer" + finansal kiralama faiz gelirleri'),
 ('interest_expense', 'Faiz giderleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GİDERLERİ (-)')], 'negatif işaretli (KAP)'),
 ('interest_on_deposits', 'Mevduata verilen faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GİDERLERİ (-) > Mevduata Verilen Faizler')], 'negatif'),
 ('interest_on_funds_borrowed', 'Kullanılan kredilere verilen faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GİDERLERİ (-) > Kullanılan Kredilere Verilen Faizler')], 'negatif'),
 ('interest_on_money_market', 'Para piyasası işlemlerine verilen faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GİDERLERİ (-) > Para Piyasası İşlemlerine Verilen Faizler')], 'negatif'),
 ('interest_on_securities_issued', 'İhraç edilen MK verilen faizler', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GİDERLERİ (-) > İhraç Edilen Menkul Kıymetlere Verilen Faizler')], 'negatif'),
 ('other_interest_expense', 'Diğer faiz giderleri (kiralama dahil)', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAİZ GİDERLERİ (-) > Diğer Faiz Giderleri'), PL(G + 'FAİZ GİDERLERİ (-) > Kiralama Faiz Giderleri')], 'negatif'),
 ('net_interest_income', 'Net faiz geliri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'NET FAİZ GELİRİ VEYA GİDERİ')], ''),
 ('fee_commission_income', 'Ücret ve komisyon gelirleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'NET ÜCRET VE KOMİSYON GELİRLERİ VEYA GİDERLERİ > Alınan Ücret ve Komisyonlar')], ''),
 ('fee_commission_expense', 'Ücret ve komisyon giderleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'NET ÜCRET VE KOMİSYON GELİRLERİ VEYA GİDERLERİ > Verilen Ücret ve Komisyonlar (-)')], 'negatif'),
 ('net_fee_commission_income', 'Net ücret ve komisyon geliri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'NET ÜCRET VE KOMİSYON GELİRLERİ VEYA GİDERLERİ')], ''),
 ('dividend_income', 'Temettü gelirleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'TEMETTÜ GELİRLERİ')], ''),
 ('trading_income', 'Ticari kâr/zarar (net)', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'TİCARİ KAR VEYA ZARAR (Net)')], ''),
 ('trading_securities', '  Sermaye piyasası işlemleri K/Z', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'TİCARİ KAR VEYA ZARAR (Net) > Sermaye Piyasası İşlemleri Karı (Zararı)')], ''),
 ('trading_derivatives', '  Türev finansal işlemler K/Z', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'TİCARİ KAR VEYA ZARAR (Net) > Türev Finansal İşlemlerden Kar (Zarar)')], ''),
 ('trading_fx', '  Kambiyo işlemleri K/Z', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'TİCARİ KAR VEYA ZARAR (Net) > Kambiyo İşlemleri Karı (Zararı)')], ''),
 ('other_operating_income', 'Diğer faaliyet gelirleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'DİĞER FAALİYET GELİRLERİ')], ''),
 ('gross_operating_profit', 'Faaliyet brüt kârı', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'FAALİYET BRÜT KÂRI')], ''),
 ('total_revenue', 'Toplam gelir (NII + net ücret + ticari + diğer)', 'income_statement', 'flow', 'DERIVED', ('D', [('net_interest_income', 1), ('net_fee_commission_income', 1), ('trading_income', 1), ('other_operating_income', 1)]), 'Blanco cost_to_income paydası'),
 ('expected_credit_loss_expense', 'Beklenen zarar karşılıkları giderleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'BEKLENEN ZARAR KARŞILIKLARI GİDERLERİ (-)')], 'negatif'),
 ('other_provision_expense', 'Diğer karşılık giderleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'DİĞER KARŞILIK GİDERLERİ (-)')], 'negatif'),
 ('provision_expenses', 'Karşılık giderleri (toplam)', 'income_statement', 'flow', 'DERIVED', ('D', [('expected_credit_loss_expense', 1), ('other_provision_expense', 1)]), 'negatif'),
 ('personnel_expenses', 'Personel giderleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'PERSONEL GİDERLERİ (-)')], 'negatif'),
 ('other_operating_expenses', 'Diğer faaliyet giderleri', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'DİĞER FAALİYET GİDERLERİ (-)')], 'negatif'),
 ('operating_expenses', 'Faaliyet giderleri (personel + diğer)', 'income_statement', 'flow', 'DERIVED', ('D', [('personnel_expenses', 1), ('other_operating_expenses', 1)]), 'negatif'),
 ('net_operating_profit', 'Net faaliyet kârı', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'NET FAALİYET KARI (ZARARI)')], ''),
 ('monetary_position_gain', 'Net parasal pozisyon K/Z (TMS 29)', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'NET PARASAL POZİSYON KARI (ZARARI)')], 'tüm dönemlerde 0 → enflasyon muhasebesi yok'),
 ('profit_before_tax', 'Vergi öncesi kâr', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'SÜRDÜRÜLEN FAALİYETLER VERGİ ÖNCESİ KARI (ZARARI)')], ''),
 ('tax_provision', 'Vergi karşılığı', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'SÜRDÜRÜLEN FAALİYETLER VERGİ KARŞILIĞI (+/-)')], 'negatif'),
 ('net_profit_continuing', 'Sürdürülen faaliyetler dönem net kârı', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'SÜRDÜRÜLEN FAALİYETLER DÖNEM NET KARI (ZARARI)')], ''),
 ('net_profit', 'Net dönem kârı', 'income_statement', 'flow', 'VERIFIED', [PL(G + 'DÖNEM NET KARI VEYA ZARARI')], ''),
 # ---- Kredi kalitesi
 ('ecl_total_tfrs9', 'Toplam beklenen kredi zararı karşılığı (bilanço)', 'credit_quality', 'stock', 'DERIVED', ('D', [('ecl_allowance_liquid_assets', -1), ('ecl_allowance_loans', -1)]), '= −(BZK likit + BZK krediler); pozitif gösterim'),
 ('npl_amount', 'Takipteki krediler (3. aşama)', 'credit_quality', 'stock', 'UNAVAILABLE', None, 'KAP ana tabloda yok; kredi dipnotu / TBB DT20 Donuk Alacak'),
 ('loan_loss_provisions', 'Donuk alacak özel karşılığı', 'credit_quality', 'stock', 'UNAVAILABLE', None, 'dipnot / DT20'),
 ('stage_2_loans', 'İkinci aşama krediler', 'credit_quality', 'stock', 'UNAVAILABLE', None, 'dipnot / DT20'),
 ('restructured_loans', 'Yeniden yapılandırılan krediler', 'credit_quality', 'stock', 'UNAVAILABLE', None, 'dipnot / DT20'),
 # ---- Sermaye / likidite / operasyon / faiz
 ('capital_adequacy_ratio', 'Sermaye yeterliliği oranı', 'capital', 'ratio', 'UNAVAILABLE', None, 'KAP ana tabloda yok; SYR dipnotu (tam finansal rapor PDF) / BDDK'),
 ('tier_1_ratio', 'Ana sermaye yeterlilik oranı', 'capital', 'ratio', 'UNAVAILABLE', None, 'SYR dipnotu'),
 ('cet1_ratio', 'Çekirdek sermaye yeterlilik oranı', 'capital', 'ratio', 'UNAVAILABLE', None, 'SYR dipnotu'),
 ('risk_weighted_assets', 'Risk ağırlıklı varlıklar', 'capital', 'stock', 'UNAVAILABLE', None, 'SYR dipnotu'),
 ('liquidity_coverage_ratio', 'Likidite karşılama oranı', 'liquidity', 'ratio', 'UNAVAILABLE', None, 'LKO dipnotu'),
 ('nsfr', 'Net istikrarlı fonlama oranı', 'liquidity', 'ratio', 'UNAVAILABLE', None, 'NSFR dipnotu'),
 ('employee_count', 'Personel sayısı', 'operations', 'count', 'UNAVAILABLE', None, 'TBB DT13 / faaliyet raporu'),
 ('branch_count', 'Şube sayısı', 'operations', 'count', 'UNAVAILABLE', None, 'TBB DT13'),
 ('loan_interest_tl', 'TL kredi ort. faiz (stok)', 'interest', 'rate', 'UNAVAILABLE', None, 'faiz oranı riski dipnotu / TBB DT20'),
 ('deposit_interest_tl', 'TL mevduat ort. faiz (stok)', 'interest', 'rate', 'UNAVAILABLE', None, 'TBB DT20'),
 ('loan_interest_usd', 'USD kredi ort. faiz', 'interest', 'rate', 'UNAVAILABLE', None, 'TBB DT20'),
 ('deposit_interest_usd', 'USD mevduat ort. faiz', 'interest', 'rate', 'UNAVAILABLE', None, 'TBB DT20'),
 ('loan_interest_eur', 'EUR kredi ort. faiz', 'interest', 'rate', 'UNAVAILABLE', None, 'TBB DT20'),
 ('deposit_interest_eur', 'EUR mevduat ort. faiz', 'interest', 'rate', 'UNAVAILABLE', None, 'TBB DT20'),
 ('maturity_buckets', 'Kalan vade dağılımı (kredi/mevduat/aktif/pasif)', 'maturity', 'stock', 'UNAVAILABLE', None, 'likidite riski dipnotu / TBB DT20 kalan vade'),
]
code_row = {}

# ------------------------------------------------------------------ Kalemler sheet
ws = wb.create_sheet('Kalemler', index=wb.sheetnames.index('Items') + 1)
ws['A1'] = 'Blanco veri sözlüğü kalemleri – Deutsche Bank A.Ş. solo, KAP ana tablolarından'; ws['A1'].font = Font(name=F, size=11, bold=True)
ws['A2'] = 'mn TL nominal. Stoklar dönem sonu; akımlar yılbaşından kümülatif (YTD) — çeyreklik için Kalemler_Q. Boş hücre = o dönem için veri yok (31.03.2021 ve 30.06.2021 bilançoları bildirimlerde yok). UNAVAILABLE = KAP ana tablolarında bulunmayan kalem; kaynak notta.'; ws['A2'].font = fgrey
hdr = ['code', 'Kalem', 'section', 'kind', 'status', 'kaynak / formül', 'not']
for j, h in enumerate(hdr, 1):
    c = ws.cell(4, j, h); c.font = fh; c.fill = hfill
for p, j in pcol.items():
    c = ws.cell(4, j, p.to_pydatetime()); c.number_format = 'mm/yy'; c.font = fh; c.fill = hfill; c.alignment = Alignment(horizontal='right')
    c2 = ws.cell(3, j, qlab(p)); c2.font = fgrey; c2.alignment = Alignment(horizontal='right')
r = 5
for i_, it_ in enumerate(items): code_row[it_[0]] = 5 + i_
for code, name, sec, kind, status, spec, note in items:
    ws.cell(r, 1, code).font = fgrey
    ws.cell(r, 2, name).font = fb if kind == 'stock' and ('total' in code or code in ('loans_gross', 'net_profit', 'net_interest_income')) else fn
    ws.cell(r, 3, sec).font = fgrey; ws.cell(r, 4, kind).font = fgrey
    cs = ws.cell(r, 5, status); cs.font = fn
    if status == 'UNAVAILABLE': cs.fill = ufill
    if status == 'DERIVED': cs.fill = rfill
    cn = ws.cell(r, 7, ('… ' + note) if note[:1] in '=+-−' else note); cn.font = fgrey
    if spec is None:
        ws.cell(r, 6, '—').font = fgrey
        r += 1; continue
    if isinstance(spec, tuple) and spec[0] == 'D':
        ws.cell(r, 6, 'Σ ' + ' '.join(('+' if s > 0 else '−') + c_ for c_, s in spec[1])).font = fgrey
        for p, j in pcol.items():
            col = L(j)
            parts = [f"{'+' if s > 0 else '-'}{col}{code_row[c_]}" for c_, s in spec[1]]
            first = f"{col}{code_row[spec[1][0][0]]}"
            f = f'=IF({first}="","",{"".join(parts).lstrip("+")})'
            ws.cell(r, j, f).number_format = NUM; ws.cell(r, j).font = fn
        r += 1; continue
    keys = [(s, f"{st}|{cc}|{path}", basis) for s, st, cc, path, basis in spec]
    ws.cell(r, 6, '; '.join(k[1] for k in keys)).font = fgrey
    for p, j in pcol.items():
        col = L(j)
        # availability: for stocks require a BS obs that period; for flows a PL obs
        avail_key = keys[0][1] if kind == 'stock' else keys[0][1]
        basis = keys[0][2]
        sums = []
        for s, k, b in keys:
            sums.append(f"{'+' if s > 0 else '-'}SUMIFS({rng('value_mn')},{rng('series_key')},\"{k}\",{rng('p_end')},{col}$4,{rng('basis')},\"{b}\",{rng('use')},1)")
        chk = f"COUNTIFS({rng('stmt')},\"{keys[0][1].split('|')[0]}\",{rng('p_end')},{col}$4,{rng('basis')},\"{basis}\",{rng('use')},1)"
        f = f'=IF({chk}=0,"",{"".join(sums).lstrip("+")})'
        c = ws.cell(r, j, f); c.number_format = NUM; c.font = fn
    r += 1
NK = r - 1
ws.column_dimensions['A'].width = 26; ws.column_dimensions['B'].width = 44; ws.column_dimensions['C'].width = 4; ws.column_dimensions['D'].width = 4
ws.column_dimensions['E'].width = 11; ws.column_dimensions['F'].width = 4; ws.column_dimensions['G'].width = 4
for j in pcol.values(): ws.column_dimensions[L(j)].width = 9
ws.freeze_panes = ws.cell(5, PC0)
ws.sheet_view.zoomScale = 90

# ------------------------------------------------------------------ Kalemler_Q (quarterly flows + TTM)
flow_codes = [it for it in items if it[3] == 'flow' and it[5] is not None]
wq = wb.create_sheet('Kalemler_Q', index=wb.sheetnames.index('Kalemler') + 1)
wq['A1'] = 'Gelir tablosu kalemleri – bağımsız çeyrek ve son 4 çeyrek (TTM)'; wq['A1'].font = Font(name=F, size=11, bold=True)
wq['A2'] = 'Çeyrek = YTD − önceki YTD (Ç1 = YTD); 2020Ç3 bildirilen 3 aylık. TTM = son 4 çeyrek toplamı (4 çeyrek yoksa boş).'; wq['A2'].font = fgrey
for j, h in enumerate(['code', 'Kalem', 'blok'], 1):
    c = wq.cell(4, j, h); c.font = fh; c.fill = hfill
QC0 = 5
qcol = {p: QC0 + i for i, p in enumerate(periods)}
for p, j in qcol.items():
    c = wq.cell(4, j, p.to_pydatetime()); c.number_format = 'mm/yy'; c.font = fh; c.fill = hfill; c.alignment = Alignment(horizontal='right')
    c2 = wq.cell(3, j, qlab(p)); c2.font = fgrey; c2.alignment = Alignment(horizontal='right')
qrow = {}; trow = {}
r = 5
wq.cell(r, 2, 'ÇEYREKLİK').font = fb; r += 1
for code, name, *_ in flow_codes:
    qrow[code] = r
    wq.cell(r, 1, code).font = fgrey; wq.cell(r, 2, name).font = fn; wq.cell(r, 3, 'Q').font = fgrey
    kr = code_row[code]
    for i, p in enumerate(periods):
        j = qcol[p]; kc = L(pcol[p])
        if i == 0:
            # reported 3M (PL only)
            spec = [it for it in items if it[0] == code][0][5]
            if isinstance(spec, tuple):
                parts = [f"{'+' if s > 0 else '-'}{L(j)}{qrow.get(c_, 0)}" for c_, s in spec[1]] if all(c_ in qrow for c_, s in spec[1]) else None
                f = f'=IF({L(j)}{qrow[spec[1][0][0]]}="","",{"".join(parts).lstrip("+")})' if parts else '=""'
            else:
                sums = ''.join(f"{'+' if s > 0 else '-'}SUMIFS({rng('value_mn')},{rng('series_key')},\"{st}|{cc}|{path}\",{rng('p_end')},Kalemler!{kc}$4,{rng('basis')},\"Q3M\",{rng('use')},1)" for s, st, cc, path, b in spec)
                chk = f"COUNTIFS({rng('stmt')},\"PL\",{rng('p_end')},Kalemler!{kc}$4,{rng('basis')},\"Q3M\",{rng('use')},1)"
                f = f'=IF({chk}=0,"",{sums.lstrip("+")})'
        else:
            pc = L(pcol[periods[i - 1]])
            f = f'=IF(Kalemler!{kc}{kr}="","",IF(MONTH(Kalemler!{kc}$4)=3,Kalemler!{kc}{kr},IF(Kalemler!{pc}{kr}="","",Kalemler!{kc}{kr}-Kalemler!{pc}{kr})))'
        c = wq.cell(r, j, f); c.number_format = NUM; c.font = fn
    r += 1
r += 1
wq.cell(r, 2, 'SON 4 ÇEYREK (TTM)').font = fb; r += 1
for code, name, *_ in flow_codes:
    trow[code] = r
    wq.cell(r, 1, code).font = fgrey; wq.cell(r, 2, name).font = fn; wq.cell(r, 3, 'TTM').font = fgrey
    for i, p in enumerate(periods):
        j = qcol[p]
        if i < 3:
            f = '=""'
        else:
            cells = [f"{L(qcol[periods[i - k]])}{qrow[code]}" for k in range(4)]
            f = f'=IF(OR({",".join(c_ + "=\"\"" for c_ in cells)}),"",{"+".join(cells)})'
        c = wq.cell(r, j, f); c.number_format = NUM; c.font = fn
    r += 1
wq.column_dimensions['A'].width = 26; wq.column_dimensions['B'].width = 44; wq.column_dimensions['C'].width = 5
for j in qcol.values(): wq.column_dimensions[L(j)].width = 9
wq.freeze_panes = wq.cell(5, QC0); wq.sheet_view.zoomScale = 90

# ------------------------------------------------------------------ Oranlar
wo = wb.create_sheet('Oranlar', index=wb.sheetnames.index('Kalemler_Q') + 1)
wo['A1'] = 'Türetilmiş oranlar – Blanco tanımları (ytd_x4q yıllıklandırma, avg_2pt ortalama) + TTM/ortalama-bakiye varyantları'; wo['A1'].font = Font(name=F, size=11, bold=True)
wo['A2'] = 'Blanco yöntemi: akım = YTD×4/q; ortalama bakiye = (dönem sonu + önceki yıl sonu)/2. TTM yöntemi: akım = son 4 çeyrek; ortalama = son 5 çeyrek sonu ortalaması (eksik çeyrek varsa boş). Büyüme: stok QoQ/YoY; kâr YoY aynı YTD penceresi.'; wo['A2'].font = fgrey
for j, h in enumerate(['code', 'Oran', 'yöntem', 'formül'], 1):
    c = wo.cell(4, j, h); c.font = fh; c.fill = hfill
OC0 = 6
ocol = {p: OC0 + i for i, p in enumerate(periods)}
for p, j in ocol.items():
    c = wo.cell(4, j, p.to_pydatetime()); c.number_format = 'mm/yy'; c.font = fh; c.fill = hfill; c.alignment = Alignment(horizontal='right')
    c2 = wo.cell(3, j, qlab(p)); c2.font = fgrey; c2.alignment = Alignment(horizontal='right')

def K(code, p): return f"Kalemler!{L(pcol[p])}{code_row[code]}"
def Q(code, p): return f"Kalemler_Q!{L(qcol[p])}{qrow[code]}"
def T(code, p): return f"Kalemler_Q!{L(qcol[p])}{trow[code]}"
def prev_q(p): return p - pd.offsets.QuarterEnd(1)
def prev_ye(p): return pd.Timestamp(year=p.year - 1, month=12, day=31)
def yago(p): return p - pd.offsets.QuarterEnd(4)
def has(p): return p in pcol
def ann(code, p):  # ytd_x4q
    q = (p.month - 1) // 3 + 1
    return f"({K(code, p)}*4/{q})"
def avg2(code, p):
    pe = prev_ye(p)
    if not has(pe): return None
    return f"(({K(code, p)}+{K(code, pe)})/2)"
def avg5(code, p):
    ps = [p - pd.offsets.QuarterEnd(k) for k in range(5)]
    if not all(has(x) for x in ps): return None
    return f"(({'+'.join(K(code, x) for x in ps)})/5)"
def guard(cells, expr):
    conds = ','.join(f'{c}=""' for c in cells)
    return f'=IF(OR({conds}),"",IFERROR({expr},""))'

orat = []  # (code, name, method, formula_text, fn(p)->formula or None, numfmt)
def add(code, name, method, ftxt, gen, fmt=PCT): orat.append((code, name, method, ftxt, gen, fmt))

add('roa', 'Aktif kârlılığı (ROA)', 'Blanco ytd_x4q / avg_2pt', 'net_profit_annualized / avg(total_assets)',
    lambda p: guard([K('net_profit', p), K('total_assets', p), K('total_assets', prev_ye(p))], f"{ann('net_profit', p)}/{avg2('total_assets', p)}") if avg2('total_assets', p) else None)
add('roa_ttm', 'ROA – TTM / 5 çeyrek ort.', 'TTM / avg_5q', 'net_profit_ttm / avg5(total_assets)',
    lambda p: guard([T('net_profit', p)] + [K('total_assets', p - pd.offsets.QuarterEnd(k)) for k in range(5)], f"{T('net_profit', p)}/{avg5('total_assets', p)}") if avg5('total_assets', p) else None)
add('roe', 'Özkaynak kârlılığı (ROE)', 'Blanco ytd_x4q / avg_2pt', 'net_profit_annualized / avg(total_equity)',
    lambda p: guard([K('net_profit', p), K('total_equity', p), K('total_equity', prev_ye(p))], f"{ann('net_profit', p)}/{avg2('total_equity', p)}") if avg2('total_equity', p) else None)
add('roe_ttm', 'ROE – TTM / 5 çeyrek ort.', 'TTM / avg_5q', 'net_profit_ttm / avg5(total_equity)',
    lambda p: guard([T('net_profit', p)] + [K('total_equity', p - pd.offsets.QuarterEnd(k)) for k in range(5)], f"{T('net_profit', p)}/{avg5('total_equity', p)}") if avg5('total_equity', p) else None)
add('nim', 'Net faiz marjı (toplam aktif proxy)', 'Blanco ytd_x4q / avg_2pt', 'nii_annualized / avg(total_assets)',
    lambda p: guard([K('net_interest_income', p), K('total_assets', p), K('total_assets', prev_ye(p))], f"{ann('net_interest_income', p)}/{avg2('total_assets', p)}") if avg2('total_assets', p) else None)
# interest-earning assets derived
add('nim_iea_ttm', 'Net faiz marjı – faiz getirili aktif, TTM', 'TTM / avg_5q', 'nii_ttm / avg5(cash&CB + bankalar + PP + GUD KZ + GUD DKG + itfa diğer FV + brüt krediler)',
    lambda p: (lambda ps: guard([T('net_interest_income', p)] + [K('total_assets', x) for x in ps],
        f"{T('net_interest_income', p)}/((" + '+'.join('+'.join(K(c_, x) for c_ in ('cash_and_central_bank', 'due_from_banks', 'money_market_receivables', 'securities_fvtpl', 'securities_fvoci', 'securities_amortized_total', 'loans_gross')) for x in ps) + ")/5)"))([p - pd.offsets.QuarterEnd(k) for k in range(5)]) if avg5('total_assets', p) else None)
add('nim_q_ann', 'Net faiz marjı – çeyrek yıllıklandırılmış / dönem sonu aktif', 'Q×4 / period_end', 'nii_q×4 / total_assets',
    lambda p: guard([Q('net_interest_income', p), K('total_assets', p)], f"{Q('net_interest_income', p)}*4/{K('total_assets', p)}"))
add('cost_to_income', 'Gider/Gelir (CIR)', 'Blanco YTD', '−operating_expenses / (nii + net fee + trading + other)',
    lambda p: guard([K('operating_expenses', p), K('total_revenue', p)], f"-{K('operating_expenses', p)}/{K('total_revenue', p)}"))
add('cost_to_income_q', 'Gider/Gelir – çeyrek', 'Q', '−opex_q / revenue_q',
    lambda p: guard([Q('operating_expenses', p), Q('total_revenue', p)], f"-{Q('operating_expenses', p)}/{Q('total_revenue', p)}"))
add('cost_of_risk', 'Kredi risk maliyeti (CoR)', 'Blanco ytd_x4q / avg_2pt', '−ECL_expense_annualized / avg(loans_gross)',
    lambda p: guard([K('expected_credit_loss_expense', p), K('loans_gross', p), K('loans_gross', prev_ye(p))], f"-{ann('expected_credit_loss_expense', p)}/{avg2('loans_gross', p)}") if avg2('loans_gross', p) else None)
add('effective_tax_rate', 'Efektif vergi oranı', 'YTD', '−tax_provision / profit_before_tax',
    lambda p: guard([K('tax_provision', p), K('profit_before_tax', p)], f"-{K('tax_provision', p)}/{K('profit_before_tax', p)}"))
add('equity_to_assets', 'Özkaynak/Aktif', 'point', 'total_equity / total_assets',
    lambda p: guard([K('total_equity', p), K('total_assets', p)], f"{K('total_equity', p)}/{K('total_assets', p)}"))
add('loan_to_deposit_ratio', 'Kredi/Mevduat', 'point', 'loans_gross / total_deposits',
    lambda p: guard([K('loans_gross', p), K('total_deposits', p)], f"{K('loans_gross', p)}/{K('total_deposits', p)}"))
add('loans_to_assets', 'Kredi/Aktif', 'point', 'loans_gross / total_assets',
    lambda p: guard([K('loans_gross', p), K('total_assets', p)], f"{K('loans_gross', p)}/{K('total_assets', p)}"))
add('deposits_to_assets', 'Mevduat/Aktif', 'point', 'total_deposits / total_assets',
    lambda p: guard([K('total_deposits', p), K('total_assets', p)], f"{K('total_deposits', p)}/{K('total_assets', p)}"))
add('funds_borrowed_to_assets', 'Alınan krediler/Aktif', 'point', 'funds_borrowed / total_assets',
    lambda p: guard([K('funds_borrowed', p), K('total_assets', p)], f"{K('funds_borrowed', p)}/{K('total_assets', p)}"))
add('cash_to_assets', 'Nakit/Aktif', 'point', 'cash_and_cash_equivalents / total_assets  (Blanco liquid_assets_ratio KAP\'ta çift sayım → bu kullanıldı)',
    lambda p: guard([K('cash_and_cash_equivalents', p), K('total_assets', p)], f"{K('cash_and_cash_equivalents', p)}/{K('total_assets', p)}"))
add('securities_to_assets', 'Menkul kıymet/Aktif', 'point', 'securities_portfolio / total_assets',
    lambda p: guard([K('securities_portfolio', p), K('total_assets', p)], f"{K('securities_portfolio', p)}/{K('total_assets', p)}"))
add('fx_assets_share', 'YP aktif payı', 'point', 'assets_fx / total_assets',
    lambda p: guard([K('assets_fx', p), K('total_assets', p)], f"{K('assets_fx', p)}/{K('total_assets', p)}"))
add('fx_liabilities_share', 'YP pasif payı', 'point', 'liabilities_fx / total_liabilities',
    lambda p: guard([K('liabilities_fx', p), K('total_liabilities', p)], f"{K('liabilities_fx', p)}/{K('total_liabilities', p)}"))
add('fx_loans_share', 'YP kredi payı', 'point', 'loans_fx / loans_gross',
    lambda p: guard([K('loans_fx', p), K('loans_gross', p)], f"{K('loans_fx', p)}/{K('loans_gross', p)}"))
add('fx_deposits_share', 'YP mevduat payı', 'point', 'deposits_fx / total_deposits',
    lambda p: guard([K('deposits_fx', p), K('total_deposits', p)], f"{K('deposits_fx', p)}/{K('total_deposits', p)}"))
add('on_bs_fx_gap', 'Bilanço içi YP pozisyonu (YP aktif − YP pasif)', 'point, mn TL', 'assets_fx − liabilities_fx',
    lambda p: guard([K('assets_fx', p), K('liabilities_fx', p)], f"{K('assets_fx', p)}-{K('liabilities_fx', p)}"), NUM)
add('derivatives_to_assets', 'Türev nominal/Aktif (x)', 'point', 'derivatives_notional / total_assets',
    lambda p: guard([K('derivatives_notional', p), K('total_assets', p)], f"{K('derivatives_notional', p)}/{K('total_assets', p)}"), '0.00"x"')
add('nii_share', 'NII / toplam gelir', 'YTD', 'nii / total_revenue',
    lambda p: guard([K('net_interest_income', p), K('total_revenue', p)], f"{K('net_interest_income', p)}/{K('total_revenue', p)}"))
add('fee_share', 'Net ücret / toplam gelir', 'YTD', 'net_fee / total_revenue',
    lambda p: guard([K('net_fee_commission_income', p), K('total_revenue', p)], f"{K('net_fee_commission_income', p)}/{K('total_revenue', p)}"))
add('trading_share', 'Ticari K/Z / toplam gelir', 'YTD', 'trading / total_revenue',
    lambda p: guard([K('trading_income', p), K('total_revenue', p)], f"{K('trading_income', p)}/{K('total_revenue', p)}"))
add('nii_plus_trading_q', 'NII + Ticari K/Z (çeyrek, mn TL)', 'Q, mn TL', 'nii_q + trading_q  (swap-fonlu carry\'nin iki bacağı birlikte)',
    lambda p: guard([Q('net_interest_income', p), Q('trading_income', p)], f"{Q('net_interest_income', p)}+{Q('trading_income', p)}"), NUM)
add('int_yield_loans_ttm', 'Kredi faiz getirisi (TTM / 5Ç ort. brüt kredi)', 'TTM / avg_5q', 'interest_on_loans_ttm / avg5(loans_gross)',
    lambda p: guard([T('interest_on_loans', p)] + [K('loans_gross', p - pd.offsets.QuarterEnd(k)) for k in range(5)], f"{T('interest_on_loans', p)}/{avg5('loans_gross', p)}") if avg5('loans_gross', p) else None)
add('int_cost_deposits_ttm', 'Mevduat faiz maliyeti (TTM / 5Ç ort. mevduat)', 'TTM / avg_5q', '−interest_on_deposits_ttm / avg5(total_deposits)',
    lambda p: guard([T('interest_on_deposits', p)] + [K('total_deposits', p - pd.offsets.QuarterEnd(k)) for k in range(5)], f"-{T('interest_on_deposits', p)}/{avg5('total_deposits', p)}") if avg5('total_deposits', p) else None)
add('int_cost_funds_borrowed_ttm', 'Alınan kredi faiz maliyeti (TTM / 5Ç ort.)', 'TTM / avg_5q', '−interest_on_funds_borrowed_ttm / avg5(funds_borrowed)',
    lambda p: guard([T('interest_on_funds_borrowed', p)] + [K('funds_borrowed', p - pd.offsets.QuarterEnd(k)) for k in range(5)], f"-{T('interest_on_funds_borrowed', p)}/{avg5('funds_borrowed', p)}") if avg5('funds_borrowed', p) else None)
for code, name in (('assets', 'Aktif'), ('loans', 'Kredi'), ('deposits', 'Mevduat')):
    base = {'assets': 'total_assets', 'loans': 'loans_gross', 'deposits': 'total_deposits'}[code]
    add(f'{code}_growth_qoq', f'{name} büyümesi (çeyreklik)', 'stock lag_1q', f'{base}[t]/{base}[t-1q] − 1',
        (lambda b: lambda p: guard([K(b, p), K(b, prev_q(p))], f"{K(b, p)}/{K(b, prev_q(p))}-1") if has(prev_q(p)) else None)(base), PCT1)
    add(f'{code}_growth_yoy', f'{name} büyümesi (yıllık)', 'stock lag_4q', f'{base}[t]/{base}[t-4q] − 1',
        (lambda b: lambda p: guard([K(b, p), K(b, yago(p))], f"{K(b, p)}/{K(b, yago(p))}-1") if has(yago(p)) else None)(base), PCT1)
add('equity_growth_yoy', 'Özkaynak büyümesi (yıllık)', 'stock lag_4q', 'total_equity[t]/total_equity[t-4q] − 1',
    lambda p: guard([K('total_equity', p), K('total_equity', yago(p))], f"{K('total_equity', p)}/{K('total_equity', yago(p))}-1") if has(yago(p)) else None, PCT1)
add('profit_growth_yoy', 'Net kâr büyümesi (yıllık, YTD/YTD)', 'flow_same_ytd_window', 'net_profit_ytd[t]/net_profit_ytd[t-4q] − 1',
    lambda p: guard([K('net_profit', p), K('net_profit', yago(p))], f"{K('net_profit', p)}/{K('net_profit', yago(p))}-1") if has(yago(p)) else None, PCT1)
add('profit_growth_q_yoy', 'Net kâr büyümesi (çeyrek, yıllık)', 'Q lag_4q', 'net_profit_q[t]/net_profit_q[t-4q] − 1',
    lambda p: guard([Q('net_profit', p), Q('net_profit', yago(p))], f"{Q('net_profit', p)}/{Q('net_profit', yago(p))}-1") if has(yago(p)) else None, PCT1)
add('nii_growth_q_yoy', 'NII büyümesi (çeyrek, yıllık)', 'Q lag_4q', 'nii_q[t]/nii_q[t-4q] − 1',
    lambda p: guard([Q('net_interest_income', p), Q('net_interest_income', yago(p))], f"{Q('net_interest_income', p)}/{Q('net_interest_income', yago(p))}-1") if has(yago(p)) else None, PCT1)
add('derivatives_growth_yoy', 'Türev nominal büyümesi (yıllık)', 'stock lag_4q', 'derivatives_notional[t]/[t-4q] − 1',
    lambda p: guard([K('derivatives_notional', p), K('derivatives_notional', yago(p))], f"{K('derivatives_notional', p)}/{K('derivatives_notional', yago(p))}-1") if has(yago(p)) else None, PCT1)

orow = {}
r = 5
for code, name, method, ftxt, gen, fmt in orat:
    orow[code] = r
    wo.cell(r, 1, code).font = fgrey; wo.cell(r, 2, name).font = fn; wo.cell(r, 3, method).font = fgrey; wo.cell(r, 4, ftxt).font = fgrey
    for p, j in ocol.items():
        f = gen(p)
        c = wo.cell(r, j, f if f is not None else '=""'); c.number_format = fmt; c.font = fn
    r += 1
wo.column_dimensions['A'].width = 24; wo.column_dimensions['B'].width = 46; wo.column_dimensions['C'].width = 22; wo.column_dimensions['D'].width = 4; wo.column_dimensions['E'].width = 2
for j in ocol.values(): wo.column_dimensions[L(j)].width = 9
wo.freeze_panes = wo.cell(5, OC0); wo.sheet_view.zoomScale = 90

# ------------------------------------------------------------------ Grafikler
wg = wb.create_sheet('Grafikler', index=wb.sheetnames.index('Oranlar') + 1)
wg['A1'] = 'Grafikler – kaynak: Kalemler / Kalemler_Q / Oranlar (formül). Stok grafikler 2021Ç3\'ten başlar (2021Ç1-Ç2 bilançosu yok); akım grafikler 2020Ç3\'ten.'; wg['A1'].font = fgrey
wg.sheet_view.showGridLines = False

p_stock = [p for p in periods if p >= pd.Timestamp('2021-09-30')]
p_flow = periods  # contiguous from 2020-09-30
p_ttm = [p for p in periods if p >= pd.Timestamp('2021-06-30')]
p_ttm5 = [p for p in periods if p >= pd.Timestamp('2022-09-30')]  # avg5 needs 5 contiguous quarter-ends from 2021-09-30

def nice_step(vmax, n=5):
    if vmax <= 0: return 1
    raw = vmax / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag: return m * mag
    return 10 * mag

def style_chart(ch, title, ylabel, yfmt='#,##0', ymax=None, ymin=None, legend=True, label_skip=1):
    ch.title = title
    ch.roundedCorners = False
    ch.style = 2
    ch.height = 8.5; ch.width = 17
    ch.x_axis.delete = False; ch.y_axis.delete = False
    ch.y_axis.title = ylabel
    ch.y_axis.number_format = yfmt
    ch.y_axis.majorGridlines = None
    from openpyxl.chart.axis import ChartLines
    ch.y_axis.majorGridlines = ChartLines()
    ch.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill='D9D9D9', w=6350))
    ch.x_axis.majorGridlines = None
    if ymax is not None:
        st = nice_step(ymax - (ymin or 0))
        ch.y_axis.scaling.max = math.ceil(ymax / st) * st
        ch.y_axis.scaling.min = (math.floor(ymin / st) * st) if ymin is not None and ymin < 0 else 0
        ch.y_axis.majorUnit = st
    ch.x_axis.tickLblSkip = label_skip
    ch.x_axis.tickLblPos = 'low'
    ch.x_axis.tickMarkSkip = label_skip
    ch.x_axis.number_format = 'General'
    cp = CharacterProperties(sz=800)
    ch.x_axis.txPr = RichText(bodyPr=None, p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])
    from openpyxl.drawing.text import RichTextProperties
    ch.x_axis.txPr.bodyPr = RichTextProperties(rot=0, vert='horz')
    ch.y_axis.txPr = RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])
    if legend:
        ch.legend.position = 'b'
    else:
        ch.legend = None
    ch.plot_area.layout = Layout(manualLayout=ManualLayout(x=0.08, y=0.14, h=0.62, w=0.88, xMode='edge', yMode='edge'))
    ch.x_axis.title = None

def series_vals(sheet, row, ps, colmap):
    return [sheet.cell(row, colmap[p]).value for p in ps]

# we need numeric extents for axis scaling -> compute from pandas quickly (approximate with python values)
def py_series(code_or_row_sheet, ps):
    """compute numeric values in python from u for scaling only."""
    pass

# helper to compute values in python for axis scaling: evaluate using pandas directly from u
pv = {}
def val(stmt, ccy, path, basis, p):
    x = u[(u.series_key == f"{stmt}|{ccy}|{path}") & (u.basis == basis) & (u.p_end == p)].value_mn
    return float(x.iloc[0]) if len(x) else np.nan
def kal(code, p):
    spec = [it for it in items if it[0] == code][0][5]
    if spec is None: return np.nan
    if isinstance(spec, tuple):
        return sum(s * kal(c_, p) for c_, s in spec[1])
    return sum(s * (0 if np.isnan(val(st, cc, path, b, p)) else val(st, cc, path, b, p)) for s, st, cc, path, b in spec) if not np.isnan(val(spec[0][1], spec[0][2], spec[0][3], spec[0][4], p)) or True else np.nan
def kalq(code, p):
    i = periods.index(p)
    if i == 0: return np.nan
    if p.month == 3: return kal(code, p)
    return kal(code, p) - kal(code, periods[i - 1])

charts = []
def add_chart(kind, title, ylabel, series, ps, colmap, sheetname, yfmt='#,##0', stacked=False, pyvals=None, pct=False, label_skip=1):
    """series: list of (row, name). ps: periods list. colmap: period->col in sheet."""
    sh = wb[sheetname]
    ch = BarChart() if kind == 'bar' else LineChart()
    if kind == 'bar':
        ch.type = 'col'; ch.gapWidth = 60
        if stacked: ch.grouping = 'stacked'; ch.overlap = 100
    # category labels: row 3 (quarter labels)
    c0, c1 = colmap[ps[0]], colmap[ps[-1]]
    cats = Reference(sh, min_col=c0, max_col=c1, min_row=3, max_row=3)
    for row, name in series:
        ref = Reference(sh, min_col=c0, max_col=c1, min_row=row, max_row=row)
        s = Series(ref, title=name)
        if kind == 'line':
            s.smooth = False; s.marker.symbol = 'none'; s.graphicalProperties.line.width = 19050
        ch.series.append(s)
    ch.set_categories(cats)
    # scaling
    ymax = ymin = None
    if pyvals is not None:
        arr = np.array(pyvals, dtype=float); arr = arr[~np.isnan(arr)]
        if len(arr):
            ymax = float(arr.max()); ymin = float(arr.min())
            if ymax <= 0: ymax = 0
    style_chart(ch, title, ylabel, yfmt, ymax, ymin, legend=len(series) > 1, label_skip=label_skip)
    charts.append(ch)

# ---- data for scaling
S = lambda code: [kal(code, p) for p in p_stock]
SQ = lambda code: [kalq(code, p) for p in p_flow[1:]]
# 1 Toplam aktif & özkaynak
add_chart('line', 'Toplam aktifler (mn TL)', 'mn TL', [(code_row['total_assets'], 'Toplam aktifler')], p_stock, pcol, 'Kalemler', pyvals=S('total_assets'))
# 2 Aktif kompozisyonu stacked
comp = [('cash_and_central_bank', 'Nakit ve TCMB'), ('due_from_banks', 'Bankalar'), ('money_market_receivables', 'Para piyasası'), ('securities_portfolio', 'Menkul kıymetler'), ('loans_gross', 'Krediler (brüt)'), ('derivative_assets', 'Türev varlıklar'), ('other_assets', 'Diğer aktifler')]
add_chart('bar', 'Aktif kompozisyonu (mn TL)', 'mn TL', [(code_row[c], n) for c, n in comp], p_stock, pcol, 'Kalemler', stacked=True, pyvals=[sum(kal(c, p) for c, _ in comp) for p in p_stock])
# 3 Pasif kompozisyonu stacked
compl = [('total_deposits', 'Mevduat'), ('funds_borrowed', 'Alınan krediler'), ('money_market_funds', 'Para piyasası'), ('derivative_liabilities', 'Türev yükümlülükler'), ('provisions', 'Karşılıklar'), ('tax_liabilities', 'Vergi borcu'), ('other_liabilities', 'Diğer yükümlülükler'), ('total_equity', 'Özkaynaklar')]
add_chart('bar', 'Pasif kompozisyonu (mn TL)', 'mn TL', [(code_row[c], n) for c, n in compl], p_stock, pcol, 'Kalemler', stacked=True, pyvals=[sum(kal(c, p) for c, _ in compl) for p in p_stock])
# 4 Krediler TP/YP
add_chart('bar', 'Brüt krediler – TP / YP (mn TL)', 'mn TL', [(code_row['loans_tl'], 'TP krediler'), (code_row['loans_fx'], 'YP krediler')], p_stock, pcol, 'Kalemler', stacked=True, pyvals=S('loans_gross'))
# 5 Mevduat TP/YP
add_chart('bar', 'Mevduat – TP / YP (mn TL)', 'mn TL', [(code_row['deposits_tl'], 'TP mevduat'), (code_row['deposits_fx'], 'YP mevduat')], p_stock, pcol, 'Kalemler', stacked=True, pyvals=S('total_deposits'))
# 6 Alınan krediler TP/YP
add_chart('bar', 'Alınan krediler – TP / YP (mn TL)', 'mn TL', [(code_row['funds_borrowed_tl'], 'TP'), (code_row['funds_borrowed_fx'], 'YP')], p_stock, pcol, 'Kalemler', stacked=True, pyvals=S('funds_borrowed'))
# 7 Nakit ve TCMB TP/YP + menkul
add_chart('line', 'Likit aktifler (mn TL)', 'mn TL', [(code_row['cash_cb_tl'], 'Nakit+TCMB TP'), (code_row['cash_cb_fx'], 'Nakit+TCMB YP'), (code_row['due_from_banks'], 'Bankalar'), (code_row['securities_portfolio'], 'Menkul kıymetler')], p_stock, pcol, 'Kalemler', pyvals=S('cash_cb_tl') + S('cash_cb_fx') + S('due_from_banks') + S('securities_portfolio'))
# 8 Özkaynak kompozisyonu
compe = [('paid_in_capital', 'Ödenmiş sermaye'), ('capital_reserves', 'Sermaye yedekleri'), ('oci_accumulated', 'Birikmiş OCI'), ('profit_reserves', 'Kâr yedekleri'), ('net_profit_bs', 'Dönem net kârı')]
add_chart('bar', 'Özkaynak kompozisyonu (mn TL)', 'mn TL', [(code_row[c], n) for c, n in compe], p_stock, pcol, 'Kalemler', stacked=True, pyvals=S('total_equity'))
# 9 Türev nominal
compd = [('fx_forwards_notional', 'Vadeli döviz'), ('swaps_notional', 'Para+faiz swap'), ('futures_notional', 'Futures')]
add_chart('bar', 'Türev nominal (nazım, mn TL)', 'mn TL', [(code_row[c], n) for c, n in compd], p_stock, pcol, 'Kalemler', stacked=True, pyvals=S('derivatives_notional'))
# 10 Swap para alım TP bacak vs satım YP bacak + alınan krediler YP
add_chart('line', 'Swap bacakları ve YP borçlanma (mn TL)', 'mn TL', [(code_row['ccy_swap_buy_tl'], 'Swap para alım – TP'), (code_row['ccy_swap_sell_fx'], 'Swap para satım – YP'), (code_row['funds_borrowed_fx'], 'Alınan krediler – YP')], p_stock, pcol, 'Kalemler', pyvals=S('ccy_swap_buy_tl') + S('ccy_swap_sell_fx') + S('funds_borrowed_fx'))
# 11 Garanti / taahhüt / emanet
add_chart('line', 'Garanti, taahhüt, müşteri portföyü (mn TL)', 'mn TL', [(code_row['guarantees'], 'Garanti ve kefaletler'), (code_row['commitments'], 'Taahhütler'), (code_row['client_funds_portfolio'], 'Müşteri fon ve portföy')], p_stock, pcol, 'Kalemler', pyvals=S('guarantees') + S('commitments') + S('client_funds_portfolio'))
# ---- flows quarterly
pq = p_flow[1:]
# 12 NII quarterly with components
add_chart('bar', 'Çeyreklik faiz gelir/gider ve NII (mn TL)', 'mn TL', [(qrow['interest_income'], 'Faiz gelirleri'), (qrow['interest_expense'], 'Faiz giderleri'), (qrow['net_interest_income'], 'Net faiz geliri')], pq, qcol, 'Kalemler_Q', pyvals=SQ('interest_income') + SQ('interest_expense'))
# 13 Faiz gelir kompozisyonu
compi = [('interest_on_loans', 'Krediler'), ('interest_from_banks', 'Bankalar'), ('interest_from_money_market', 'Para piyasası'), ('interest_on_securities', 'Menkul'), ('other_interest_income', 'Diğer')]
add_chart('bar', 'Çeyreklik faiz geliri kompozisyonu (mn TL)', 'mn TL', [(qrow[c], n) for c, n in compi], pq, qcol, 'Kalemler_Q', stacked=True, pyvals=SQ('interest_income'))
# 14 Faiz gider kompozisyonu
compx = [('interest_on_deposits', 'Mevduat'), ('interest_on_funds_borrowed', 'Alınan krediler'), ('interest_on_money_market', 'Para piyasası'), ('other_interest_expense', 'Diğer')]
add_chart('bar', 'Çeyreklik faiz gideri kompozisyonu (mn TL, negatif)', 'mn TL', [(qrow[c], n) for c, n in compx], pq, qcol, 'Kalemler_Q', stacked=True, pyvals=SQ('interest_expense'))
# 15 Gelir karması
compr = [('net_interest_income', 'NII'), ('net_fee_commission_income', 'Net ücret'), ('trading_income', 'Ticari K/Z'), ('other_operating_income', 'Diğer')]
add_chart('bar', 'Çeyreklik gelir karması (mn TL)', 'mn TL', [(qrow[c], n) for c, n in compr], pq, qcol, 'Kalemler_Q', stacked=True, pyvals=SQ('net_interest_income') + SQ('trading_income') + SQ('total_revenue'))
# 16 Ticari K/Z breakdown
compt = [('trading_securities', 'Sermaye piyasası'), ('trading_derivatives', 'Türev'), ('trading_fx', 'Kambiyo')]
add_chart('bar', 'Çeyreklik ticari K/Z kırılımı (mn TL)', 'mn TL', [(qrow[c], n) for c, n in compt], pq, qcol, 'Kalemler_Q', stacked=True, pyvals=SQ('trading_securities') + SQ('trading_derivatives') + SQ('trading_fx') + SQ('trading_income'))
# 17 NII + trading combined vs net profit
add_chart('line', 'NII + Ticari K/Z vs net kâr (çeyrek, mn TL)', 'mn TL', [(orow['nii_plus_trading_q'], 'NII + Ticari K/Z'), (qrow['net_interest_income'], 'NII'), (qrow['net_profit'], 'Net kâr')], pq, ocol if False else qcol, 'Kalemler_Q', pyvals=SQ('net_interest_income') + SQ('net_profit'))
# fix: first series lives in Oranlar -> rebuild that chart with mixed sheets
charts.pop()
ch = LineChart()
c0, c1 = qcol[pq[0]], qcol[pq[-1]]
for sheetname, row, name, cm in (('Oranlar', orow['nii_plus_trading_q'], 'NII + Ticari K/Z', ocol), ('Kalemler_Q', qrow['net_interest_income'], 'NII', qcol), ('Kalemler_Q', qrow['net_profit'], 'Net kâr', qcol)):
    sh = wb[sheetname]
    ref = Reference(sh, min_col=cm[pq[0]], max_col=cm[pq[-1]], min_row=row, max_row=row)
    s = Series(ref, title=name); s.smooth = False; s.marker.symbol = 'none'; s.graphicalProperties.line.width = 19050
    ch.series.append(s)
ch.set_categories(Reference(wb['Kalemler_Q'], min_col=c0, max_col=c1, min_row=3, max_row=3))
arr = np.array(SQ('net_interest_income') + SQ('net_profit') + [kalq('net_interest_income', p) + kalq('trading_income', p) for p in pq]); arr = arr[~np.isnan(arr)]
style_chart(ch, 'NII + Ticari K/Z vs net kâr (çeyrek, mn TL)', 'mn TL', '#,##0', float(arr.max()), float(arr.min()))
charts.append(ch)
# 18 Opex & provisions
add_chart('bar', 'Çeyreklik faaliyet giderleri ve karşılıklar (mn TL, negatif)', 'mn TL', [(qrow['personnel_expenses'], 'Personel'), (qrow['other_operating_expenses'], 'Diğer faaliyet'), (qrow['provision_expenses'], 'Karşılıklar')], pq, qcol, 'Kalemler_Q', stacked=True, pyvals=SQ('operating_expenses') + SQ('provision_expenses'))
# 19 Net kâr & vergi
add_chart('bar', 'Çeyreklik vergi öncesi kâr, vergi, net kâr (mn TL)', 'mn TL', [(qrow['profit_before_tax'], 'Vergi öncesi kâr'), (qrow['tax_provision'], 'Vergi'), (qrow['net_profit'], 'Net kâr')], pq, qcol, 'Kalemler_Q', pyvals=SQ('profit_before_tax') + SQ('tax_provision'))
# ---- ratios
def R(code, ps): return (orow[code], ps)
def pyr(expr_fn, ps): return [expr_fn(p) for p in ps]
# 20 ROA/ROE Blanco (needs prev year end -> from 2021-09-30 since 2020-12-31 exists)
p_r = [p for p in periods if p >= pd.Timestamp('2021-09-30')]
def ann_py(code, p): return kal(code, p) * 4 / ((p.month - 1) // 3 + 1)
def avg2_py(code, p): return (kal(code, p) + kal(code, prev_ye(p))) / 2
add_chart('line', 'ROE ve ROA – Blanco yöntemi (YTD×4/q, 2 nokta ort.)', '%', [(orow['roe'], 'ROE'), (orow['roa'], 'ROA')], p_r, ocol, 'Oranlar', yfmt='0%', pyvals=[ann_py('net_profit', p) / avg2_py('total_equity', p) for p in p_r] + [0])
# 21 ROE/ROA TTM
add_chart('line', 'ROE ve ROA – TTM / 5 çeyrek ortalama', '%', [(orow['roe_ttm'], 'ROE TTM'), (orow['roa_ttm'], 'ROA TTM')], p_ttm5, ocol, 'Oranlar', yfmt='0%', pyvals=[sum(kalq('net_profit', p - pd.offsets.QuarterEnd(k)) for k in range(4)) / np.mean([kal('total_equity', p - pd.offsets.QuarterEnd(k)) for k in range(5)]) for p in p_ttm5] + [0])
# 22 NIM
add_chart('line', 'Net faiz marjı', '%', [(orow['nim_iea_ttm'], 'NIM – faiz getirili aktif, TTM'), (orow['nim'], 'NIM – toplam aktif, Blanco'), (orow['nim_q_ann'], 'NIM – çeyrek×4 / dönem sonu aktif')], p_r, ocol, 'Oranlar', yfmt='0.0%', pyvals=[ann_py('net_interest_income', p) / avg2_py('total_assets', p) for p in p_r] + [kalq('net_interest_income', p) * 4 / kal('total_assets', p) for p in p_r] + [0])
# 23 CIR
add_chart('line', 'Gider/Gelir oranı', '%', [(orow['cost_to_income'], 'CIR YTD'), (orow['cost_to_income_q'], 'CIR çeyrek')], p_flow[1:], ocol, 'Oranlar', yfmt='0%', pyvals=[-kalq('operating_expenses', p) / kalq('total_revenue', p) for p in p_flow[1:]] + [0])
# 24 Balance sheet structure ratios
add_chart('line', 'Bilanço yapısı', '%', [(orow['loans_to_assets'], 'Kredi/Aktif'), (orow['deposits_to_assets'], 'Mevduat/Aktif'), (orow['funds_borrowed_to_assets'], 'Alınan krediler/Aktif'), (orow['cash_to_assets'], 'Nakit/Aktif'), (orow['equity_to_assets'], 'Özkaynak/Aktif')], p_stock, ocol, 'Oranlar', yfmt='0%', pyvals=[kal('cash_to_assets' if False else 'cash_and_cash_equivalents', p) / kal('total_assets', p) for p in p_stock] + [0])
# 25 FX shares
add_chart('line', 'YP payları', '%', [(orow['fx_assets_share'], 'YP aktif'), (orow['fx_liabilities_share'], 'YP pasif'), (orow['fx_loans_share'], 'YP kredi'), (orow['fx_deposits_share'], 'YP mevduat')], p_stock, ocol, 'Oranlar', yfmt='0%', pyvals=[1, 0])
# 26 L/D & derivatives/assets
add_chart('line', 'Kredi/Mevduat ve türev nominal/aktif', 'x / %', [(orow['loan_to_deposit_ratio'], 'Kredi/Mevduat'), (orow['derivatives_to_assets'], 'Türev nominal / Aktif (x)')], p_stock, ocol, 'Oranlar', yfmt='0.0', pyvals=[kal('derivatives_notional', p) / kal('total_assets', p) for p in p_stock] + [0])
# 27 Yields
add_chart('line', 'Efektif getiri / maliyet (TTM / 5Ç ort. bakiye)', '%', [(orow['int_yield_loans_ttm'], 'Kredi faiz getirisi'), (orow['int_cost_deposits_ttm'], 'Mevduat faiz maliyeti'), (orow['int_cost_funds_borrowed_ttm'], 'Alınan kredi faiz maliyeti')], p_ttm5, ocol, 'Oranlar', yfmt='0%', pyvals=[sum(kalq('interest_on_loans', p - pd.offsets.QuarterEnd(k)) for k in range(4)) / np.mean([kal('loans_gross', p - pd.offsets.QuarterEnd(k)) for k in range(5)]) for p in p_ttm5] + [0])
# 28 Growth YoY
p_g = [p for p in periods if p >= pd.Timestamp('2022-09-30')]
add_chart('line', 'Yıllık büyüme (stok)', '%', [(orow['assets_growth_yoy'], 'Aktif'), (orow['loans_growth_yoy'], 'Kredi'), (orow['deposits_growth_yoy'], 'Mevduat'), (orow['equity_growth_yoy'], 'Özkaynak')], p_g, ocol, 'Oranlar', yfmt='0%', pyvals=[kal(c, p) / kal(c, yago(p)) - 1 for p in p_g for c in ('total_assets', 'loans_gross', 'total_deposits', 'total_equity')])
# 29 Profit growth
p_pg = [p for p in periods if p >= pd.Timestamp('2021-09-30')]
add_chart('bar', 'Net kâr ve NII büyümesi (çeyrek, yıllık)', '%', [(orow['profit_growth_q_yoy'], 'Net kâr çeyrek YoY'), (orow['nii_growth_q_yoy'], 'NII çeyrek YoY')], p_pg, ocol, 'Oranlar', yfmt='0%', pyvals=[kalq('net_profit', p) / kalq('net_profit', yago(p)) - 1 for p in p_pg] + [kalq('net_interest_income', p) / kalq('net_interest_income', yago(p)) - 1 for p in p_pg])
# 30 Effective tax
add_chart('line', 'Efektif vergi oranı (YTD)', '%', [(orow['effective_tax_rate'], 'Efektif vergi oranı')], p_flow, ocol, 'Oranlar', yfmt='0%', pyvals=[-kal('tax_provision', p) / kal('profit_before_tax', p) for p in p_flow] + [0])
# 31 ECL total & CoR
add_chart('bar', 'Beklenen kredi zararı karşılığı stoku (mn TL)', 'mn TL', [(code_row['ecl_total_tfrs9'], 'Toplam BZK (bilanço)')], p_stock, pcol, 'Kalemler', pyvals=S('ecl_total_tfrs9'))
add_chart('line', 'Kredi risk maliyeti (CoR, Blanco)', '%', [(orow['cost_of_risk'], 'CoR')], p_r, ocol, 'Oranlar', yfmt='0.00%', pyvals=[-ann_py('expected_credit_loss_expense', p) / avg2_py('loans_gross', p) for p in p_r] + [0])

# place charts in 2-column grid
for i, ch in enumerate(charts):
    row = 3 + (i // 2) * 18
    col = 'A' if i % 2 == 0 else 'L'
    wg.add_chart(ch, f'{col}{row}')

# README append
wr = wb['README']
extra = [
 '',
 'ANALİZ KATMANI (Blanco veri sözlüğü yerine)',
 'Kalemler   : Blanco data_dictionary.yaml kalem kodları → KAP series_key eşlemesi; status VERIFIED (KAP ana tablo satırı) / DERIVED (bileşenlerden formül) / UNAVAILABLE (ana tabloda yok, kaynak notta). Tüm değerler DB sayfasından SUMIFS.',
 'Kalemler_Q : Gelir tablosu kalemleri bağımsız çeyrek (YTD farkı) ve TTM.',
 'Oranlar    : ROA/ROE/NIM/CIR/CoR/büyüme — Blanco calc/engine.py yöntemleri (ytd_x4q, avg_2pt, lag_1q/lag_4q, flow_same_ytd_window) + TTM/5Ç ortalama varyantları ve KAP\'a özgü ek oranlar (YP payları, türev/aktif, efektif getiri-maliyet).',
 'Grafikler  : 32 grafik; stoklar 2021Ç3\'ten, akımlar 2020Ç4\'ten (boş dönem çizilmez).',
]
r0 = wr.max_row + 1
for i, t in enumerate(extra):
    wr.cell(r0 + i, 1, t).font = fb if t.isupper() and t else fn

wb.calculation.fullCalcOnLoad = True
wb.save(OUT)
print('ok items', len(items), 'ratios', len(orat), 'charts', len(charts))
