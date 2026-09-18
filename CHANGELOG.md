# Changelog del programa

Registra cambios del código y documentación del producto. Es distinto de docs/changelog/, que contiene resultados privados del pipeline sobre commits. Las publicaciones y push a GitHub los realiza manualmente el propietario.

## Baseline local — pendiente de primer commit y release

### Implementado

- Interfaz local y biblioteca con búsqueda, filtros, etiquetas y paginación.
- Expedientes separados con pregunta, resultados, fuentes, auditoría, claims y adjuntos.
- Cuatro pasadas independientes mediante Antigravity headless y transporte NDJSON.
- Publicación exclusiva de VERIFIED y controles estructurales de dominios sensibles/favorabilidad.
- Procedencia por claim, extractos y referencias Collector/Skeptic/Writer.
- Publicación local verificada en vault independiente, índices y notas personales protegidas.
- Lectura opcional del vault mediante MCPVault configurado externamente.
- Inicialización portable de datos faltantes sin reset; lanzador Windows Python/py.
- Wrappers raíz actualizados para delegar al pipeline activo.
- Exclusiones Git de datos, adjuntos, evidencias, configuración local y documentación generada.
- Guías de instalación, servidor, recuperación, arquitectura y GitHub.
- Pruebas simuladas de pipeline y biblioteca, con cien expedientes temporales.

### Validación observada

Las dos suites pasaron en una copia limpia formada por los archivos del índice Git; setup fue idempotente y la API devolvió una biblioteca vacía. No se ejecutó una investigación real para probar el clon limpio. Las simulaciones no demuestran veracidad semántica del modelo.

### Pendiente

No hay primer commit, remoto, tag o release del baseline creados. No hay OCR/visión, comprobación HTTP independiente de fuentes, URLs persistentes de navegación, trazabilidad de herramientas en vivo, score de evidencia, LAN autenticada o Studio implementados. Consulta ROADMAP.md.

## H1 — Flujo y navegación (publicación manual pendiente)

- Diferenciar ejecución finalizada de afirmaciones VERIFIED y presentar conclusión inconclusa cuando no haya VERIFIED.
- Ordenar vistas y mostrar etapas observables, errores y motivos registrados de revisión.
- Conservar investigación, pestaña, filtros y página en URL; permitir enlaces por afirmación y navegación Atrás/Adelante.
- Aceptar enlaces directos con parámetros en el servidor; mostrar error persistente para expedientes inexistentes.
- Mantener diagnóstico de la última ejecución accesible al leer un expediente.
- Validación: biblioteca y pipeline simulados, JavaScript compilable, recarga y navegación en navegador. Sin llamadas al modelo ni cambios de veredictos.

## H2 parcial — Fuentes y fichas (publicación manual pendiente)

- Recuperación independiente de referencias públicas y snapshots privados limitados, registros HTTP/extracto e integridad.
- Política source-v2: referencias externas no confirmadas no cuentan como respaldo primario para VERIFIED; claims antiguos requieren reevaluación antes de Writer.
- Ficha individual con origen, fuente, disponibilidad, extracto, motivos, historial y pasos pendientes; JSON opcional.
- Botón Comprobar fuentes sin IA conserva estados históricos.
- Tests de recuperación, bloqueos de red, falsificación/integridad y gate; pipeline/biblioteca simulados y revisión UI. La auditoría HTTP no valida automáticamente apoyo semántico ni oficialidad.

## Reevaluación selectiva (publicación manual pendiente)

- Formulario de enlaces/texto sin verificar en ficha de claim; fuerza nueva evaluación sólo del seleccionado.
- Solicitudes persistentes y snapshots del claim/reportes anteriores; historial de procedencia con revision_id.
- Diferenciar fallo de recolección, veredicto guardado, resultados locales y sincronización pendiente.
- Bloquear reutilización de solicitudes procesadas y solicitudes durante ejecución activa. Mantener JOB activo hasta completar sync.
- CLI document --case ... --claim ...; guía para traer investigación externa de ChatGPT como material sin verificar.
- Pruebas simuladas de alcance, aislamiento de Skeptic, fallos, respaldo, repetición/conteos y API. No se ejecutó el modelo real para validar esta entrega.


## Claridad de estados y revisión

Implementado: aviso visible de ejecución y reevaluación, señales de error y pendientes, auditoría estructurada, aclaración de vistas vacías, recorrido de herramientas conservado y avisos nativos en Obsidian. Pendiente: transmisión de herramientas en vivo y atribución exclusiva de acciones a cada afirmación en lotes. Guía: [Estados y recorrido](guides/ESTADOS-Y-RECORRIDO.md).


## Guía y actividad de investigación

Barra de etapas documentadas (separada de certeza), guía de lectura, Actividad reconstruida de registros con enlaces, referencias numeradas con fondos distintos y explicaciones sin banderas de programación en la vista principal. Nuevos ángulos preparan preguntas para investigaciones independientes; no son hallazgos de IA ya ejecutada. [Cómo entender una investigación](guides/COMO-ENTENDER-UNA-INVESTIGACION.md).


Navegación unificada: recorrido numerado Pregunta, Hipótesis, Evidencia, Revisión crítica y Resultados; Resumen y herramientas de consulta separados de las etapas. La guía usa el mismo orden.


Diagnóstico por afirmación: separa ausencia de evidencia, fuentes pendientes, direcciones caídas, restricciones y pasajes no confirmados. Propone siguientes acciones sin modificar veredictos. PENDIENTES actualizado y copiado a outputs y Proyecto en Obsidian.
