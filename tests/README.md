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

Comprobación de fuentes y publicación: `python tests/test_source_check.py` (fixtures; sin servicios externos).

Reevaluación selectiva: `python tests/test_revisions.py` (casos temporales; sin modelo ni consultas externas).


`python -m unittest discover -s tests -p "test_action_trace.py"`: eventos observables sin razonamiento interno, última ejecución, rutas seguras y VERIFIED externos pendientes cuando falta comprobación independiente.


Pruebas opcionales del modelo de interfaz: `python -m unittest discover -s tests -p "test_research_ui.py"` (Node para desarrollo). Comprueban proceso finalizado pero inconcluso, veredictos históricos pendientes, eventos sin invenciones, deduplicación y explicaciones principales sin booleanos.

Traspaso web: `python -m unittest discover -s tests -p "test_handoff.py"`: hashes de base, comprobación de parche sin aplicación, rechazo de rutas privadas, bloqueo de investigación activa, respaldo íntegro y detección de cambios concurrentes. Fixtures temporales; no modelo ni vault real.

Recuperación: test_collector_checkpoint.py comprueba fallo/reanudación de Skeptic, caducidad, integridad e invalidación; test_human_review.py comprueba observaciones sin cambiar veredictos, evidencia histórica, sesión y bloqueo activo. test_documents.py incluye ausencia de coincidencias y respaldo PDF sin URL accesible; test_research_ui.py separa evaluación de resolución y explica errores. Fixtures sin proveedor real.
