# Uso y configuración

## Biblioteca central y expedientes

La pantalla inicial ofrece búsqueda de título, pregunta, enlaces, etiquetas y afirmaciones; filtros por etiqueta y estado; paginación de doce expedientes; y catálogo central de fuentes. Al abrir un expediente se muestran sus propios resultados, fuentes, claims, auditoría, notas personales y adjuntos descargables. El botón Abrir en Obsidian abre su resumen. Las relacionadas comparten etiquetas o URLs: son enlaces de navegación, no corroboración.

Los expedientes viven en .project-intelligence/library/<id>/ y se publican en Investigaciones/<id>/ del vault. Cada claim nuevo del frontend conserva investigation_id. Las pasadas con --case seleccionan ese expediente; sus resultados no mezclan afirmaciones de otras investigaciones. Las acciones de terminal sin --case conservan la documentación general del sistema. --brief permite texto largo sin límites de longitud de comando.

El histórico importa los registros previos sin inventar una pregunta original ni repetir una verificación. Puede contener referencias desactualizadas. Los estados de ejecución, como completed o error, son distintos de los veredictos VERIFIED/PARTIAL/UNSUPPORTED/CONTRADICTED.

Mis notas se leen del vault si existe su copia. Guardarlas desde el frontend actualiza ambas ubicaciones; la publicación nunca sobrescribe notas.md existente. Gestiona las etiquetas desde el frontend para regenerar los índices; el YAML generado de resumen.md se reconstruye. Biblioteca.md, Temas.md, Fuentes.md y Guia.md proporcionan navegación en Obsidian.

Reintentar un expediente sin claims retoma su brief; con claims guardados retoma document sin duplicar hipótesis. Tras reiniciar el servicio sin lock activo, los expedientes pendientes se marcan interrumpidos. No se borra automáticamente un lock de una ejecución que pueda seguir activa.

Referencias técnicas primarias: [Etiquetas](https://obsidian.md/help/tags) y [Obsidian URI](https://help.obsidian.md/Extending+Obsidian/Obsidian+URI). El catálogo agrupa URLs exactas sin fragmento; esa agrupación no verifica independencia ni apoyo semántico. Las etiquetas, notas personales y enlaces aportados no constituyen evidencia verificada por sí mismos.

Los wrappers de esta carpeta comparten `pipeline.py`, que usa únicamente la biblioteca estándar de Python 3.10 o posterior. Comprueban que python3, python o py sea un intérprete funcional; omiten los accesos directos a Microsoft Store. No requieren jq. Los wrappers de la raíz también delegan al pipeline activo; los originales antiguos se archivaron localmente en .project-intelligence/legacy/.

Desde Git Bash, en Windows:

```bash
cd /y/ChatGPT/obsidian-gemini-research/my_docs
bash scripts/research.sh "tema o pregunta"
bash scripts/document.sh
bash scripts/changelog.sh
```

En WSL debes usar la ruta donde hayas montado Y: y disponer de Python, Git y Antigravity en ese entorno. Python puede ejecutar el mismo flujo directamente: `python scripts/pipeline.py research "tema"`.

Antigravity CLI debe estar instalado y autenticado. El pipeline resuelve agy en PATH o, en Windows, en %LOCALAPPDATA%/agy/bin/agy.exe. Cada pasada inicia un proceso independiente con --input-format stream-json, --output-format stream-json y --disable-slash-commands. Envía un único evento user por stdin y cierra el pipe. Valida exactamente un result final con status SUCCESS, código de salida 0 y respuesta no vacía. Conserva los eventos completos y stderr incluso al fallar; el timeout local es de 360 segundos. El contrato GEMINI.md se incluye íntegro en cada prompt, junto con la raíz absoluta del proyecto.

El Collector recibe candidatos sin razonamiento previo. El Skeptic recibe únicamente IDs, claims y evidencias; el Writer recibe solo VERIFIED. El contrato completo permanece en GEMINI.md, incluida su posibilidad de usar PARTIAL; estos wrappers aplican el requisito más estricto del proyecto y publican únicamente VERIFIED.

Las referencias de archivo se verifican contra líneas y extractos reales; los commits deben existir y tener SHA completo. Las referencias externas requieren URL, extracto, fecha y registro explícito de búsqueda y fetch. Ese registro procede de Gemini: la validación estructural no demuestra por sí sola que una fuente soporte semánticamente un claim ni que el agente haya usado las herramientas correctamente. Conserva y revisa las evidencias y veredictos. Si una herramienta o permiso de lectura falta, el agente debe declarar la limitación y dejar el claim sin verificar. Se añadió únicamente read_file(Y:/ChatGPT/obsidian-gemini-research/my_docs) a permissions.allow en la configuración global de Antigravity para permitir las lecturas headless del proyecto. Los permisos para comandos, escritura, MCP y actuación web permanecen sin cambios. La lectura web usa read_url(*) para evitar que una fuente nueva bloquee las pasadas headless. No se activa --dangerously-skip-permissions.

`research` guarda candidatos en los registros de architecture/dependencies. `document` evalúa UNVERIFIED, conserva todos los veredictos y reconstruye docs/architecture.md y docs/research.md desde los VERIFIED acumulados. Para reexaminar cambios de código, ejecuta research de nuevo: un VERIFIED antiguo no se revalida automáticamente salvo las comprobaciones de referencias antes de publicar. Un fallo de Writer puede reintentarse con document sin perder veredictos. No edites manualmente esos dos documentos si necesitas conservar texto: Writer los reconstruye.

`changelog` exige un repositorio Git con HEAD y archivos de entrada limpios antes de ejecutar; excluye de esa comprobación los registros de .project-intelligence y los documentos generados architecture.md, research.md y changelog/. No inicializa Git ni crea commits. Procesa commits desde last_commit hasta HEAD; la primera ejecución incluye todo el historial alcanzable. Se adjuntan diff completo, commits con patches y contenido de archivos afectados. Si last_commit ya no es ancestro de HEAD, se detiene sin elegir otra base. Los cambios sin commit no se incluyen. Un lote sin VERIFIED produce una entrada que declara la ausencia de claims consolidados; los otros estados permanecen en claims y reports. last_commit avanza solo después de guardar el changelog. Al reintentar el mismo rango se reutilizan sus claims guardados. Los nombres incluyen fecha, hora e identificador para evitar sobrescrituras.

state.json usa fecha UTC ISO 8601; last_commit se refiere exclusivamente al último changelog procesado. Los contadores se recalculan desde los tres registros canónicos, sin contar salidas crudas ni sumar por cada reprocesamiento. Un lock evita ejecuciones simultáneas. Si una interrupción abrupta deja pipeline.lock, comprueba que ya no corre el proceso indicado antes de retirar ese archivo. Cada archivo se reemplaza mediante un temporal; el conjunto de archivos no constituye una transacción de base de datos.

## Obsidian: vault independiente

El vault del proyecto está en `Y:\Obsidian\obsidian-gemini-research`, separado de Work. Antigravity tiene el servidor `obsidian` con MCPVault 0.16.0 en modo de solo lectura. Reinicia las sesiones existentes después de cambiar la conexión. `.gemini/settings.json` es la configuración antigua de Gemini; la conexión activa pertenece a Antigravity.

`.project-intelligence/obsidian.json` configura el destino local. Al finalizar document/changelog, el pipeline ejecuta `scripts/obsidian_sync.py` con el mismo Python. Publica todos los Markdown de docs/ y los reportes sources.md y audit-flags.md en auditoria/. Verifica cada copia byte por byte y registra destinos y SHA-256 en reports/obsidian-receipt.json antes de marcar SYNCED. Conserva la cola si falla. `python scripts/pipeline.py document --sync-only` reintenta sin ejecutar las pasadas de IA.

La publicación usa el sistema de archivos local; MCP da acceso de lectura al resultado. No hay servidor remoto de homelab configurado. No copia logs crudos ni credenciales y no borra archivos del vault. Los documentos publicados se regeneran desde el repositorio: evita editarlos directamente en el vault. Las referencias de código y artefactos de procedencia corresponden al repositorio original, no a archivos trasladados al vault.

Un OBSIDIAN_SYNC_HOOK explícito conserva prioridad sobre el adaptador local. Su contrato sigue siendo recibir el manifiesto como único argumento y devolver cero solo después de confirmar la publicación.

## Referencias oficiales consultadas al crear el esqueleto

- [Modo headless y respuesta JSON](https://geminicli.com/docs/cli/headless/)
- [Configuración de Gemini CLI](https://geminicli.com/docs/reference/configuration/)
- [Servidores MCP](https://geminicli.com/docs/tools/mcp-server/)

Se probó el transporte real y una investigación local mínima con Antigravity; no se generó contenido de negocio.

## Referencia de la migración

[Headless, NDJSON por stdin y eventos result de Antigravity](https://antigravity.google/docs/cli/headless)
[Permisos de lectura por carpeta](https://antigravity.google/docs/cli/permissions)

## Lectura web headless

En ~/.gemini/antigravity-cli/settings.json se configuró permissions.allow con read_url(*), además de la lectura local limitada a este proyecto. Las reglas específicas para Google, Python y Antigravity se conservan. El permiso general permite consultar fuentes y buscar contraevidencia sin bloquear cada dominio nuevo; no concede execute_url, comandos ni escritura. La calidad de la fuente se evalúa separadamente: prioriza documentación oficial y no uses páginas de otro producto como soporte.

Si una lectura se bloquea por una regla deny/ask con mayor prioridad y la respuesta queda vacía, el error identifica el dominio. Los logs se conservan y no se publica documentación. Reintenta document tras corregir la configuración pertinente; no necesitas volver a ejecutar research.

## Política de sesgo y dominios sensibles (risk-flags-v1)

El contrato añade el árbol de PASS 3 para legal, médico, fiscal, migratorio y seguridad, junto con la bandera favorable. Cada veredicto incluye domain, sensible, favorable, primary_sources y skeptic_note. El wrapper fuerza sensible cuando domain está en esa lista, exige índices de evidencia reales y justificación de independencia, descarta fuentes externas no declaradas primarias/oficiales y no cuenta URLs duplicadas ni grupos de origen repetidos. En legal solo acepta tipos law, regulation o jurisprudence; un resumen no cuenta. Con una sola fuente de apoyo, un claim marcado no puede llegar VERIFIED a Writer; queda PARTIAL. Sin fuente primaria de apoyo queda UNSUPPORTED. CONTRADICTED conserva prioridad.

El conteo y el bloqueo son controles estructurales. La identidad oficial, el carácter primario, la independencia entre documentos diferentes, el dominio y la favorabilidad siguen requiriendo juicio y revisión: no se verifican automáticamente por contar dos URLs o creer una etiqueta. No hay una auditoría externa realizada ni una garantía de veracidad semántica.

.project-intelligence/reports/audit-flags.md se construye desde TODOS los registros acumulados, antes de Writer, e incluye cualquier status si sensible o favorable está activada. También lista por separado los claims antiguos o pendientes sin esta clasificación. Los veredictos anteriores se reevalúan en la siguiente ejecución de document; no se asignan banderas false por defecto. Los documentos existentes se conservan hasta esa revisión. La nueva política también se aplica a changelog. document.sh y chatgpt_document.sh de la raíz delegan ahora en scripts/document.sh, que ejecuta el pipeline actualizado de Antigravity. Sus versiones anteriores se conservaron en .project-intelligence/legacy/.

## Fuentes y procedencia

reports/sources.md reúne todos los claims y estados: origen de la hipótesis, ejecución, fuentes, ubicación, fechas, extractos conservados, hash SHA-256 del extracto y razonamiento del Skeptic. Los nuevos veredictos registran el historial Collector/Skeptic y las publicaciones registran la salida Writer y documentos asociados. La información histórica ausente se señala, sin inventarla. Los documentos generados muestran una referencia por evidencia (claim:E1, E2...) con enlaces externos y ubicación de archivos/commits. audit-flags.md también incluye las fuentes de los claims marcados. Esto permite seguir hipótesis → evidencia → revisión → respuesta; no demuestra por sí solo independencia, veracidad semántica ni custodia pericial.

## Referencias de archivo desplazadas

Collector recibe snapshots actuales con líneas numeradas de los archivos referenciados por los claims. Si un extracto coincide exactamente una sola vez en el archivo pero cambió de posición, la validación actualiza lines y conserva original_lines y location_verified_at. Si el texto cambió, está inventado o aparece en varias ubicaciones, se detiene con archivo y rango específicos. No se sustituye el contenido del extracto por otra evidencia sin revisión.

## Interfaz local

Haz doble clic en Abrir-investigacion.cmd en la raíz del proyecto. Abre http://127.0.0.1:8765. Mantén la ventana del servicio abierta mientras trabajas; no requiere usar la terminal de Antigravity. La interfaz permite escribir contexto largo, enlaces y adjuntos, iniciar research seguido de document, revisar fuentes y claims, publicar en Obsidian y generar changelog. Usa la misma autenticación y permisos existentes de Antigravity.

Los materiales se conservan en .project-intelligence/inputs/<id>/ con un brief y un registro de SHA-256. Los TXT/Markdown/CSV/JSON UTF-8 se entregan como texto al investigador. Imágenes y PDF quedan guardados y expresamente marcados como no analizados: esta versión no ofrece visión ni OCR. Añade transcripciones o descripciones para aportar contexto, sin confundirlas con evidencia verificada. No se procesa contenido binario como prueba automáticamente.

La página y sus archivos se sirven localmente. Al iniciar una investigación, el texto se envía a Antigravity y al proveedor de IA, que puede realizar búsquedas externas según el contrato. No es inferencia local sin conexión. Los resultados son acumulativos, no expedientes separados por pregunta. El servidor escucha únicamente en 127.0.0.1 y rechaza acciones sin el token de la sesión. Los logs y la cola Obsidian permanecen en el proyecto si falla una pasada.
