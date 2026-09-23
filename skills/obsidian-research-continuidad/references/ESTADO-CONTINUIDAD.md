# Estado de continuidad — entrega actual

Fecha UTC: 2026-09-18T23:31:48.029499+00:00
Commit base: 5aab9c311516faaa086a7da166970764e8970449. Incluye cambios locales y archivos nuevos SIN COMMIT.
El remoto no se ha comprobado ni actualizado. El manifiesto SHA-256 identifica los bytes de esta entrega.

## Implementado en el código entregado
- Antigravity CLI (agy), Python estándar y frontend HTML/JavaScript en español.
- Expedientes aislados, reevaluación selectiva y comprobación independiente de fuentes.
- PDFs originales conservados con hash; extracción opcional Docling/pypdf por página, fragmentos y registros de recuperación para Collector/Skeptic. Sin OCR ni NotebookLM integrado. Un PDF local no implica autenticidad ni respaldo.
- Alcance aprobado acumulativo: agregar hipótesis sin borrar las anteriores; historial y cancelación de propuestas. Edición/retirada de hipótesis admitidas todavía pendiente.
- Cierre científico conservador: ejecución terminada distinta de investigación resuelta; bloqueos y resultados provisionales visibles. No fabricar consenso ni convertir falta de evidencia en refutación.
- Evaluación por afirmación, guardando cada veredicto completo antes de continuar; timeout de 900 segundos por llamada al proveedor (Collector y Skeptic por separado).
- PASS 3 puede corregir clasificación de fuentes sin alterar URL, extracto ni identidad documental; cambios de anotaciones registrados.
- Eliminación recuperable de expedientes; restaura interfaz pendiente. Notas personales protegidas.

## Nueva entrega de identidad y trazabilidad
IDs calculados para fuente/pasaje y deduplicación conservadora por señales documentales; roles apoyo/contradicción/contexto/sin revisar. CONTRADICTED exige pasaje de refutación técnicamente comprobado. Recibos persistentes por llamada y acciones atribuidas según entradas guardadas, conservando origen de Collector reutilizado. Actividad incluye decisiones del alcance y revisiones humanas. Ver guides/FUENTES-Y-TRAZABILIDAD.md. No acredita autenticidad ni independencia científica; catálogo definitivo y auditoría semántica pendientes.

## Orientación y reutilización — nueva entrega
Planes disponibles de recuperación separados de intentos ejecutados. Primera accesibilidad de teclado/móvil (390px comprobados), conservando controles avanzados. Pasajes web de otros expedientes se proponen con búsqueda léxica limitada, sin veredictos; Skeptic debe registrar pertinencia, relación, motivo y límites para cada pasaje reutilizado. Comparador de registros sin IA; comparación científica real pendiente. PDFs entre expedientes y búsqueda semántica/multilingüe pendientes. Ver guides/REUTILIZACION-Y-ACCESIBILIDAD.md.

## Primera tarea en ChatGPT web
Progreso claro ya implementado localmente. Próximo hito: distinguir credibilidad, primariedad, independencia e identidad documental de respaldo concreto; automatizar metadatos e identidad documental y comprobar primariedad/independencia sin reclasificar silenciosamente expedientes. Consultar el código y PENDIENTES actualizado antes de acotar el hito.

## Pendientes relevantes
Collector validado ya se reutiliza durante seis horas cuando las mismas entradas siguen vigentes; recuperación automática de URLs bloqueadas; auditoría automática de identidad documental; catálogo documental definitivo y auditoría de primariedad/independencia; auditor de salida; cierre indeterminado justificado; agentes especializados adicionales. Más agentes no garantiza mejores resultados. Consultar PENDIENTES completo.

## Validación y límites
Entrega actual: 103 pruebas aprobadas y validate_pipeline.py aprobado, sin proveedor real; sintaxis JavaScript y git diff --check aprobados. Consultar VALIDACION-ENTREGA.txt para los controles ejecutados ahora.
No se ejecuta investigación real para probar cambios. No se actualizaron las fuentes del proyecto web privado en esta entrega. Servicio actualizado disponible en http://127.0.0.1:8770/ (PID 10316). El servicio propio 8770 se reinició tras comprobar inactividad. Las instancias anteriores no se actualizaron en esta entrega. Evitar ejecutar trabajos simultáneos en ambas interfaces.

Respaldo privado real completo tras inactividad, con COMPLETE en work/private-backups/20260918T232644Z. El propietario debe sustituir las cinco fuentes de desarrollo de la entrega anterior.

Nueva entrega: revisión humana opcional separada del veredicto y con evidencia congelada; recuperación de Collector completa con invalidación; progreso separado; PDFs cotejados aceptados sin URL adicional; se excluyen fragmentos sin coincidencias. Ver guides/REVISION-Y-RECUPERACION.md.

## Continuar y volver a Codex
ChatGPT normal prepara un hito y Antigravity valida/aplica en la copia aislada. Commit/push manuales por el propietario. Tras cada hito actualizar este único estado con versión, archivos, pruebas reales, límites y siguiente tarea. Las guías antiguas adjuntas no prevalecen sobre código y manifiesto actuales.
