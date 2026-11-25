"""Los cuatro grupos del CBSFBE y a cuál pertenece cada promoción.

Un buzo pertenece al grupo de su año de egreso del Curso Básico. La tabla es de
la unidad: no se deduce con una fórmula porque no sigue un ciclo regular.
Los grupos compiten el último día de la habilitación.
"""

INMORTALES = 'INMORTALES'
LEGIONARIOS = 'LEGIONARIOS'
PRETORIANOS = 'PRETORIANOS'
GLADIADORES = 'GLADIADORES'

GRUPOS = {
    INMORTALES: {
        'nombre': 'Inmortales', 'color': '#1E7A3C',
        'anios': (1974, 1979, 1980, 1985, 1990, 1998, 2002, 2003, 2007, 2011,
                  2015, 2019, 2023),
    },
    LEGIONARIOS: {
        'nombre': 'Legionarios', 'color': '#16181B',
        'anios': (1975, 1978, 1981, 1986, 1993, 1996, 1999, 2004, 2008, 2012,
                  2016, 2020, 2024),
    },
    PRETORIANOS: {
        'nombre': 'Pretorianos', 'color': '#14284B',
        'anios': (1976, 1982, 1987, 1989, 1994, 2000, 2005, 2009, 2013, 2017,
                  2021, 2025),
    },
    GLADIADORES: {
        'nombre': 'Gladiadores', 'color': '#B3261E',
        'anios': (1977, 1983, 1984, 1988, 1995, 2001, 2006, 2010, 2014, 2018,
                  2022, 2026),
    },
}

CHOICES = [(codigo, g['nombre']) for codigo, g in GRUPOS.items()]

_POR_ANIO = {a: codigo for codigo, g in GRUPOS.items() for a in g['anios']}
assert sum(len(g['anios']) for g in GRUPOS.values()) == len(_POR_ANIO), \
    'Un año figura en dos grupos.'


def grupo_de(anio):
    """El código del grupo de un año de curso, o `None` si no consta."""
    return _POR_ANIO.get(anio)


def descripcion(codigo):
    """Lo que la pantalla necesita para dibujar un grupo."""
    if codigo is None:
        return None
    g = GRUPOS[codigo]
    return {'codigo': codigo, 'nombre': g['nombre'], 'color': g['color']}
