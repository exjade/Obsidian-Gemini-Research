# Revisar, recuperar y continuar una investigación

## Reintentar sin repetir una búsqueda completa
Cuando Collector finaliza, el programa valida su respuesta y conserva un checkpoint antes de llamar a Skeptic. Si Skeptic falla, Reintentar puede reutilizar esa recopilación: vuelve a ejecutar la revisión crítica y a comprobar las fuentes externas. El checkpoint no es un veredicto ni una fuente ya confirmada.

Sólo sirve durante seis horas, para las mismas entradas, alcance, contratos, política y documentos. Si cambia un archivo utilizado, una extracción, revisión de identidad o material, se vuelve a recopilar. El registro explica qué se reutilizó y conserva las rutas del Collector original. Un fallo de Collector, salida parcial o archivo .raw.json antiguo no se importa automáticamente.

Reevaluar explícitamente una ficha crea otra solicitud; sus nuevos datos invalidan la reutilización anterior. El timeout sigue siendo 900 segundos por llamada, no por expediente completo. El checkpoint reduce repeticiones; no garantiza una duración máxima de toda la investigación.

## Leer el progreso
«Pendiente 1 de 2» describe esta ejecución; «alcance: 3» describe las hipótesis admitidas; «evaluaciones anteriores conservadas: 1» explica lo que no se repite. Tener un veredicto registrado no significa estar científicamente resuelto. La pantalla conserva la distinción y explica cómo recuperar un timeout o una revisión no validada.

## PDFs
La recuperación léxica no envía pasajes con cero coincidencias. Esto evita incorporar texto arbitrario; no prueba relevancia semántica. Un PDF cotejado puede ser respaldo sin otra URL accesible, pero sigue necesitando las verificaciones de identidad, primariedad, independencia y política aplicables. No se rebajó el umbral de VERIFIED.

## Registrar mi revisión (opcional)
Abre una ficha individual y «Registrar mi revisión · opcional». Indica quién revisó, marca las fuentes realmente examinadas, selecciona tu observación y escribe qué comprobaste y qué dudas quedan. Guarda.

El programa conserva una copia exacta de la evidencia examinada y el veredicto vigente. Si cambian después, la observación se muestra como histórica. El nombre del revisor es una declaración del usuario, no una identidad autenticada. Tus observaciones nunca cambian automáticamente un veredicto ni desbloquean la consolidación. No son un requisito para hacer una pregunta.

Las observaciones se conservan en revisiones-humanas dentro del expediente y su informe en revisiones-humanas.md. Usa Publicar biblioteca en Obsidian para copiar el informe; guardar no sincroniza por sí solo. Las notas personales permanecen separadas.

## Límites que siguen pendientes
Recuperación automática de páginas bloqueadas, auditoría automática de identidad documental, normalización de fuentes/DOI y relaciones, auditor semántico de respuesta y nuevas skills especializadas. La extracción léxica y las observaciones humanas no sustituyen esos controles. No se implementaron OCR ni NotebookLM MCP.
