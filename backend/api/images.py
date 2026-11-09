"""Compresión de los archivos que suben los buzos.

Las fotos de celular (JPEG o HEIC) salen como JPEG de LADO_MAYOR píxeles en el
lado mayor, sin metadatos EXIF. Los PDF no se recomprimen (puede volver ilegible una
radiografía escaneada), pero se guardan siempre con extensión `.pdf`.
"""

import io
import os

import pillow_heif
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
LADO_MAYOR = 2000
CALIDAD = 75
# Una foto de 48 MP (8000x6000) entra. Una imagen que se expande a cientos de MiB
# no: el tope de bytes no la ve, porque el archivo comprimido puede pesar poco.
MAX_PIXELES = 60_000_000

_CABECERA_PDF = b'%PDF'
_MENSAJE_NO_IMAGEN = (
    'El archivo no es una imagen ni un PDF. Debe subirse una imagen o un archivo PDF.')
_MENSAJE_DEMASIADOS_PIXELES = (
    'La resolución de la imagen supera el máximo permitido de 60 megapíxeles.')


class ArchivoRechazado(Exception):
    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


def comprimir(archivo: UploadedFile) -> UploadedFile:
    # El tope mide el archivo comprimido, no los píxeles en que se expande:
    # el límite de píxeles está más abajo, después de abrir la imagen.
    if archivo.size > MAX_UPLOAD_BYTES:
        raise ArchivoRechazado(
            'El archivo supera el tamaño máximo permitido de 12 MB.')

    # El tipo se decide por los primeros bytes, no por el nombre del archivo.
    archivo.seek(0)
    if archivo.read(len(_CABECERA_PDF)) == _CABECERA_PDF:
        archivo.seek(0)
        # El nombre del archivo lo manda el cliente y decide con qué tipo lo
        # sirve el servidor web: un `.html` o `.svg` que empiece con `%PDF` se
        # serviría como página en el mismo origen que la app, y su script podría
        # leer el token del médico que lo abra. La extensión la pone el servidor.
        nombre = os.path.splitext(os.path.basename(archivo.name))[0] + '.pdf'
        return SimpleUploadedFile(
            nombre, archivo.read(), content_type='application/pdf')

    archivo.seek(0)
    try:
        imagen = Image.open(archivo)
        # Pillow lee el encabezado al abrir, así que el tamaño ya se conoce. Se
        # chequea antes de transponer o convertir, que es donde se reserva la memoria.
        if imagen.width * imagen.height > MAX_PIXELES:
            raise ArchivoRechazado(_MENSAJE_DEMASIADOS_PIXELES)
        # Antes de descartar el EXIF: la rotación de la foto vive ahí.
        imagen = ImageOps.exif_transpose(imagen)
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
