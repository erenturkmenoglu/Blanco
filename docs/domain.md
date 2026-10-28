# Alan adı kontrolü — bilanço.versel.app

**Punycode:** `bilanço.versel.app` → `xn--bilano-0ua.versel.app` (Python `str.encode("idna")` ile hesaplandı).
Tarayıcılar IDN'i Unicode gösterir; DNS/TLS/CDN tarafında ASCII (xn--) biçimi kullanılır. Sertifika (Let's Encrypt vb.) xn-- adına kesilir.

**Bu ortamdan DNS doğrulaması YAPILAMADI** (sandbox dış DNS'i çözmüyor: `versel.app`, `vercel.app` dahil hepsi "Name or service not known").
Aşağıdakiler kontrol edilmeli:

1. `versel.app` ≠ `vercel.app`. Vercel'in ücretsiz alt alan adı `*.vercel.app`'tir. `versel.app` ayrı bir kayıtlı alan adıdır (size ait değilse
   kullanılamaz). Yazım hatasıysa hedef `vercel.app`'tir.
2. `*.vercel.app` alt alan adları yalnızca ASCII (a-z, 0-9, -) olabilir → `bilanço.vercel.app` **mümkün değil**; `bilanco.vercel.app` (müsaitse) mümkün.
3. IDN istenirse: kendi alan adınız (ör. `bilanço.app`, `bilanço.com.tr`) kayıt ettirilip Vercel'e **özel alan adı** olarak `xn--bilano-0ua.<tld>`
   biçiminde eklenir; CNAME `cname.vercel-dns.com`. `.app` TLD'si HSTS-preloaded olduğundan HTTPS zorunludur (Vercel otomatik sağlar).

**Öneri (ürün adı değişmez):** Ürün/markalama "Bilanço"; teknik ana makine `bilanco.vercel.app` (varsayılan) + isteğe bağlı IDN özel alan adı.
Açık soru: "versel" bilinçli bir tercih mi (size ait bir alan adı mı), yoksa "vercel" mi kastedildi?
