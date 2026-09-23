# Changelog del programa

Registra cambios del código y documentación del producto. Es distinto de docs/changelog/, que contiene resultados privados del pipeline sobre commits. Las publicaciones y push a GitHub los realiza manualmente el propietario.

## Baseline local — pendiente de primer commit y release

### 2026-09-18 — Investigación automática especializada (pendiente de publicación)

- Acción principal por claim con nueve roles especializados, tres rondas limitadas y salidas JSON validadas.
- Operaciones persistentes con progreso, presupuesto, manifiestos, matrices, auditoría y cierre `excluded_with_limit` sin borrar el veredicto histórico.
- Comprobación técnica de páginas separada de la investigación; doble clic deduplicado y resultado visible.
- Trazas con total previo al recorte, acciones omitidas, consultas agrupadas, atribución por manifiesto y descarga completa.
- Servicio único en 8770 con esquema/build/PID/puerto y bloqueo de acciones ante versiones incompatibles.

### 2026-09-18 — Control de alcance (pendiente de publicación)

- Nuevos expedientes se detienen después de proponer y revisar hipótesis; aprobación explícita de una a tres antes de Collector/Writer.
- Selección versionada, motivos, origen declarado y corridas de generación/revisión visibles; propuestas no admitidas se conservan.
- Revisión de alcance para expedientes históricos y bloqueo equivalente desde frontend/CLI.
- Revisor con SKILL.md, pruebas de aprobación, integridad del alcance y compatibilidad con pipeline.
- Registrado backlog acordado: recuperación, agentes especializados, auditoría de respuesta, cierre científico y accesibilidad. Estos bloques siguen pendientes.

### 2026-09-18 — Evidencia PDF local (pendiente de publicación)

- Original y hash conservados por expediente; extracción paginada y versionada con pypdf o Docling opcional en CPU, sin OCR.
- Interfaz PDF con pasos, paneles Abrir/Cerrar, campos completos, métodos con nombres comprensibles y límites visibles.
- PDFs disponibles en la interfaz, lectura por página y registro de revisión de identidad; ninguna de estas acciones verifica claims.
- Fragmentos exactos enviados a Collector/Skeptic, cotejo literal y deduplicación de identidad por DOI.
- Benchmark de dos papers, 39 páginas; limitaciones y pasos de reevaluación documentados.

### 2026-09-18 — Recuperación del Collector (pendiente de publicación)

- Evaluación por afirmación, registros separados y conservación de revisiones completas ante fallo posterior.
- Tiempo máximo de 900 segundos y diagnóstico consistente; posición de la afirmación visible durante la ejecución.
- Entradas exactas del proveedor conservadas y auditoría con alcance explícito.
- Publicación inconclusa registrada como terminada; placeholders iniciales siguen pendientes.
- Pruebas de reanudación y timeout; fixture de integración sintético sin copiar investigaciones privadas.

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

### 2026-09-18 — Control conservador de consolidación

- Bloqueo de Writer cuando una hipótesis del alcance aprobado sigue pendiente.
- Informes provisionales, archivo local de informes anteriores y avisos en frontend/Obsidian.
- Fuentes restringidas no se convierten en refutación; veredictos históricos requieren revisión explícita.
- Corregido panel de alcance en Pregunta y envío del expediente al solicitar su revisión.

### 2026-09-18 — Ampliación acumulativa del alcance

- scope-v2 mantiene el alcance aprobado mientras prepara una ampliación independiente.
- Añade hasta tres hipótesis por lote; sin límite total de tres por expediente.
- Propuestas manuales UNVERIFIED y cancelación de ampliaciones con historial.
- Consolidación bloqueada mientras exista una ampliación sin decidir; sin borrar evidencia ni reiniciar revisiones vigentes.

### 2026-09-18 — Eliminar investigación

- Eliminación recuperable desde frontend con confirmación del nombre.
- Retirada aislada de biblioteca y Obsidian, copia de notas personales, bloqueo mientras hay tareas activas y conservación de evidencia compartida.
- Formulario nuevo después de eliminar; índices regenerados y sincronización con aviso de fallos.

### 2026-09-18 — Correcciones de clasificación de fuentes

- El validador permite corregir anotaciones de primariedad, oficialidad, tipo y relación sin confundirlas con evidencia eliminada. Mantiene inmutables identidad, extracto y recuperación originales.
- Cambios de anotaciones trazados en provenance; futuras fallas del frontend conservan el error específico del proceso.

## 2026-09-18 — Traspaso seguro a ChatGPT web
Actualizadas guía, instrucciones y estado de continuidad con las capacidades actuales. Entrega con código sin publicar, manifiesto SHA-256 y copia aislada. Nuevo verificador de hashes y parche sin aplicación; bloqueo de rutas privadas. Nuevo respaldo privado que rechaza trabajos activos y no marca copias que cambiaron como completas. Flujo de aplicación/pruebas por Antigravity y commit/push manuales. Pruebas: 57 existentes en copia aislada y 7 nuevas de traspaso. Carga web y respaldo real pendientes de sesión iniciada y fin de investigación.

## 2026-09-18 — Recuperación y revisión accesible
Collector completo validado se conserva antes de Skeptic y puede reutilizarse con TTL de seis horas e invalidación explícita; veredictos y comprobaciones externas siguen independientes. Progreso separa lote pendiente, alcance y evaluaciones conservadas. Revisión humana opcional con evidencia congelada e historial, sin promover estados; informe exportable a Obsidian. Recuperación PDF excluye coincidencias cero y permite respaldo documental comprobable sin URL accesible adicional. Respaldo privado real terminado tras inactividad.

## 2026-09-18 — Identidad de referencias y trazabilidad
Deduplicación conservadora antes de contar corroboraciones; IDs calculados de fuentes y pasajes, relaciones de contexto/contradicción separadas del apoyo. CONTRADICTED exige refutación explícita con pasaje comprobado. Recibos de inicio/final/duración/estado por llamada y atribución de acciones a entradas registradas, conservando origen de Collector reutilizado. Actividad incorpora decisiones del alcance y observaciones humanas opcionales. No se reclasifican silenciosamente expedientes históricos ni se acredita autenticidad con un identificador. Ver guides/FUENTES-Y-TRAZABILIDAD.md.

## 2026-09-18 — Orientación, accesibilidad y reutilización
Bloqueos explican importancia, responsable y plan disponible al reevaluar sin fingir intentos ejecutados. Foco visible, salto de teclado y vista móvil en una columna. Candidatos web limitados entre expedientes, sin copiar veredictos; revisión estructurada de pertinencia con límites y revalidación externa. Comparador de registros controla pregunta/alcance y conserva desconocidos cuando faltan recibos o auditoría. No demuestra superioridad de especialización ni completa accesibilidad o recuperación semántica. Ver guides/REUTILIZACION-Y-ACCESIBILIDAD.md.
