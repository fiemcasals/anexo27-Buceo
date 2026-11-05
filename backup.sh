#!/bin/bash
# Respaldo diario de Anexo Buceo: base SQLite + media/, 14 dias de retencion.
# Mismo esquema que /root/malvinas/backup.sh, sin el espejo en Drive.
# Cron:  15 3 * * *  /root/anexo27-Buceo/anexo27-Buceo/backup.sh >> /root/anexo27-Buceo/anexo27-Buceo/datos/backup.log 2>&1
set -u
cd "$(dirname "$(readlink -f "$0")")"

DEST=datos
STAMP=$(date +%Y%m%d)
mkdir -p "$DEST"

# .backup() de SQLite y no un cp: la base esta abierta por gunicorn.
# Desde el host, que ya tiene python3 con sqlite3; el contenedor no monta datos/.
python3 -c "
import sqlite3
o = sqlite3.connect('backend/db.sqlite3')
d = sqlite3.connect('$DEST/db-$STAMP.sqlite3')
with d: o.backup(d)
d.close(); o.close()
" || { echo "$(date +%F) ERROR: no se pudo respaldar la base"; exit 1; }

gzip -f "$DEST/db-$STAMP.sqlite3"
tar czf "$DEST/media-$STAMP.tar.gz" -C backend media 2>/dev/null

find "$DEST" -name 'db-*.sqlite3.gz' -mtime +14 -delete
find "$DEST" -name 'media-*.tar.gz' -mtime +14 -delete

printf '%s\tdb=%s\tmedia=%s\tdatos=%s\n' "$(date +%F)" \
  "$(du -h backend/db.sqlite3 | cut -f1)" \
  "$(du -sh backend/media 2>/dev/null | cut -f1)" \
  "$(du -sh $DEST | cut -f1)" >> "$DEST/crecimiento.log"
