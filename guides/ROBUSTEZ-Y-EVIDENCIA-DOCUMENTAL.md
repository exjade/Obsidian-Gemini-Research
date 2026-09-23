# Recuperación de investigaciones y siguiente etapa documental

## Qué ocurrió en el expediente de aprendizaje

El registro local del expediente `2026-09-18-que-metodo-de-aprendizaje-funciona-mejor-para-72582ae4` indica ejecución terminada, siete afirmaciones UNSUPPORTED y un informe generado sin hechos consolidados. No significa que siete afirmaciones hayan sido refutadas. Tampoco autoriza conclusiones sobre el perfil cognitivo del usuario.

El código tenía un límite de 360 segundos. El propietario lo aumentó a 900 y consiguió terminar. Se conserva ese valor: ahora el límite y el diagnóstico comparten una constante para que no se contradigan.

## Cambios implementados

- Collector y Skeptic procesan una afirmación por vez, con registros independientes. El indicador de ejecución incluye su posición dentro del trabajo pendiente.
- Tras cada revisión completa y validada se guardan el veredicto, sus evidencias, procedencia y contadores. Si falla la siguiente afirmación, las anteriores se conservan.
- Reintentar el documento selecciona afirmaciones sin revisión o con política antigua. Las revisiones completadas con la política actual no se repiten. Para revisar de nuevo una ya clasificada, usar su ficha y aportar nuevas fuentes.
- La evidencia anterior de esa misma afirmación se entrega al Collector para volver a comprobarla; no se considera automáticamente vigente ni suficiente.
- Una salida parcial del proveedor se conserva como registro de diagnóstico. No se promueve a evidencia canónica ni se usa como un veredicto.
- Si Collector termina pero Skeptic falla, esa afirmación todavía se reintenta desde Collector. La reutilización de ese punto intermedio sigue pendiente.
- La entrada exacta enviada al proveedor se conserva en archivos privados `.input.json`. Esto permite inspeccionar datos e instrucciones; no expone ni promete pensamiento interno del modelo.
- Un informe local inconcluso cuenta como publicación terminada. Las nuevas publicaciones registran fecha, hash del informe y cantidad de afirmaciones consolidadas, incluso cuando es cero.
- Los mensajes de auditoría indican si cuentan el repositorio completo o un expediente.

El límite de 900 segundos corresponde a cada llamada al proveedor, no a toda la investigación. Procesar por afirmación mejora la recuperación, pero puede aumentar el número de llamadas y el tiempo total. No se garantiza una reducción de cuota.

## Cómo continuar desde la interfaz

1. Si la ejecución falló, abrir Actividad y el detalle del error.
2. Usar Reintentar para completar lo pendiente. El informe anterior permanece hasta que se completa la nueva redacción.
3. Si la ejecución terminó pero una afirmación quedó sin respaldo, abrir su ficha. Reintentar el documento no obliga a reinvestigar ese veredicto.
4. Aportar una fuente accesible o material adicional y solicitar reevaluación de esa afirmación.
5. Distinguir informe generado, sincronización con Obsidian y calidad de la evidencia: son resultados diferentes.

## Próximas prioridades

1. Probar extracción de un PDF digital real, aislada del pipeline, comparando 3–5 pasajes humanos: texto, página física, columnas, tablas, tiempo y memoria.
2. Incorporar identidad documental y versiones. DOI, PubMed, editor y copia local pueden representar un mismo documento; no son corroboraciones independientes por tener URLs distintas.
3. Registrar documento → página → pasaje → afirmación, con extracción opcional y recuperación de fragmentos. OCR después, para documentos que lo necesiten.
4. Separar afirmaciones compuestas y distinguir respaldo parcial de contradicción directa.
5. Añadir revisión humana registrada y cierre concluyente/inconcluso del expediente.
6. Evaluar NotebookLM MCP como recuperación opcional, cotejando sus citas contra la copia local. No convertir sus respuestas en autoridad final.

No se ha instalado ni evaluado Docling con un PDF real. No se ha conectado NotebookLM. El diseño está en `docs/decisions/0001-evidencia-documental-local.md`.

## Validación de esta entrega

Pruebas sintéticas de fallo en la segunda afirmación y recuperación de la primera, error de tiempo con salida parcial conservada, revisiones selectivas, publicación inconclusa y flujo de cuatro pasadas/changelog. No se ejecutó de nuevo la investigación real ni se gastó cuota de Antigravity para estas pruebas.
