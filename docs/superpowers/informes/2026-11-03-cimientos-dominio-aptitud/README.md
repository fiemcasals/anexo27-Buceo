# Informes del plan 1 — Cimientos del dominio de aptitud

Registro de como se construyo el plan 1, rescatado del workspace de trabajo
(`.superpowers/sdd/`, que esta en `.gitignore`) antes de borrarlo al cerrar la rama
`nicolas/primer-cambio`.

Se versiona porque es el unico lugar donde queda escrito **por que** el codigo quedo como
quedo: que se verifico, que se encontro, que se decidio no hacer y con que fundamento. Las
decisiones en firme viven aparte, en
[`../../specs/2026-11-03-decisiones-posteriores.md`](../../specs/2026-11-03-decisiones-posteriores.md)
(D-1 a D-6); esto es el detalle que las respalda.

Merge del plan: `4c70bd1`. 45 commits, 220 tests.

## Por donde empezar

| Archivo | Que es |
|---|---|
| `progress.md` | La bitacora de la construccion, tarea por tarea. Es el hilo conductor. |
| `final-review-fix-report-3.md` | **El mas util.** La re-revision final y el segundo pase del item 4: los cuatro endpoints del acceso por rol, los controles de mutacion y la verificacion con la app corriendo. |
| `final-review-fixes.md` → `final-review-fix-report.md` → `-2.md` | Las rondas anteriores de revision final, en orden. |
| `fix-brief-3.md` | El encargo que produjo el anteultimo pase. |
| `task-N-brief.md` / `task-N-report.md` | Lo que se le pidio a cada tarea y lo que reporto. N de 1 a 7. |
| `REANUDAR.md` | El estado al reanudar entre sesiones. Historico: la rama ya esta cerrada. |
| `pendiente-nombres-castellano.md` | Nota suelta sobre los nombres en castellano del admin. |

## Lo que no se copio

**Los 18 `review-*.diff` (484 KB).** Son `git diff` de rangos de commits, asi que se
regeneran exactos cuando haga falta:

```bash
git diff <rango> > review-<rango>.diff
```

Rangos que existian, en el orden en que se produjeron:

```
13b4391..6c88518   6c88518..2d429e3   2d429e3..951be16   951be16..441db91
441db91..c30cf10   c30cf10..acfd92c   acfd92c..a4123a5   a4123a5..7de41b4
7de41b4..45f3ccf   45f3ccf..b430a52   b430a52..7430bfa   7430bfa..a80060c
a80060c..c7086a5   13b4391..c7086a5   c7086a5..6cc290b   6cc290b..96ff78d
6cc290b..2f9bcea   96ff78d..ccdbd2f
```

El ultimo, `96ff78d..ccdbd2f`, es el que reviso `final-review-fix-report-3.md`.

## Advertencia de lectura

**Son documentos de su momento, no documentacion vigente.** Varios describen estado que
despues cambio: `REANUDAR.md` habla de trabajo sin commitear que ya esta commiteado, y los
informes 1 y 2 describen defectos que el informe 3 cerro. Donde un informe y el codigo de
hoy no coincidan, manda el codigo; donde un informe y una decision no coincidan, manda
`decisiones-posteriores.md`.

Dos lineas quedaron corregidas en su lugar y estan marcadas como tales: la de
`final-review-fix-report-2.md` sobre `get_access_level`, y el item del estudio marcado "g"
en el informe 3, cerrado por D-6.
