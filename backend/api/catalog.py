"""Catálogo de los ocho estudios exigidos por la Directiva 443/21.

Módulo puro: no importa nada de Django. Lo consumen el motor de estados,
los serializadores y las plantillas de correo.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RequiredStudy:
    code: str
    text: str
    validity_days: int
    min_age: int | None
    upload_hint: str


ALL: tuple[RequiredStudy, ...] = (
    RequiredStudy(
        code="a",
        text="Electrocardiograma de esfuerzo",
        validity_days=365,
        min_age=40,
        upload_hint="",
    ),
    RequiredStudy(
        code="b",
        text="Ecocardiograma con informe (sin excepción)",
        validity_days=365,
        min_age=None,
        upload_hint="",
    ),
    RequiredStudy(
        code="c",
        text="Electroencefalograma",
        validity_days=365,
        min_age=None,
        upload_hint="",
    ),
    RequiredStudy(
        code="d",
        text="Radiografía de tórax, frente y perfil",
        validity_days=365,
        min_age=None,
        upload_hint="El archivo debe incluir las dos placas, frente y perfil.",
    ),
    RequiredStudy(
        code="e",
        text="Radiografía de senos frontales y paranasales",
        validity_days=365,
        min_age=None,
        upload_hint="",
    ),
    RequiredStudy(
        code="f",
        text="Hemograma, eritrosedimentación, dosaje de urea, dosaje de glucosa y orina completo",
        validity_days=365,
        min_age=None,
        upload_hint="El archivo debe incluir los cinco análisis: hemograma, eritrosedimentación, urea, glucosa y orina completo.",
    ),
    RequiredStudy(
        code="g",
        text="Ficha de control odontológico (actualizada)",
        validity_days=365,
        min_age=None,
        upload_hint="",
    ),
    RequiredStudy(
        code="h",
        text="Anexo 27 ORIGINAL, firmado por el médico militar y Jefe de Elemento",
        validity_days=30,
        min_age=None,
        upload_hint="",
    ),
)

CODES: tuple[str, ...] = tuple(study.code for study in ALL)

_BY_CODE: dict[str, RequiredStudy] = {study.code: study for study in ALL}


def get(code: str) -> RequiredStudy:
    """Devuelve el estudio con ese código; levanta KeyError si no existe."""
    return _BY_CODE[code]


def required_for_age(age: int) -> tuple[RequiredStudy, ...]:
    """Estudios que debe presentar un buzo de la edad dada (año de habilitación − año de nacimiento)."""
    return tuple(
        study
        for study in ALL
        if study.min_age is None or age >= study.min_age
    )
