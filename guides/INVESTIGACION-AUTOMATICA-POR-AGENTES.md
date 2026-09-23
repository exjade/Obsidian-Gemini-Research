# Investigación automática por agentes

La ficha de una afirmación separa dos acciones:

- **Volver a comprobar esta página** repite la descarga limitada y busca el pasaje literal. No busca estudios, no evalúa pertinencia y no cambia el veredicto.
- **Buscar respaldo y reevaluar automáticamente** inicia un protocolo de hasta tres rondas: evidencia primaria, recuperación alternativa y huecos/contradicciones.

El protocolo usa agentes con contratos separados para planificar, revisar la formulación, localizar, recuperar, evaluar la fuente, evaluar pertinencia, buscar contradicciones, redactar y auditar. El programa valida cada salida JSON y conserva manifiestos, resultados, matrices y recibos. Los agentes no se invocan entre sí.

## Límites

Cada afirmación dispone como máximo de 16 consultas nuevas, 24 páginas únicas y 30 minutos. Cada ronda tiene su propio límite. Consultas equivalentes, DOI, URLs, fuentes y contenido ya vistos se reutilizan sin volver a consumir el presupuesto lógico. Si el proceso propio excede el límite, se detiene y la salida parcial no se convierte en evidencia.

Si no se resuelve después de tres rondas, el claim conserva su veredicto histórico y recibe `excluded_with_limit`. El expediente puede pasar a **Completado con límites**, pero debe mostrar qué parte no pudo responderse y por qué. Las subpreguntas nunca verifican automáticamente el claim padre.

## Trazabilidad

La interfaz muestra el total real de acciones antes del recorte, las acciones visibles, las omitidas y las consultas agrupadas. Las rutas y el JSON permanecen en el detalle técnico. La descarga de auditoría contiene la lista observable completa; no contiene pensamiento interno.

El lanzador usa el puerto 8770 como instancia autoritativa. `/api/version` y `/api/status` exponen esquema, build, PID y puerto. Si la página y el backend no comparten esquema, las acciones se bloquean y se pide volver a abrir el lanzador.

No se ejecutó el nuevo protocolo sobre expedientes reales durante esta entrega. Las pruebas usan proveedores y datos sintéticos.
