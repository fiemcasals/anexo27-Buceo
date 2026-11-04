"""Compresión de los archivos que suben los buzos.

Las fotos de celular (JPEG o HEIC) salen como JPEG de LADO_MAYOR píxeles en el
lado mayor, sin metadatos EXIF. Los PDF no se tocan: recomprimirlos puede volver
ilegible una radiografía escaneada.
"""

import io
import os

import pillow_heif
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from PIL import Image

pillow_heif.register_heif_opener()

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
LADO_MAYOR = 2000
CALIDAD = 75

_CABECERA_PDF = b'%PDF'
_MENSAJE_NO_IMAGEN = (
    'El archivo no es una imagen ni un PDF. Debe subirse una imagen o un archivo PDF.')


class ArchivoRechazado(Exception):
    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


def comprimir(archivo: UploadedFile) -> UploadedFile:
    # El tope se mira antes de abrir nada: una carga enorme no llega a Pillow.
    if archivo.size > MAX_UPLOAD_BYTES:
        raise ArchivoRechazado(
            'El archivo supera el tamaño máximo permitido de 12 MB.')

    # El tipo se decide por los primeros bytes, no por el nombre del archivo.
    archivo.seek(0)
    if archivo.read(len(_CABECERA_PDF)) == _CABECERA_PDF:
        archivo.seek(0)
        return archivo

    archivo.seek(0)
    try:
        imagen = Image.open(archivo)
        imagen = imagen.convert('RGB')
    except (OSError, Image.DecompressionBombError):
        raise ArchivoRechazado(_MENSAJE_NO_IMAGEN)

    imagen.thumbnail((LADO_MAYOR, LADO_MAYOR))

    # Se pegan los píxeles en una imagen nueva para no arrastrar los metadatos
    # de la original, en vez de depender de que save() los omita.
    limpia = Image.new('RGB', imagen.size)
    limpia.paste(imagen)

    salida = io.BytesIO()
    limpia.save(salida, 'JPEG', quality=CALIDAD)

    nombre = os.path.splitext(archivo.name)[0] + '.jpg'
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type='image/jpeg')
