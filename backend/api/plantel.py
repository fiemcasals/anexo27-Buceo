"""El plantel para el listado del médico: una fila por buzo.

No define ninguna regla. Cada conteo, vigencia, estado y último dictamen sale de
``fitness.diver_summary``; acá sólo se elige qué se muestra y cómo se nombra. Una
segunda definición de la regla (un ``annotate``, una consulta "para optimizar")
se desincronizaría de la que ve el buzo.

Tampoco consulta la base: lee el perfil ya traído, con la receta de ``select_related``
y ``prefetch_related`` que documenta ``fitness``.
"""

from __future__ import annotations

import unicodedata
from datetime import date
from typing import TYPE_CHECKING

from . import fitness

if TYPE_CHECKING:  # pragma: no cover - sólo para las anotaciones
    from users.models import UserProfile


def fila(profile: UserProfile, today: date) -> dict:
    """La fila del listado para un buzo. No hace consultas.

    ``presentados`` cuenta los slots que tienen bloque: los exigidos si hay turno
    y fecha de nacimiento, los ocho del catálogo si falta alguno de los dos.
    """
    resumen = fitness.diver_summary(profile, today)
    window = profile.habilitation_window

    # Sin turno o sin fecha de nacimiento el exigido no se puede determinar, y eso
    # no es lo mismo que cero: un buzo que subió ocho estudios sin inscribirse
    # leería "0/0", o sea que no presentó nada.
    determinado = window is not None and profile.birth_date is not None

    return {
        'id': profile.pk,
        'grado': profile.rank,
        'apellido': profile.user.last_name,
        'nombre': profile.user.first_name,
        'unidad': profile.destination,
        'dni': profile.dni,
        # La edad de la regla (año del turno menos año de nacimiento), no la de
        # hoy: es la que decide si corresponden siete estudios u ocho.
        'edad': (profile.age_in_year(fitness.habilitation_year(window))
                 if determinado else None),
        'turno': None if window is None else {
            'id': window.pk,
            'slot': window.slot,
            'slot_display': window.get_slot_display(),
            'start_date': window.start_date,
            'end_date': window.end_date,
        },
        'presentados': (resumen.presented if determinado
                        else _subidos(resumen)),
        'exigidos': len(resumen.required_codes) if determinado else None,
        'a_revisar': resumen.pending_review + resumen.pre_reviewed,
        'sin_tocar': resumen.pending_review,
        'pre_revisados': resumen.pre_reviewed,
        'vencidos': resumen.expired,
        'rechazados': resumen.rejected,
        'ultima_revision': resumen.last_doctor_review,
        'estado': resumen.state.name,
        'subida_mas_vieja_sin_dictamen': _subida_mas_vieja(resumen),
    }


def _subidos(resumen: fitness.DiverSummary) -> int:
    """Cuántos puntos tienen carga vigente cuando no hay exigidos contra los
    cuales contar.

    ``DiverSummary.presented`` cuenta sólo los exigidos, y sin turno o sin edad no
    hay ninguno: daría cero para un buzo que subió ocho. Los ``slots`` conservan
    la carga de los ocho, así que se cuenta de ahí, sin definir ninguna regla.
    """
    return sum(1 for slot in resumen.slots if slot.block is not None)


def _subida_mas_vieja(resumen: fitness.DiverSummary):
    """Cuándo se cargó lo más viejo que nadie tocó; None si no hay nada.

    Es la pila cruda (spec, §8.1): sólo mira lo que no tiene ningún dictamen
    (en revisión). Lo pre-revisado ya lo miró el enfermero y va en la pila
    rápida del médico; un estudio viejo ya dictaminado tampoco encabeza la
    pila cruda.
    """
    subidas = [
        slot.block.created_at for slot in resumen.slots
        if slot.state is fitness.StudyState.IN_REVIEW and slot.block is not None
    ]
    return min(subidas) if subidas else None


FILTROS = ('todos', 'completa', 'incompleta', 'pendientes')
CRITERIOS = ('apellido', 'ultima_revision', 'pendientes', 'pila_rapida',
             'pila_cruda', 'grado_antiguo', 'grado_moderno')


def _plano(texto) -> str:
    """Minúsculas y sin acentos, para comparar lo que escribe el médico."""
    descompuesto = unicodedata.normalize('NFKD', str(texto or ''))
    return ''.join(c for c in descompuesto
                   if not unicodedata.combining(c)).casefold()


def _sin_puntos(texto: str) -> str:
    """El DNI se escribe de mil maneras: se compara sin puntos ni espacios."""
    return texto.replace('.', '').replace(' ', '')


def _pajar(fila: dict) -> str:
    """El texto donde se busca: grado, apellido, nombre y DNI, en un solo campo."""
    return ' '.join((_plano(fila['grado']), _plano(fila['apellido']),
                     _plano(fila['nombre']), _sin_puntos(_plano(fila['dni']))))


def buscar(filas: list[dict], texto) -> list[dict]:
    """Las filas que contienen todas las palabras de ``texto``.

    Sin mayúsculas, sin acentos y sin puntos en el DNI. Un texto vacío no filtra.
    """
    palabras = [_sin_puntos(p) for p in _plano(texto).split()]
    if not palabras:
        return list(filas)
    resultado = []
    for fila in filas:
        pajar = _pajar(fila)
        if all(p in pajar for p in palabras):
            resultado.append(fila)
    return resultado


def _completa(fila: dict) -> bool:
    """Todo lo exigido está presentado. No mira el dictamen: un estudio
    rechazado cuenta, el papel está. Sin exigidos (None) no hay contra qué
    comparar, y no se puede decir que esté completo."""
    return fila['exigidos'] is not None and fila['presentados'] >= fila['exigidos']


_PREDICADOS = {
    'todos': lambda fila: True,
    'completa': _completa,
    'incompleta': lambda fila: not _completa(fila),
    'pendientes': lambda fila: fila['a_revisar'] > 0,
}


def filtrar(filas: list[dict], *, filtro=None, turno=None) -> list[dict]:
    """Filtra por documentación (``FILTROS``) y por turno.

    ``turno`` es el id de un turno, o ``'sin'`` para los no inscriptos.
    """
    filtro = filtro or 'todos'
    if filtro not in _PREDICADOS:
        raise ValueError(f'Filtro desconocido: {filtro!r}')
    resultado = [f for f in filas if _PREDICADOS[filtro](f)]
    if turno == 'sin':
        resultado = [f for f in resultado if f['turno'] is None]
    elif turno is not None:
        resultado = [f for f in resultado
                     if f['turno'] is not None and f['turno']['id'] == turno]
    return resultado


def contar(filas: list[dict]) -> dict:
    """Contadores de la cabecera. Cuentan buzos, no estudios.

    Cada buzo cae en un solo estado (``estado`` ya trae la precedencia resuelta
    por ``fitness``), así que ``vencidos`` no incluye al que además tiene un
    rechazado.
    """
    return {
        'aptos': sum(1 for f in filas if f['estado'] == 'APTO'),
        'a_revisar': sum(1 for f in filas if f['a_revisar'] > 0),
        'vencidos': sum(1 for f in filas if f['estado'] == 'EXPIRED'),
        'por_filtro': {nombre: sum(1 for f in filas if _PREDICADOS[nombre](f))
                       for nombre in FILTROS},
    }


def _por_apellido(fila: dict) -> tuple:
    return (_plano(fila['apellido']), _plano(fila['nombre']))


def _al_fondo_los_none(valor) -> tuple:
    """Clave que manda los None al final sin comparar None con una fecha."""
    return (valor is None, valor if valor is not None else 0)


def _posicion_del_grado(fila_: dict, invertido: bool) -> tuple:
    """Lugar del grado en la jerarquía (`UserProfile.RANK_VALUES`, del más
    antiguo al más moderno). Sin grado, o con uno que no está en la lista, va al
    final en los dos sentidos."""
    from users.models import UserProfile
    valores = UserProfile.RANK_VALUES
    grado = fila_.get('grado')
    if grado not in valores:
        return (1, 0)
    lugar = valores.index(grado)
    return (0, -lugar if invertido else lugar)


def ordenar(filas: list[dict], criterio: str) -> list[dict]:
    """Una lista nueva ordenada según ``CRITERIOS``; desempata por apellido.

    - ``ultima_revision``: primero los nunca revisados, después el más antiguo.
    - ``pendientes``: más estudios por revisar primero.
    - ``pila_rapida``: más pre-revisados primero (lo que se aprueba de un vistazo).
    - ``pila_cruda``: la subida más vieja sin dictamen primero; sin nada
      esperando, al fondo.
    - ``grado_antiguo`` / ``grado_moderno``: por jerarquía, del grado más antiguo
      (GD) al más moderno (CB) o al revés; sin grado, al final.
    """
    claves = {
        'apellido': _por_apellido,
        'ultima_revision': lambda f: (
            f['ultima_revision'] is not None,
            f['ultima_revision'] or date.min, *_por_apellido(f)),
        'pendientes': lambda f: (-f['a_revisar'], *_por_apellido(f)),
        'pila_rapida': lambda f: (-f['pre_revisados'], *_por_apellido(f)),
        'pila_cruda': lambda f: (
            *_al_fondo_los_none(f['subida_mas_vieja_sin_dictamen']),
            *_por_apellido(f)),
        'grado_antiguo': lambda f: (
            *_posicion_del_grado(f, False), *_por_apellido(f)),
        'grado_moderno': lambda f: (
            *_posicion_del_grado(f, True), *_por_apellido(f)),
    }
    if criterio not in claves:
        raise ValueError(f'Criterio desconocido: {criterio!r}')
    return sorted(filas, key=claves[criterio])
