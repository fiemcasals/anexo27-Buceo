# Como volver atras el plan 1

Escrito el 2026-11-04, al integrar y pushear el plan 1. Todo lo que esta aca es reversible.
Los SHA son exactos, no hay que buscarlos.

## Los puntos fijos

| Que | SHA | Que es |
|---|---|---|
| **Antes de todo** | `8d3f8d385d2b597fd5778bfd9d11d3f0a9579cc1` | `main` y `origin/main` antes del plan 1. Tambien marcado con el tag **`antes-del-plan-1`**. Su mensaje: "Fix user instance assignment in create_test_data script" |
| **El merge** | `4c70bd1f03e5d6481405f3268663a71e43a62c89` | "merge: plan 1 — cimientos del dominio de aptitud". Hecho con `--no-ff`, asi que los 45 commits cuelgan de el y se revierten juntos |
| **Este documento** | `6ad2ef2` | "docs: rescatar los informes del plan 1 y anotar como volver atras". Va **encima** del merge, asi que revertir el merge no lo saca |

El push se hizo el 2026-11-04: `origin/main` paso de `8d3f8d3` a `6ad2ef2`, 47 commits, en
fast-forward (no se reescribio nada).

> **El tag `antes-del-plan-1` es local.** Existe solo en esta maquina; no se pusheo. Desde otra
> computadora hay que usar el SHA `8d3f8d38` directamente, o traerlo con
> `git push origin antes-del-plan-1`.

Copia de la base de datos de antes del merge, **fuera del repo** (asi sobrevive a un
`reset --hard`):

```
C:\Users\nicol\Documents\Proyectos\anexo27-db-antes-del-plan-1.sqlite3
```

## Caso 1 — deshacer en tu maquina y en el remoto, de forma segura

Es la opcion recomendada en un repo compartido: no reescribe historia, asi que a nadie que
haya hecho `pull` se le rompe nada. Deja el trabajo en el historial y agrega un commit que
lo anula.

```bash
cd /c/Users/nicol/Documents/Proyectos/anexo27-Buceo
git checkout main
git revert -m 1 4c70bd1
git push origin main
```

El `-m 1` le dice a git que el lado que se conserva es `main` como estaba antes del merge.

**Ojo con lo que este camino NO deshace:** revertir el merge saca los 45 commits del plan, pero
deja en pie `6ad2ef2`, que es el que trae los informes y **este mismo documento**. Normalmente es
lo que querés —si volviste atras, estas instrucciones son justo lo que necesitas tener a mano—
pero si buscas que no quede rastro, eso es el Caso 2 o el 3.

Si despues te arrepentis y lo querés de vuelta, se revierte el revert:

```bash
git revert <sha-del-revert>
git push origin main
```

## Caso 2 — borrarlo del remoto como si nunca hubiera pasado

**Reescribe historia compartida.** El repo es `github.com/fiemcasals/anexo27-Buceo`, que no
es tu cuenta: si alguien ya hizo `pull` de estos commits, esto le rompe su copia. Usalo solo
si estas seguro de que nadie los bajo todavia.

```bash
cd /c/Users/nicol/Documents/Proyectos/anexo27-Buceo
git checkout main
git reset --hard antes-del-plan-1
git push --force-with-lease origin main
```

`--force-with-lease` y no `--force`: aborta si el remoto se movio desde tu ultimo `fetch`,
que es justo la situacion en la que pisarlo seria destructivo.

## Caso 3 — deshacer solo en tu maquina, dejando el remoto como esta

```bash
git checkout main
git reset --hard antes-del-plan-1
```

El trabajo sigue en el remoto y lo recuperas con `git pull`.

## Deshacer un solo arreglo, no todo el plan

Los cambios de seguridad del cierre son siete commits independientes y cada uno se revierte
solo:

```
1a002ea  refactor(api): es_revisor pasa a su propio modulo
1a0a883  fix(api): el rol lo designa el admin, no su propio dueno
b54742e  fix(api): el dictamen se firma con el rol real, no con el declarado
3ddc4b2  fix(api): dictaminar exige seguir designado, no haberlo estado
d09042a  fix(api): el Anexo 27 y access_level salen del rol
7d426fe  docs: registrar el segundo pase del item 4
a7cb8b9  docs: D-6, los estudios marcados "g" no se recuperan
```

```bash
git revert <sha>
```

El de `es_revisor` (`1a002ea`) es el unico del que dependen los otros: si vas a revertir
varios, hacelo en orden inverso al de arriba.

## La base de datos no vuelve atras con git

`backend/db.sqlite3` esta en `.gitignore`: git **nunca** la toca. Revertir el codigo no
deshace una migracion ya aplicada.

El plan 1 trae **16 migraciones**, y dos de ellas mueven datos con `RunPython.noop` como
reversa — Django las desaplica sin protestar y **sin restaurar nada**:

- `api/0014_demote_duplicate_current_studies`
- `api/0015_backfill_rejection_reason_and_detail`

Para volver atras la base, el camino es reemplazar el archivo por la copia:

```bash
cp /c/Users/nicol/Documents/Proyectos/anexo27-db-antes-del-plan-1.sqlite3 \
   /c/Users/nicol/Documents/Proyectos/anexo27-Buceo/backend/db.sqlite3
```

Si no existiera esa copia, la base se recrea desde cero:

```bash
cd backend
rm db.sqlite3
./venv/Scripts/python.exe manage.py migrate
SEED_CONFIRM=1 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 ./venv/Scripts/python.exe manage.py shell -c "exec(open('create_test_data.py', encoding='utf-8').read())"
```

Ese `-c "exec(...)"` no es capricho: con `manage.py shell < create_test_data.py` la consola
interactiva pierde las variables entre bloques separados por lineas en blanco y la siembra sale
mal. Lo aclara el propio docstring del script.

`SEED_CONFIRM=1` es una traba a proposito: el script **borra** los usuarios de su lista con todo
lo asociado, asi que si la base tuviera un `admin` de verdad se lo lleva. Antes de borrar imprime
que usuarios va a destruir.

Perdes lo cargado, que hoy es solo data de prueba (ver D-6).

## Si recuperaste el estado viejo y no sabes si quedo bien

```bash
cd backend
./venv/Scripts/python.exe manage.py test
./venv/Scripts/python.exe manage.py makemigrations --check --dry-run
```

Con el plan 1 puesto: **220 tests** y "No changes detected".
En `antes-del-plan-1`: la suite es mucho mas chica, porque casi todo lo que la llena entro
con este plan.

## Donde esta el resto del contexto

- Decisiones en firme (D-1 a D-6): `docs/superpowers/specs/2026-11-03-decisiones-posteriores.md`
- Por que el codigo quedo asi: `docs/superpowers/informes/2026-11-03-cimientos-dominio-aptitud/`
- El diseno aprobado: `docs/superpowers/specs/2026-11-03-control-aptitud-medica-design.md`
