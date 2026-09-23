# Bloqueos, accesibilidad y reutilización — entrega local

## Cómo continuar
En Resumen, «Qué falta para concluir» explica el bloqueo, por qué importa, quién lo resuelve y cómo continuar. Abre «Qué hará el sistema al reevaluar» para ver el plan disponible. Un plan no significa que esos intentos ya se hayan ejecutado. El sistema consulta PDFs del expediente, busca candidatos locales de otros expedientes, revisa su pertinencia y comprueba páginas seleccionadas. La búsqueda automática de versiones alternativas de una URL bloqueada todavía está pendiente.

Puedes iniciar reevaluación con los materiales disponibles, sin aportar nuevas fuentes. No tienes que auditar papers para probar esta entrega. La decisión de incluir o descartar hipótesis sigue siendo tuya; aprobar alcance no comprueba sus afirmaciones.

## Accesibilidad
Hay foco visible, enlace para saltar al contenido con teclado y foco en el título al cambiar de vista mediante controles. Las secciones plegables conservan activación por teclado. En pantallas estrechas, acciones y etapas pasan a una columna, los textos largos se ajustan y desaparece el desplazamiento interno del informe. Se respeta la preferencia de movimiento reducido. Se conservan comprobar fuentes, reevaluar, auditoría y detalle avanzado.

Se comprobaron salto al título, apertura del plan con Enter y ausencia de desbordamiento horizontal a 390 px. Esto no constituye una auditoría completa de accesibilidad ni pruebas en un teléfono físico o lector de pantalla. Acceso remoto al móvil no se habilitó.

## Reutilización entre expedientes
La primera entrega propone hasta seis pasajes web, leyendo sólo claims y evidencia estructurada de otros expedientes: hasta 200 carpetas, 100 afirmaciones por carpeta y 30 referencias por afirmación. Se excluyen notas personales, el expediente actual, PDFs no asociados y archivos corruptos. El buscador usa coincidencias léxicas normalizadas; todavía no hay embeddings ni búsqueda multilingüe semántica.

Los candidatos no transfieren veredictos, primariedad ni independencia. Collector puede descartarlos todos. Si selecciona exactamente una URL y su pasaje, el programa conserva expediente, afirmación e índice de evidencia de origen. Skeptic debe registrar una revisión de pertinencia para la afirmación de destino: apoyo, contradicción, contexto o no pertinente, motivo y límites. Falta de revisión válida detiene la pasada; un pasaje no pertinente se cuenta como contexto, nunca como apoyo. Las páginas vuelven a comprobarse con el mismo filtro técnico. La revisión semántica registrada sigue siendo una evaluación del modelo, no una garantía de que sea correcta.

El manifiesto de candidatos y la entrada real del proveedor quedan conservados. La nueva evidencia muestra origen reutilizado y revisión registrada. Ningún resultado previo se modifica por encontrar candidatos. Una reevaluación posterior puede cambiar un nuevo veredicto según su propia evidencia. Los PDFs compartidos, pertinencia supervisada independiente y catálogo definitivo de relaciones siguen pendientes.

## Comparar flujos sin inventar resultados
scripts/workflow_compare.py compara dos registros JSON con la misma pregunta y textos de hipótesis admitidas. Mide revisiones críticas registradas, afirmaciones con pasajes, veredictos VERIFIED, llamadas, fallos del proveedor y suma de tiempos registrados. Calidad de contenido necesita audited_claims de una revisión independiente. Sin recibos o sin revisión, el dato se informa desconocido, no cero.

Formato mínimo de cada registro (ejemplo ficticio, no investigación ejecutada):
```json
{"question":"Pregunta de prueba","approved_claim_ids":["a"],"claims":[{"id":"a","claim":"Hipótesis de prueba","status":"UNVERIFIED","evidence":[]}],"receipts":null,"audited_claims":null}
```
Receipts, cuando existen, contienen run_id, stage, status y elapsed_seconds de los archivos reales de ejecución. Audited_claims, cuando existe revisión independiente, contiene id y decision (correct, error o uncertain). No rellenar estos datos con suposiciones. Para ejecutar sobre archivos preparados en la copia aislada:
```
python scripts/workflow_compare.py --baseline anterior.json --specialized especializado.json --output comparacion.json
```
La herramienta no llama a la IA. La comparación científica real está pendiente: controlar documentos, proveedor, condiciones y presupuesto, y revisar resultados independientemente. Cantidad de pasajes, estados VERIFIED y llamadas no equivale a calidad ni demuestra superioridad de agentes especializados.
