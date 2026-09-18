# Reevaluar una afirmación con nuevas fuentes

## Usar el frontend

1. Biblioteca → Afirmaciones → Abrir ficha.
2. Despliega Aportar nuevas fuentes y reevaluar.
3. Pega enlaces originales y explica qué respalda cada uno. Añade pasajes textuales o una transcripción si hace falta.
4. Pulsa Solicitar nueva evaluación de esta afirmación. Esta acción usa Antigravity e Internet; no garantiza VERIFIED.
5. Revisa el nuevo veredicto, fuentes comprobadas y Solicitudes de reevaluación. Ver materiales permite recuperar lo que aportaste.

Sólo se recopila/evalúa otra vez el claim seleccionado, aunque ya tuviera estado final. El texto de la afirmación no cambia. Las demás conservan su veredicto; Writer puede reconstruir resultados del expediente con claims VERIFIED bajo política vigente. Los VERIFIED históricos bajo política antigua no se consolidan como hechos y aparecen pendientes por ID. No se omiten silenciosamente.

Los enlaces/textos aportados son datos sin verificar. No sustituyen contenido original comprobado ni convierten una respuesta de ChatGPT en fuente primaria. PDF/imágenes aún requieren transcripción o descripción; el programa no los interpreta automáticamente.

Los borradores permanecen durante polling y cambios de vista en la misma sesión; una recarga/cierre los pierde si no se enviaron. El historial de solicitudes enviadas sí es persistente.

## Qué se conserva

Cada solicitud crea .project-intelligence/library/<expediente>/revisiones/<id>/ con request.json, previous_claim.json, previous_resultados.md y respaldos de fuentes/auditoría disponibles, más status.json. Estados: queued, running, reviewed, published_local, completed, error, interrupted. Son estados de ejecución, distintos del veredicto del claim.

PASS 2 recibe los nuevos materiales y referencias previas para volver a comprobarlas. PASS 3 recibe únicamente claim + evidence; no recibe el razonamiento Investigator ni texto de apoyo sin recolectar. Se agrega revisión/solicitud al historial de procedencia.

Si falla Collector/Skeptic, queda el estado previo. Si falla Writer, el nuevo veredicto se conserva y el reporte anterior sigue disponible: la ficha lo advierte. Si falla sync, puede haber resultados locales nuevos pero Obsidian pendiente. Un reinicio señala solicitudes inacabadas; se crea otra revisión, sin reutilizar una solicitud ya procesada. No se trata como transacción de base de datos ni recuperación automática del modelo.

Historial y respaldos son privados, excluidos de Git y no se copian como archivo íntegro de revisiones a Obsidian en esta entrega. El vault recibe los reportes/expedientes conforme al sync existente. Incluye .project-intelligence en backups privados.

## Terminal opcional

python scripts/pipeline.py document --case ID_EXPEDIENTE --claim ID_AFIRMACION

Crea una solicitud vacía y fuerza reevaluación sólo de ese claim. El frontend permite agregar materiales cómodamente. --revision se usa para la solicitud interna ya registrada; no reutiliza solicitudes completadas.

## Comprobación de implementación

python tests/test_revisions.py

Pruebas simuladas: alcance de un claim, materiales nuevos en Collector, aislamiento de Skeptic, respaldo anterior, historial, solicitudes repetidas, conteos sin duplicados, fallos de búsqueda/Writer y API con guard de ejecución activa. No se inició una investigación real en tus expedientes durante esta implementación.
