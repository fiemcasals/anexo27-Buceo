"""Quién es revisor designado, según el §5.

Vive en su propio módulo porque lo consultan las vistas y los serializadores, y
`views` importa `serializers`: dejarlo en `views` obligaba a un import local
dentro de `get_access_level` para esquivar el ciclo.
"""

# §5: el acceso a los estudios médicos sale del rol que designa el admin, no de
# concesiones entre usuarios. El buzo "ve y gestiona sus propios estudios, nada
# más"; el médico y los enfermeros auxiliares "ven los estudios de todos"; nadie
# más ve los de nadie. El circuito anterior era el inverso y venía de la vida
# previa de la app: cada buzo le concedía acceso al revisor desde la pantalla de
# Permisos, así que el médico designado no veía nada y un buzo podía compartir
# sus estudios médicos con cualquier usuario registrado — y el registro es
# abierto y sin verificación. `Permission` se deja en pie (§5) y deja de regir.
#
# No confundir con `Comment.REVIEWER_ROLES`, que es la lista de opciones del
# campo `reviewer_role` con sus etiquetas para el admin. Acá sólo hacen falta
# los valores.
REVIEWER_ROLES = ('DOCTOR', 'NURSE')


def es_revisor(user):
    """True si el usuario es el médico o un enfermero auxiliar designado.

    El perfil puede no existir —`UserProfile` se crea aparte del `User`, y
    `UserProfileViewSet.me` lo prueba haciéndole `get_or_create`— y en ese caso
    el usuario no es revisor: la falta de perfil nunca puede significar "ve
    todo". El `getattr` es el mismo cuidado que ya tiene `generate_anexo_27`;
    hace falta porque el acceso a un OneToOne inverso inexistente levanta.
    """
    profile = getattr(user, 'profile', None)
    return profile is not None and profile.role in REVIEWER_ROLES
