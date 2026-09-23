# Contexto permanente del proyecto

Este archivo se carga en cada sesión de Gemini CLI para este proyecto.
Define cómo debes investigar, documentar y registrar cambios.

## Principio general

Tu memoria de entrenamiento NO es una fuente confiable para afirmaciones
sobre este proyecto, sus dependencias, APIs externas o su historial de
cambios. La única fuente de verdad es:

1. El propio repositorio (código, git log, git diff).
2. Documentación oficial verificada con google_web_search + web_fetch.
3. Los archivos en .project-intelligence/ (claims y evidence acumulados).

Nunca escribas una afirmación factual en docs/ sin evidencia verificable.
Si no puedes verificar algo, escríbelo explícitamente como "no verificado"
y no lo agregues como hecho consolidado.

## Verificación externa obligatoria

Para cualquier afirmación sobre APIs, versiones, librerías, comportamiento
externo o documentación de terceros:

1. No respondas desde memoria si puedes verificarlo.
2. Usa google_web_search.
3. Prioriza documentación oficial sobre blogs/foros.
4. Abre las fuentes relevantes con web_fetch antes de citarlas.
5. Si dos fuentes discrepan, indícalo explícitamente en el claim.
6. No hay excepciones por "es obvio" o "lo sé de memoria".

## Sistema de claims + evidence

Cada afirmación relevante (sobre arquitectura, dependencias o cambios) se
registra como un objeto claim con esta forma:

{
"claim": "texto de la afirmación",
"evidence": [
{ "type": "commit", "ref": "sha" },
{ "type": "file", "path": "src/...", "lines": "42-91" },
{ "type": "external", "url": "https://..." }
],
"status": "UNVERIFIED"
}

## Flujo de 4 pasadas (multi-pass)

No generes documentación en una sola pasada. Sigue este orden estricto:

PASS 1 — Investigator
Explora el código/repositorio y produce candidatos a claim en
.project-intelligence/claims/. Aún sin evidencia formal, solo hipótesis.

PASS 2 — Evidence collector
Para cada claim, busca evidencia concreta (commit, archivo+línea, PR,
issue, o fuente externa verificada con web_fetch) y la adjunta en
.project-intelligence/evidence/.

PASS 3 — Skeptic
Recibe ÚNICAMENTE claim + evidence (sin el razonamiento previo) e intenta
refutar cada claim. Clasifica cada uno como:
VERIFIED | PARTIAL | UNSUPPORTED | CONTRADICTED
Actualiza el campo "status" en el claim correspondiente.

## Discriminador de sesgo favorable (extensión de PASS 3 — Skeptic)

Antes de asignar status, evalúa cada claim con este árbol de decisión:

1. ¿Hay evidencia primaria (commit/archivo para claims internos, o una
   fuente oficial abierta con web_fetch para claims externos)?
   - No → status: UNSUPPORTED. Detente aquí.

2. ¿El dominio del claim es legal, médico, fiscal, migratorio o de
   seguridad? → SENSIBLE = true
   ¿El claim reduce una obligación, riesgo, costo o responsabilidad del
   usuario, o confirma algo que el usuario parece querer oír?
   → FAVORABLE = true

   Si SENSIBLE == true O FAVORABLE == true:
     - Requiere evidencia de AL MENOS 2 fuentes primarias independientes
       que concuerden entre sí.
     - Para dominio legal: las fuentes deben ser el texto de la ley,
       reglamento o jurisprudencia oficial — nunca un resumen de
       terceros, por confiable que parezca la fuente secundaria.
     - Si solo hay 1 fuente primaria (aunque sea oficial): status máximo
       posible = PARTIAL, nunca VERIFIED.
   Si no:
     - 1 fuente primaria de jerarquía adecuada es suficiente para
       VERIFIED, siempre que no haya evidencia contradictoria.

3. Busca activamente evidencia CONTRADICTORIA, incluso si ya tienes
   fuentes que apoyan el claim. Esto es obligatorio siempre, pero es
   especialmente crítico cuando SENSIBLE o FAVORABLE son true: un modelo
   que quiere complacerte tiende a dejar de buscar en cuanto encuentra
   algo que confirma lo que esperabas.
   - Si encuentras contradicción → status: CONTRADICTED.

4. Asigna status final y registra en skeptic_note por qué (incluye
   explícitamente si SENSIBLE o FAVORABLE se activaron, para que quede
   trazable en el reporte).

Registra domain, sensible y favorable como metadatos para TODOS los claims,
incluso si el paso 1 termina en UNSUPPORTED; no omitas su clasificación de
riesgo por falta de evidencia. La búsqueda contradictoria se registra con
sus limitaciones. Una contradicción fundamentada conserva CONTRADICTED.
El wrapper genera reports/audit-flags.md desde los registros, sin filtrar
por status y antes de Writer, incluso si Writer falla. Los registros
antiguos sin banderas quedan pendientes de revisión; no equivalen a false.
La independencia exige orígenes documentales distintos, no dos URLs,
copias o resúmenes de una misma fuente. Esta clasificación no sustituye
una auditoría cruzada externa.

PASS 4 — Writer
Solo puede usar claims con status VERIFIED (opcionalmente PARTIAL, marcado
como tal) para escribir o actualizar docs/. Nunca usa UNSUPPORTED ni
CONTRADICTED como hechos.

## Criterio de finalización de tareas (no te detengas antes)

No des una tarea de documentación/changelog por completada hasta que:

- hayas inspeccionado git diff relevante;
- hayas leído los archivos afectados, no solo sus nombres;
- cada cambio importante tenga al menos una evidencia adjunta;
- toda afirmación sobre herramientas/APIs externas tenga fuente verificada;
- hayas buscado activamente evidencia CONTRADICTORIA antes de marcar algo
  como VERIFIED;
- los claims sin soporte suficiente queden marcados como UNSUPPORTED,
  nunca omitidos silenciosamente.

## Integración con Obsidian (memoria central)

Este proyecto sincroniza docs/ con un vault de Obsidian mediante un
servidor MCP hosteado en un homelab. Ese servidor:

- permite que agentes en distintos dispositivos lean/escriban en el mismo
  contexto (docs/, changelog/, decisions/);
- se actualiza automáticamente al final de cada ejecución de
  document.sh / changelog.sh mediante la skill correspondiente.
  Cuando termines una pasada Writer, deja explícito en el resumen final qué
  archivos de docs/ cambiaron, para que la skill de sincronización con
  Obsidian sepa qué subir.

## Estilo de documentación

### Trazabilidad de investigación y respuestas

Toda respuesta de investigación debe distinguir hipótesis, observación,
inferencia y veredicto. Cita las fuentes concretas que soportan cada hecho,
incluyendo la fuente primaria, fecha de consulta, extracto y ubicación
(URL canónica, archivo+líneas o commit). Explica el nexo entre evidencia y
claim, su alcance, limitaciones y posibles contradicciones. Si una fuente
no se abrió o no se pudo verificar, decláralo sin presentarla como verificada.

Conserva el origen de cada hipótesis, identificador de claim, ejecución,
salidas crudas de cada pasada y cambios de veredicto. El reporte sources.md
reúne estos datos y audit-flags.md debe mostrar las fuentes de los claims
marcados. No reconstruyas metadatos históricos ausentes por suposición.
La falta de refutación no demuestra una teoría: VERIFIED representa soporte
documental dentro del alcance evaluado y puede revisarse con nueva evidencia.
Este registro de investigación no constituye una cadena de custodia pericial.

- docs/architecture.md: descripción viva del sistema, actualizada por
  Writer, sin historial (eso va en changelog/).
- docs/changelog/: un archivo por release o por lote de cambios, con
  fecha, resumen y lista de claims VERIFIED que lo respaldan.
- docs/decisions/: registros tipo ADR (Architecture Decision Record),
  uno por decisión relevante, con contexto, opciones consideradas y
  justificación.

## Comprobación independiente de referencias externas

Los campos searched/fetched y los extractos generados por el modelo son declaraciones que deben corroborarse. El wrapper hace recuperación GET limitada y conserva un registro técnico; no cuenta una referencia externa como apoyo primario si no confirma su contenido y extracto. No inventes IDs ni resultados de comprobación: los produce el wrapper. Un 404 no prueba falsedad ni demuestra que la fuente existiera antes. Una paráfrasis no es una cita textual. Ausencia de prueba o no detección no basta por sí sola para CONTRADICTED; exige evidencia contradictoria directa. Explica límites y separa tu explicación de acciones realmente observadas.

## Evidencia documental local (ruta complementaria de verificación)

Cuando una web no permita recuperar el texto completo, puedes usar una copia PDF aportada al expediente. Conserva la referencia editorial y busca verificar externamente su identidad; no declares que la URL se abrió si fue bloqueada. El wrapper conserva el original, SHA-256, versión de extracción, página física y fragmento. Usa únicamente los identificadores suministrados en local_document_fragments; nunca inventes páginas, IDs o citas.

Registra evidence.type=document con document_id, document_sha256, extraction_id, chunk_id, physical_page y excerpt literal. El wrapper coteja el extracto contra el fragmento conservado. Una coincidencia textual demuestra presencia en esa extracción, no autenticidad, autoridad ni apoyo semántico a toda la afirmación. Skeptic debe revisar el contexto recibido, límites, población, método y contradicciones.

Un PDF sólo cuenta como fuente primaria si tiene revisión de identidad registrada para este expediente, el modelo justifica su primariedad y el tipo documental es adecuado. Una revisión de literatura no es un estudio original; sus referencias pueden orientar la búsqueda de originales. Las normas requieren texto oficial pertinente. No supongas dos fuentes independientes por tener un PDF y otra URL del mismo paper: DOI coincidente cuenta como una identidad documental.

La revisión humana de identidad no verifica claims. La extracción tampoco cambia veredictos; se requiere una reevaluación explícita. Si el pasaje está partido por guiones, es ilegible o no coincide literalmente, conserva el límite y usa otro pasaje comprobable; no rellenes texto desde memoria. OCR y NotebookLM no están implementados en esta entrega.

## Control de alcance de expedientes

Para expedientes de investigación, PASS 1 propone pocas hipótesis útiles y delimitadas. Una revisión separada de pertinencia aplica skills/hypothesis-review/SKILL.md y explica cada candidato. Esa revisión no sustituye Evidence collector ni Skeptic. El usuario aprueba entre una y tres hipótesis antes de buscar evidencia o ejecutar Writer. Investiga exclusivamente las admitidas; conserva las demás y su historial, sin considerarlas resueltas. Cambios de pregunta o formulación requieren nueva revisión y aprobación. No interpretes aprobación de alcance como respaldo factual. Los expedientes históricos requieren revisión explícita de alcance antes de reevaluar; no los reclasifiques silenciosamente.

## Control de consolidación por expediente

Antes de Writer, todas las hipótesis admitidas deben pasar el control closure-v1. Falta de apoyo, restricciones y errores no resuelven una hipótesis ni demuestran refutación. Una refutación requiere pasaje de contradicción explícito comprobado. Ante pendientes, conservar revisiones y emitir informe provisional con responsables y acciones. No inferir indeterminación justificada de un error de recuperación; su protocolo sigue pendiente. El control no sustituye auditoría semántica ni garantiza verdad absoluta.

## Ampliación del alcance

En scope-v2, el máximo de tres se aplica a hipótesis nuevas por lote. Mantener las admitidas y sus veredictos/evidencias. Revisar sólo candidatos adicionales, exigir aprobación explícita y registrar motivos. Proponer no verifica; retirar, invalidar o reformular necesita un protocolo independiente. Una ampliación sin decidir bloquea consolidación, no borra revisiones anteriores.
