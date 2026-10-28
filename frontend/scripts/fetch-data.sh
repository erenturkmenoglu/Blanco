#!/usr/bin/env bash
# Vercel build adımı: veri snapshot'ını (GitHub Actions ingest'in yayımladığı web-data.tar.gz) public/data altına açar.
# Repo public olduğu için raw.githubusercontent.com üzerinden anahtar gerekmeden indirilir; yoksa site boş snapshot ile derlenir.
set -e
URL="${DATA_BUNDLE_URL:-https://raw.githubusercontent.com/erenturkmenoglu/Blanco/data/web-data.tar.gz}"
mkdir -p public
if curl -fsSL "$URL" -o /tmp/web-data.tar.gz; then
  rm -rf public/data && tar -xzf /tmp/web-data.tar.gz -C public
  echo "data snapshot: $(find public/data -type f | wc -l) dosya ($(du -sh public/data | cut -f1))"
else
  echo "UYARI: veri snapshot'ı alınamadı ($URL) — site boş veriyle derleniyor"
  mkdir -p public/data
fi
