#!/usr/bin/env bash
# Despliega Anexo Buceo en buceo.nuestrocamino.cloud.
#
# Uso: ./deploy.sh [rama]     (por defecto, la rama que ya esta checkouteada)
#
# El checkout de este directorio ES produccion: el codigo esta horneado en las
# imagenes, asi que nada cambia hasta el build. db.sqlite3 y media/ estan
# bind-mounteados y en .gitignore, por eso el pull no los puede pisar -- pero las
# migraciones si, de ahi el backup de la primera linea.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

RAMA="${1:-$(git rev-parse --abbrev-ref HEAD)}"
SITIO="https://buceo.nuestrocamino.cloud"

log() { printf '\n==> %s\n' "$*"; }

# --- backup ---------------------------------------------------------------
# Va antes de todo: es el unico camino de vuelta si una migracion sale mal.
# La API .backup de sqlite3 y no un cp, porque la base esta abierta por gunicorn.
log "Backup de la base"
BACKUP=$(python3 - <<'PY'
import sqlite3, time
dst = f"backend/db.sqlite3.bak-predeploy-{time.strftime('%Y%m%d-%H%M%S')}"
src = sqlite3.connect("backend/db.sqlite3")
d = sqlite3.connect(dst)
with d:
    src.backup(d)
d.close(); src.close()
print(dst)
PY
)
echo "    $BACKUP"
# Sin rotacion esto crece un archivo por deploy, y con el autodeploy son
# muchos mas que antes. Los 10 ultimos alcanzan para volver atras; el historico
# largo lo guarda backup.sh en datos/.
ls -t backend/db.sqlite3.bak-predeploy-* 2>/dev/null | tail -n +11 | xargs -r rm --

# --- traer el codigo ------------------------------------------------------
ANTES="$(git rev-parse HEAD)"
log "Actualizando $RAMA"
# --ff-only: si quedo algo editado a mano en este checkout, que falle ruidoso en
# vez de pisarlo. Ya paso -- AuditorScope vivio sin commitear una semana.
git pull --ff-only origin "$RAMA"
AHORA="$(git rev-parse HEAD)"
if [ "$ANTES" = "$AHORA" ]; then
    echo "    sin cambios de codigo ($(git rev-parse --short HEAD)), rebuild igual"
else
    echo "    $(git rev-parse --short "$ANTES") -> $(git rev-parse --short "$AHORA")"
    git log --oneline "$ANTES..$AHORA" | sed 's/^/      /'
fi

# --- build ----------------------------------------------------------------
# El VPS corre ~50 contenedores con 7.8 GB: el build de vite es lo que mas
# aprieta. Hay 2 GB de swap puestos para que un pico no se lleve puesto al resto.
log "Build de las imagenes"
docker compose build

# --- migraciones ----------------------------------------------------------
# Dentro de la imagen nueva, contra la base de produccion (el compose la monta).
log "Migraciones"
docker compose run --rm backend python manage.py migrate --noinput

# --- levantar -------------------------------------------------------------
log "Levantando"
docker compose up -d

# --- verificar ------------------------------------------------------------
# Contra el dominio publico: prueba la cadena entera (proxy -> nginx -> gunicorn),
# no solo que el contenedor arranco. El 401 del API es la respuesta correcta sin
# credenciales; un 502 seria el backend caido.
log "Verificando $SITIO"
ok=0
for _ in $(seq 1 30); do
    home=$(curl -s -o /dev/null -w '%{http_code}' "$SITIO/" || true)
    api=$(curl -s -o /dev/null -w '%{http_code}' "$SITIO/api/profiles/" || true)
    if [ "$home" = "200" ] && [ "$api" = "401" ]; then
        echo "    home $home · api $api"
        ok=1; break
    fi
    sleep 2
done

if [ "$ok" = "1" ]; then
    log "Desplegado: $(git rev-parse --short HEAD)"
    exit 0
fi

# --- rollback -------------------------------------------------------------
echo "    home ${home:-?} · api ${api:-?} -- no quedo sirviendo en 60s"
docker compose logs --tail 40
log "ROLLBACK a $(git rev-parse --short "$ANTES")"
cp "$BACKUP" backend/db.sqlite3
git reset --hard "$ANTES"
docker compose build
docker compose up -d
echo
echo "Volvi a $(git rev-parse --short HEAD) y restaure la base desde $BACKUP."
echo "El despliegue fallido quedo en los logs de arriba."
exit 1
