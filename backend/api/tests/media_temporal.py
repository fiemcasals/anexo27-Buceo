"""Un MEDIA_ROOT descartable para las clases de test que suben archivos.

Sin esto la suite escribe en el `media/` de la aplicacion (una corrida dejo
miles de archivos). El directorio se crea una vez por proceso y se borra al
salir.
"""
import atexit
import shutil
import tempfile

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix='anexo27-test-media-')
atexit.register(shutil.rmtree, MEDIA_TEMPORAL, ignore_errors=True)
