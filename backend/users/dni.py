"""El DNI se guarda sin puntos, comas ni espacios: "30.123.456" y "30123456"
son la misma persona, y el índice único tiene que verlo así."""

import re

from rest_framework import serializers

DNI_REPETIDO = 'Ya existe un registro con ese DNI.'

_SEPARADORES = re.compile(r'[.,\s]')


def normalizar_dni(valor):
    """El DNI sin puntos, comas ni espacios. None y '' pasan tal cual."""
    if not valor:
        return valor
    return _SEPARADORES.sub('', str(valor))


class CampoDni(serializers.CharField):
    """Campo de DNI que normaliza ANTES de validar, así el largo máximo y la
    unicidad se miden sobre el valor que de verdad se guarda."""

    def to_internal_value(self, data):
        limpio = normalizar_dni(super().to_internal_value(data))
        if limpio == '' and not self.allow_blank:
            self.fail('blank')
        return limpio
