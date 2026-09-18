# Pruebas sin proveedor de IA

Desde la raíz, con Python 3.10 o posterior:

```powershell
python scripts/setup.py
python tests/validate_pipeline.py
python tests/test_library.py
```

No requieren Antigravity autenticado: simulan las respuestas y el ejecutable para validar el orquestador. Usan directorios temporales y no crean investigaciones de prueba en tu biblioteca. test_library crea cien expedientes temporales; puede tardar según disco/antivirus.

validate_pipeline verifica cuatro pasadas, publicación exclusiva de VERIFIED, independencia de datos recibidos por Skeptic, fallo/reintento de Writer, conservación de veredictos y salidas crudas, evidencias, commits incrementales y fallo/reintento de sincronización. Requiere Git instalado.

test_library verifica dos expedientes aislados, procedencia de Writer, documentos globales intactos, notas personales protegidas, cien expedientes con búsqueda/paginación, lectura/edición API y rechazo de rutas fuera de la biblioteca. No prueba visión/OCR ni veracidad semántica del modelo.

Una investigación real requiere autenticación, permisos y acceso al proveedor; se prueba por separado con una pregunta y fuentes que puedas revisar. La compatibilidad con una nueva versión del CLI no queda garantizada por una simulación.
