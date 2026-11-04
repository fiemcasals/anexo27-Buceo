"""Tests de la compresión de archivos subidos por los buzos.

Las imágenes de prueba se arman en memoria con Pillow: no se versiona ningún
binario. Ningún test toca la base ni HTTP, por eso alcanza con SimpleTestCase.
"""

import io
import warnings
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from api.images import MAX_UPLOAD_BYTES, ArchivoRechazado, comprimir


def _archivo(contenido, nombre):
    return SimpleUploadedFile(nombre, contenido)


def _imagen(ancho, alto, formato, nombre=None):
    buffer = io.BytesIO()
    Image.new('RGB', (ancho, alto), (120, 60, 30)).save(buffer, formato)
    extension = 'heic' if formato == 'HEIF' else 'jpg'
    return _archivo(buffer.getvalue(), nombre or f'foto.{extension}')


def _imagen_con_exif(ancho, alto):
    # El EXIF de la cámara puede traer ubicación y modelo del dispositivo:
    # no debe llegar a la carpeta del buzo.
    exif = Image.Exif()
    exif[0x010F] = 'Marca de cámara'
    buffer = io.BytesIO()
    Image.new('RGB', (ancho, alto), (120, 60, 30)).save(
        buffer, 'JPEG', exif=exif.tobytes())
    return _archivo(buffer.getvalue(), 'foto.jpg')


def _imagen_con_orientacion(ancho, alto, orientacion):
    # El celular en vertical guarda los píxeles en horizontal y marca la rotación
    # en la etiqueta 0x0112 del EXIF.
    exif = Image.Exif()
    exif[0x0112] = orientacion
    buffer = io.BytesIO()
    Image.new('RGB', (ancho, alto), (120, 60, 30)).save(
        buffer, 'JPEG', exif=exif.tobytes())
    return _archivo(buffer.getvalue(), 'foto.jpg')


def _pdf():
    contenido = (
        b'%PDF-1.4\n'
        b'1 0 obj << /Type /Catalog >> endobj\n'
        b'%%EOF\n'
    )
    return _archivo(contenido, 'estudio.pdf')


class ReduceLasFotosDeCelularTests(SimpleTestCase):
    def test_una_foto_grande_sale_en_2000_pixeles_de_lado_mayor(self):
        # 4032x3024 es el tamaño real de una foto de celular
        salida = comprimir(_imagen(4032, 3024, 'JPEG'))
        self.assertEqual(max(Image.open(salida).size), 2000)

    def test_la_proporcion_no_se_deforma(self):
        ancho, alto = Image.open(comprimir(_imagen(4032, 3024, 'JPEG'))).size
        self.assertAlmostEqual(ancho / alto, 4032 / 3024, places=2)

    def test_una_foto_mas_chica_que_el_tope_no_se_agranda(self):
        self.assertEqual(Image.open(comprimir(_imagen(800, 600, 'JPEG'))).size, (800, 600))

    def test_sale_sin_metadatos_exif_de_la_camara(self):
        self.assertFalse(Image.open(comprimir(_imagen_con_exif(4032, 3024))).getexif())

    def test_la_salida_se_comprime_con_calidad_75(self):
        # La calidad queda escrita en las tablas de cuantización del JPEG. Con 30
        # el análisis se vuelve borroso; con 95 el disco se llena.
        referencia = io.BytesIO()
        Image.new('RGB', (64, 64), (120, 60, 30)).save(referencia, 'JPEG', quality=75)
        esperadas = Image.open(io.BytesIO(referencia.getvalue())).quantization
        salida = comprimir(_imagen(800, 600, 'JPEG'))
        self.assertEqual(Image.open(salida).quantization, esperadas)

    def test_la_foto_en_vertical_sale_derecha(self):
        # Si se descarta el EXIF sin aplicar la rotación antes, la foto le llega
        # al médico acostada. La orientación 6 es la de una foto en vertical.
        salida = comprimir(_imagen_con_orientacion(400, 200, 6))
        self.assertEqual(Image.open(salida).size, (200, 400))


class ElHeicDelIphoneSeConvierteTests(SimpleTestCase):
    # El iPhone guarda las fotos en HEIC por defecto. El médico ve JPEG,
    # así que la salida tiene que ser JPEG aunque la entrada no lo sea.
    def test_una_foto_heic_sale_como_jpeg(self):
        self.assertEqual(Image.open(comprimir(_imagen(4032, 3024, 'HEIF'))).format, 'JPEG')

    def test_el_nombre_pasa_a_jpg(self):
        salida = comprimir(_imagen(100, 100, 'HEIF', nombre='foto.heic'))
        self.assertTrue(salida.name.endswith('.jpg'))


class ElPdfNoSeTocaTests(SimpleTestCase):
    # Recomprimir un PDF puede volver ilegible una radiografía escaneada.
    def test_un_pdf_vuelve_byte_a_byte_igual(self):
        entrada = _pdf()
        esperado = entrada.read()
        entrada.seek(0)
        self.assertEqual(comprimir(entrada).read(), esperado)


class LoQueNoSeAceptaTests(SimpleTestCase):
    # El tipo se decide por el contenido, no por la extensión: por eso los
    # tests de abajo mandan bytes que no son imagen con nombre de imagen.
    def test_un_docx_se_rechaza_con_mensaje_en_castellano(self):
        with self.assertRaises(ArchivoRechazado) as cm:
            comprimir(_archivo(b'PK\x03\x04', 'informe.docx'))
        self.assertIn('imagen', cm.exception.mensaje.lower())

    def test_un_archivo_que_pasa_el_tope_se_rechaza_antes_de_abrirlo(self):
        # Una JPEG válida seguida de relleno: Pillow la abriría sin quejarse, así
        # que el rechazo sólo puede venir del chequeo de tamaño.
        jpeg = _imagen(100, 100, 'JPEG').read()
        with self.assertRaises(ArchivoRechazado):
            comprimir(_archivo(jpeg + b'\x00' * MAX_UPLOAD_BYTES, 'enorme.jpg'))

    def test_el_mensaje_del_tope_dice_el_limite(self):
        with self.assertRaises(ArchivoRechazado) as cm:
            comprimir(_archivo(b'\xff\xd8' + b'x' * MAX_UPLOAD_BYTES, 'e.jpg'))
        self.assertIn('12', cm.exception.mensaje)

    def test_un_jpg_mentido_que_no_es_imagen_se_rechaza_sin_traza_de_pillow(self):
        with self.assertRaises(ArchivoRechazado):
            comprimir(_archivo(b'no soy una imagen', 'mentira.jpg'))

    def test_una_imagen_con_demasiados_pixeles_se_rechaza_aunque_pese_poco(self):
        # Una imagen de 12000x12000 pesa poco porque es de un solo color, pero al
        # decodificarla ocupa cientos de MiB. El tope de bytes no la ve, así que
        # el rechazo tiene que venir del tope de píxeles. Se usa 1 bit por píxel
        # para que armar el fixture no ocupe cientos de MiB.
        buffer = io.BytesIO()
        Image.new('1', (12000, 12000)).save(buffer, 'PNG')
        # Pillow avisa con DecompressionBombWarning por encima de su límite; el
        # aviso es esperado aquí y no dice nada nuevo.
        with warnings.catch_warnings(), self.assertRaises(ArchivoRechazado) as cm:
            warnings.simplefilter('ignore', Image.DecompressionBombWarning)
            comprimir(_archivo(buffer.getvalue(), 'enorme.png'))
        self.assertIn('megapíxeles', cm.exception.mensaje)

    def test_una_imagen_que_se_expande_demasiado_se_rechaza(self):
        # Una imagen chica que declara muchísimos píxeles es una bomba de
        # descompresión. Pillow la corta con DecompressionBombError, que no es
        # OSError: sin su propia traducción llegaría como 500.
        archivo = _imagen(100, 100, 'JPEG')
        with mock.patch.object(Image, 'MAX_IMAGE_PIXELS', 100):
            with self.assertRaises(ArchivoRechazado):
                comprimir(archivo)
