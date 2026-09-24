# Pendientes del proyecto

Repositorio oficial: https://github.com/exjade/Obsidian-Gemini-Research

Esta lista describe trabajo por hacer, no funciones ya disponibles. La publicación de cada entrega es manual por el propietario. H1 está implementado localmente; no se presupone que todos sus ajustes posteriores estén publicados.


## Nuevo bloque acordado — accesibilidad, alcance y agentes especializados

Orden de trabajo: alcance → recuperación documental → control de cierre y auditoría de respuesta → navegación accesible.

- [x] Proponer pocas hipótesis y revisar pertinencia, duplicados y presuposiciones antes de pedir aprobación del alcance. Primera entrega local; máximo tres nuevas por lote, no por expediente. Edición de formulaciones y preguntas todavía pendiente.
- [x] Registrar origen declarado, corrida del generador, revisión y aprobación del alcance; revisión explícita de expedientes antiguos sin reclasificar claims.
- [x] Ampliación acumulativa: hasta tres hipótesis adicionales por lote, sin sustituir las anteriores; propuestas del usuario, revisión y aprobación explícitas, cancelación de ampliación e historial.
- [ ] Edición, retirada e invalidación de claims investigados.
  - [x] Proponer una formulación más estrecha como claim descendiente versionado, preservando el original y sin heredar evidencia ni veredicto.
  - [ ] Editar, retirar o invalidar formulaciones con motivo y versiones de evidencia; no borrar revisiones automáticamente.
- [ ] Modos de investigación y expansión supervisada de evidencia.
  - [x] Elegir entre pregunta con búsqueda, sólo documentos y documentos con búsqueda complementaria.
  - [x] Dirigir búsquedas posteriores a dimensiones pendientes y registrar conclusiones que podrían verse afectadas.
  - [ ] Ampliar la recuperación semántica, multilingüe y documental más allá de los resolutores actuales.
- [ ] Recuperación automática con presupuesto acotado.
  - [x] Primera entrega: tres rondas, presupuesto por consultas/páginas/tiempo, operaciones persistentes y rechazo de salidas parciales.
  - [ ] Comparar agentes especializados con el flujo anterior en una prueba controlada real; auditar errores, cobertura y respaldo.
- [x] Separar credibilidad, primariedad, independencia y respaldo concreto de cada afirmación en registros versionados para evaluaciones nuevas. La independencia científica externa y la autenticidad no se infieren automáticamente.
- [x] Skills especializadas: planificador, revisor de formulación, localizador, recuperador, evaluador de fuentes, evaluador de pertinencia, Skeptic, Writer y auditor final; llamadas independientes coordinadas por el wrapper.
- [x] Primera validación estructural de entregables de agentes, pasajes, matrices y auditoría con artefactos versionados; evaluación comparativa real pendiente.
- [x] Primera auditoría de respuesta contra dimensiones del claim, pasajes, veredicto y errores temporales; ampliar reglas por dominio sigue pendiente.
- [ ] Cierre científico de todas las hipótesis admitidas.
  - [x] Exigir respaldo o refutación directa comprobados; la ausencia de respaldo no equivale a refutación.
  - [x] Registrar una resolución científica versionada y auditable, separada del veredicto histórico, para respaldo, refutación directa o indeterminación justificada.
  - [x] Revalidar identidad, política, dimensiones, pasajes y criterios de una resolución persistida antes de permitir el cierre del alcance.
  - [ ] Ampliar criterios de cierre y auditoría a dominios específicos.
- [x] Separar ejecución terminada, investigación inconclusa y resultados consolidados; informes provisionales con bloqueos y siguiente acción. Primera entrega local; ver guides/CIERRE-CIENTIFICO.md.
- [x] Explicar bloqueos, importancia, responsable, plan disponible al reevaluar y ayuda eventual, sin presentar intentos pendientes como ejecutados. Recuperación alternativa automática sigue en su tarea independiente.
- [x] Primera entrega de accesibilidad: foco visible, salto al contenido, navegación por teclado y adaptación móvil conservando comprobar fuentes, reevaluar, auditoría y detalle avanzado.
- [ ] Auditoría completa con lector de pantalla, teléfono físico y formularios/estados extensos; acceso remoto móvil sigue siendo H6.
- [x] Herramienta reproducible para comparar registros equivalentes: revisiones, pasajes, llamadas, fallos y tiempos; calidad desconocida sin revisión independiente.
- [ ] Ejecutar comparación controlada real de especialización frente al flujo anterior y auditar errores de contenido, cobertura y respaldo; no inferir superioridad desde pruebas sintéticas.

No exigir usar todo el archivo contextual: cubrir el alcance aprobado y considerar evidencia pertinente, especialmente contradictoria. No garantizar ausencia total de alucinaciones. Presupuesto acordado: recuperación limitada; cierre estricto sobre hipótesis admitidas; cambios de alcance explícitos.

## Prioridad 1 — Poder revisar una investigación sin conocimientos técnicos

- [x] H1.1: guía dentro del frontend: qué investigar, qué revisar y qué hacer después.
- [x] Ficha individual con evidencia, motivo registrado y siguientes acciones; mejorar aún la explicación automática de motivos.
- [x] Mostrar por afirmación huecos de recuperación comprobados, separados del motivo del modelo. La evaluación automática nueva conserva auditoría claim-pasaje; la revisión humana del apoyo completo sigue siendo opcional y separada.
- [x] Incorporar enlaces/texto de apoyo a una afirmación del mismo expediente con historial de solicitudes.
- [x] Solicitar nuevas investigaciones o revisiones desde la ficha de una afirmación ya clasificada.
  - [x] Conservar la revisión supervisada y su historial de solicitudes.
  - [x] Permitir «Investigar de nuevo» con operación independiente tras resultados terminados; distinguirlo del retry, conservar el resultado anterior y el historial hasta que el nuevo cierre, y agrupar clics concurrentes equivalentes.
- [x] Revisión humana opcional registrada por ficha: actor declarado, fecha, evidencia examinada congelada, observación y límites; historial y exportación a Obsidian. No cambia veredictos ni el cierre científico. Autenticación de identidad humana pendiente.

## H2 — Nuevo bloque: evidencia documental local (2026-09-18)

### Recuperación del Collector — primera entrega local

- [x] Collector/Skeptic por afirmación con registros separados, avance visible y veredictos completos guardados antes de continuar.
- [x] Reintento de pendientes sin repetir revisiones completas con la política actual; diagnóstico consistente con 900 segundos por llamada.
- [x] Entradas exactas del proveedor conservadas por pasada y afirmación.
- [x] Publicación local inconclusa registrada como terminada, separada de hechos consolidados.
- [x] Contadores de auditoría con alcance explícito: expediente o repositorio.
- [x] Reutilizar Collector completo validado cuando falla Skeptic; TTL seis horas e invalidación por entradas, alcance, contratos, política, documentos y archivos utilizados. Sin importar salidas parciales ni promover evidencia a veredicto.
- [x] Extracción documental versionada y reutilización local de fragmentos; contexto e identidad conservados.
- [x] Primera reutilización entre expedientes de pasajes web: candidatos léxicos limitados, origen conservado, revisión estructurada de pertinencia por Skeptic y revalidación externa; no copiar veredictos.
- [ ] Búsqueda semántica/multilingüe, PDFs asociados explícitamente, revisión independiente y catálogo definitivo de relaciones entre expedientes.

Ver guides/ROBUSTEZ-Y-EVIDENCIA-DOCUMENTAL.md para operación, límites y prioridad siguiente.

Primera implementación documental local disponible; ver guides/ENTREGA-PDF-Y-DOCLING.md. H2 sigue incompleto.

- [x] Benchmark aislado Docling CPU nativo/estándar sin OCR con dos PDFs reales y pasajes revisados visualmente por el agente. No es ground truth humano ni evaluación ciega.
- [x] Baseline aislado de los dos PDFs aportados: extracción nativa pypdf por página, identidad SHA-256, copia intacta y revisión visual inicial. No sustituye benchmark Docling ni ground truth humano; ver guides/PRUEBA-PDF-LOCAL.md.
- [x] Registro opcional de documentos: original inmutable, hash, procedencia, versión y asociación a expediente.
- [x] Extracción paginada versionada con límites/errores; distinguir página física e impresa.
- [x] Recuperación léxica con contexto y manifiestos de fragmentos enviados a Collector/Skeptic.
- [x] Evidencia PDF validada y reevaluación selectiva, sin promoción automática por extracción.
- [ ] Explorar NotebookLM MCP aislado como recuperación opcional; cotejar citas con copia local.
- [ ] OCR por página y documentos mixtos como fase posterior; no añadir PaddleOCR todavía.

## Prioridad 2 — H2: fuentes comprobables y correcciones de verificación

- [x] Comprobar URL original/final, estado HTTP, fecha, restricciones y contenido conservado (GET limitado; HTML/texto).
- [x] Mostrar accesible, caída, restringida o pendiente sin convertir accesibilidad en verdad.
- [x] Conservar extractos/snapshots con origen, fecha, hash, URL normalizada, redirecciones e identificadores reconocibles; las evaluaciones nuevas registran aparte si el pasaje apoya exactamente la afirmación.
- [ ] Catálogo definitivo de fuentes y relaciones estables.
  - [x] Catálogo versionado por IDs ya persistidos; pasajes con roles por relación afirmación-pasaje; registros sin IDs históricos excluidos; relaciones entre expedientes por IDs estables.
  - [ ] Resolver metadatos bibliográficos externos con fuentes controladas.
    - [x] Entrega inicial local para DOI/PMID/PMCID declarados, recibos verificables y catálogo offline determinista; revisada y aceptada por C2C.
    - [ ] Ampliar cobertura más allá de esos identificadores; no implica validar autenticidad, independencia ni apoyo científico.
  - [x] Consolidar metadatos locales versionados desde declaraciones guardadas y recibos técnicos ligados a la evidencia; conservar procedencia y conflictos sin reidentificar fuentes.
- [ ] Revisar primariedad e independencia. Implementados estados y bases separados, deduplicación explicable y rechazo conservador: «no duplicada» no significa «independiente». La confirmación científica externa, metadatos completos y migración siguen pendientes.
- [ ] Separar afirmaciones compuestas para no verificar varias conclusiones con una evidencia parcial.
  - [x] Primera descomposición estructurada en dimensiones y subpreguntas sin alterar el texto original; dirigir la recuperación a huecos y asociar pasajes por dimensión.
  - [ ] Detectar y proponer la separación automática de proposiciones independientes con revisión de alcance.
- [x] Exigir para CONTRADICTED un pasaje contradictorio comprobado y auditado semánticamente en evaluaciones nuevas; mismatch, unreported, ausencia de respaldo, detección o URL accesible no refutan.
- [ ] Revisar la política legal: distinguir normas de hechos procesales. Para hechos, considerar documentos judiciales oficiales pertinentes (acusación, resolución, expediente, transcripción), sin admitir resúmenes como texto normativo.
- [ ] Revisar detección de dominios sensibles: una imputación de corrupción no debe depender únicamente de que el modelo se autodetecte como sensible.
- [ ] Backup, migración y reevaluación explícita de expedientes antiguos; nunca cambiar estados silenciosamente.
  - [x] Herramienta local de vista previa/aplicación idempotente y recuperable para añadir IDs sin alterar revisiones o veredictos; revisada y aceptada por C2C.
  - [ ] Ejecutar migración sobre expedientes reales sólo tras respaldo verificado y revisión explícita de la vista previa.

## Prioridad 3 — H3–H4: trazabilidad y método

- [ ] H3: trazabilidad comprobable de las operaciones.
  - [x] Mostrar etapa, presupuesto, recorte, consultas agrupadas, manifiestos y descarga completa.
  - [x] Historial durable por afirmación para investigaciones, errores scoped y comprobaciones técnicas; la cronología del claim y Actividad consumen una proyección backend compartida, con orden estable, deduplicación por identidad y enlaces a la ficha.
  - [ ] Transmitir cada herramienta durante la ejecución.
  - [ ] Registrar y presentar duración individual de cada herramienta cuando el proveedor la exponga.
- [ ] Explicación del veredicto enlazada con evidencia a favor/en contra y regla aplicada.
- [x] Separar explicación del modelo de eventos observados; atribución y acciones reutilizadas identificadas. No se promete pensamiento interno completo.
- [ ] H4: método comprobable por hipótesis.
  - [x] Primera entrega versionada por claim: subpreguntas, hipótesis competidoras y criterios de refutación.
  - [x] Proyectar una cronología durable por claim con identidades estables, orden determinista y fechas faltantes explícitas; Actividad reutiliza esa proyección y separa investigaciones, cambios de veredicto, resoluciones, comprobaciones, revisión humana y reformulaciones.
  - [ ] Completar límites metodológicos y cobertura H4 por dominio.
- [ ] Rúbrica explicable de fuerza de evidencia; sin inventar probabilidad de verdad ni anular contradicciones con un puntaje.
  - [x] Primera rúbrica categórica por dimensión/pasaje, sin probabilidades de verdad y conservando evidencia mixta.
  - [ ] Calibrar y documentar la rúbrica para dominios y diseños de estudio distintos.

## Prioridad 4 — H5–H6: uso cotidiano

- [ ] H5: diagnosticar y evitar consolas auxiliares inesperadas, conservando errores y modo diagnóstico.
- [ ] Controles claros para arrancar, detener y recuperar el servicio.
- [ ] H6: móvil optativo, autenticado y revocable; mantener acceso local por defecto.

## Prioridad 5 — H7–H10: Studio y cerebro de Obsidian

- [ ] H7: versiones/snapshots e informes citados; señalar artefactos desactualizados.
- [ ] H8: notas de afirmaciones/fuentes, relaciones tipadas, mapa mental y grafo navegable, protegiendo notas personales.
- [ ] H9: flashcards y cuestionarios con evidencia, incertidumbres apartadas y control de versiones.
- [ ] H10: infografías/cronologías con datos citados, unidades, incertidumbre y revisión.

## Publicación y extras aún no implementados

- [ ] Elegir licencia y añadir LICENSE.
- [ ] Revisar/publicar ajustes finales de H1 y conservar referencia de cada hito.
- [ ] Automatizar pruebas sin IA en GitHub; no asumir que los resultados locales ya son CI.
- [ ] Interpretación de imágenes y PDFs escaneados: OCR pendiente. PDFs digitales tienen extracción opcional paginada; no verifica veracidad automáticamente.
- [ ] Homelab/remoto: no está implementado; la copia local a Obsidian y MCP de lectura son mecanismos diferentes.

Ver ROADMAP.md para criterios de aceptación y dependencias. La primera entrega del resolutor controlado y la herramienta de migración están implementadas localmente, pendientes de revisión C2C; no se han aplicado a fuentes o expedientes reales. Falta establecer independencia científica con comprobación externa. Después, abordar claims compuestos y revisar la migración histórica coordinada descrita arriba, antes de Studio.


## Claridad de estados y revisión

Implementado: aviso global separado de errores por operación; resultado científico vigente separado del último intento; Actividad y cronología derivadas de registros persistidos y de la misma proyección backend; auditoría estructurada, vistas vacías explicadas y avisos nativos en Obsidian. Pendiente: transmisión de herramientas en vivo y atribución exclusiva de acciones a cada afirmación en lotes. Guía: [Estados y recorrido](guides/ESTADOS-Y-RECORRIDO.md).


## Guía y actividad de investigación

Barra de etapas documentadas (separada de certeza), guía de lectura, Actividad reconstruida de registros con enlaces, referencias numeradas con fondos distintos y explicaciones sin banderas de programación en la vista principal. Nuevos ángulos preparan preguntas para investigaciones independientes; no son hallazgos de IA ya ejecutada. [Cómo entender una investigación](guides/COMO-ENTENDER-UNA-INVESTIGACION.md).

## Entrega de cierre conservador

Writer no consolida un subconjunto cuando otra hipótesis admitida sigue pendiente. Fuentes bloqueadas no se convierten en refutación. La primera resolución indeterminada ya se registra con sus criterios, recibos y límites, separada del veredicto histórico; siguen pendientes su calibración por dominio, el auditor semántico completo de respuesta y la comparación real de recuperación. Los expedientes históricos no cambian de veredicto.

## Alcance acumulativo — entrega local

El botón Ampliar alcance revisa candidatos fuera del alcance, mantiene los admitidos y añade hasta tres por aprobación. Proponer una nueva hipótesis la registra UNVERIFIED sin iniciar Antigravity. Una ampliación pendiente necesita aprobarse o descartarse antes de consolidar; las evaluaciones previas permanecen disponibles. Retirar, invalidar o reformular una hipótesis admitida son acciones distintas todavía pendientes.

## Gestión de investigaciones

- [x] Eliminar investigación del frontend con confirmación, bloqueo durante ejecución, copias recuperables del expediente y notas de Obsidian; conservar documentos compartidos y actualizar navegación.
- [ ] Pantalla de papelera y restauración selectiva con comprobación de conflictos.
- [ ] Vaciado definitivo de papelera mediante confirmación específica.

## Corrección de fallos de investigación

- [x] Permitir que Skeptic corrija clasificación de fuentes sin perder payloads originales; cambios trazados y protección de URLs/documentos/extractos.
- [x] Conservar y presentar errores específicos sin mezclarlos con el estado global.
  - [x] Mostrar errores del proceso general en la interfaz.
  - [x] Asociar errores de `claim_research` a su operación persistente y presentarlos junto al historial, aunque exista un resultado anterior vigente.
- [x] Recuperación de Collector validado y trazabilidad del origen; nuevas comprobaciones externas al revisar. Ver guides/REVISION-Y-RECUPERACION.md.

## Continuidad segura hacia ChatGPT web — 2026-09-18
- [x] Guía, instrucciones y estado actualizados para PDFs, alcance acumulativo y cierre científico.
- [x] Paquete de código actual incluyendo archivos nuevos y cambios sin commit; manifiesto SHA-256 y copia aislada sin datos reales.
- [x] Verificador de base/parche sin aplicar cambios, protección de rutas privadas y respaldo privado con rechazo de actividad y detección de cambios.
- [x] Flujo ChatGPT normal → Antigravity → validación aislada → integración por archivo; commit/push manuales.
- [ ] Cargar entrega al proyecto web: el navegador disponible requiere iniciar sesión.
- [x] Respaldo privado real completo del proyecto y vault tras finalizar la investigación, con hashes y marcador COMPLETE. No publicado ni incluido en el paquete web.
- [x] Progreso del reintento separado del alcance y de evaluaciones conservadas; explicación de evaluación frente a resolución científica y recuperación de errores.

## Avance local — revisión accesible y recuperación
- [x] Los PDFs cotejados pueden respaldar claims externos sin exigir además URL accesible; se conserva la política de evidencia.
- [x] Recuperación léxica excluye fragmentos sin coincidencias; no equivale a pertinencia semántica comprobada.
- [x] Mensajes orientan a reevaluar con materiales existentes, sin exigir aportes adicionales en todos los casos.
Ya están implementadas las señales deterministas de identidad, las evaluaciones versionadas que separan identidad, primariedad, independencia, acceso y credibilidad, y la auditoría claim–pasaje para evaluaciones nuevas. La primera descomposición estructurada de claims y resolución científica versionada ya está implementada; continúan pendientes la resolución definitiva de metadatos y catálogo, establecer independencia científica mediante comprobación externa, detectar proposiciones independientes para separarlas, migrar explícitamente expedientes históricos y ampliar la recuperación alternativa. El auditor semántico completo de la respuesta final sigue siendo un trabajo distinto pendiente.

## Avance local — identidad, refutación y trazabilidad
- [x] IDs calculados de fuentes/pasajes y señales de duplicación, sin acreditar autenticidad ni modificar veredictos históricos.
- [x] Contexto y contradicción separados de referencias de apoyo al contar fuentes primarias.
- [x] Registro persistente de tiempo y estado del proveedor por llamada, conservado en fallas.
- [x] Actividad con decisiones de alcance, observaciones humanas y recibos de ejecución disponibles.
Ver guides/FUENTES-Y-TRAZABILIDAD.md para operación y límites. H2/H3/H4 completos permanecen pendientes; esta entrega cubre sólo sus primeros hitos de resolución científica, dimensiones y rúbrica.

## Avance local — orientación y reutilización supervisada
Ver guides/REUTILIZACION-Y-ACCESIBILIDAD.md. Planes disponibles no son acciones ejecutadas; coincidencia léxica no demuestra pertinencia. El sistema exige registrar pertinencia para cada pasaje reutilizado, pero la evaluación semántica sigue dependiendo del modelo. Comparación científica y accesibilidad completa permanecen pendientes.
