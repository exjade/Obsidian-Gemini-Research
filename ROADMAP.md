# Roadmap por hitos

Plan basado en las observaciones del propietario y el código existente. La propuesta adjunta aporta ideas, no una descripción comprobada de features ya implementadas. Este plan no copia sus estimaciones de calendario, afirmaciones sobre productos comparados, números de tests de ejemplo o reglas incompatibles con el contrato actual.

Nombre actual del repositorio: Obsidian Gemini Research. Visualize es una referencia de experiencia/propuesta, no un cambio de nombre aplicado.

## Baseline confirmado

Stack: Python 3.10+ estándar y HTML/JavaScript sin framework. Datos JSON y Markdown, no base de datos SQL. Servidor loopback, puerto 8765. Proveedor mediante Antigravity CLI; copia local a Obsidian; conexión MCP externa de lectura.

Ya existen expedientes separados, catálogo de URLs, búsqueda/paginación, etiquetas, referencias y extractos por claim, controles de riesgo, notas personales protegidas y pruebas. Faltan navegación persistente, estado investigativo explicativo, comprobación independiente de fuentes, registro de acciones en vivo y artefactos versionados.

## Orden y dependencias

| Hito | Entrega | Dependencia | Estado |
|---|---|---|---|
| H0 | Baseline GitHub y tracking del programa | Ninguna | Preparado localmente; publicación manual pendiente |
| H1 | Flujo claro, diagnósticos y URLs por expediente | H0 publicado | Pendiente |
| H2 | Fuentes comprobables y relaciones claim/evidencia | H1 | Pendiente |
| H3 | Traza de acciones, auditoría y motivos de decisión | H2 | Pendiente |
| H4 | Protocolo de investigación rigurosa e índice explicable | H2–H3 | Pendiente |
| H5 | Experiencia Windows sin consolas auxiliares | H0; coordinar con H3 | Pendiente |
| H6 | Acceso móvil autenticado y optativo | H1 y diseño de acceso | Pendiente |
| H7 | Versiones de investigación y Studio: informe | H2–H4 | Pendiente |
| H8 | Mapa mental y grafo de Obsidian | H7 | Pendiente |
| H9 | Flashcards y cuestionario | H7 | Pendiente |
| H10 | Infografías y visualizaciones | H7–H9 | Pendiente |

Secuencia recomendada: el propietario publica/revisa H0 antes de iniciar cambios funcionales del siguiente hito, para conservar un baseline comparable. H5 puede adelantarse después del baseline si las ventanas afectan el uso diario. H6 no requiere lanzar Studio, pero sí un diseño explícito de autenticación y acceso.

## H0 — Guardar una base revisable

Entregas: README, guías, .gitignore, tests, CHANGELOG, roadmap y manifiesto de archivos del índice con hashes. El usuario elige identidad, licencia, visibilidad y repositorio, hace commit y push manual, y conserva una referencia baseline.

Aceptación: clon limpio abre biblioteca vacía; setup no reemplaza datos existentes; tests pasan; Git no rastrea .project-intelligence ni documentación privada; el usuario puede comparar el índice con el manifiesto. Estado Git inicial sin HEAD no se presenta como commit o release publicado.

## H1 — Entender el proceso y conservar la navegación

Separar ejecución, etapa investigativa, veredicto de cada afirmación y conclusión del expediente. El resumen es un dashboard y la auditoría una vista transversal. Orden visible recomendado: Resumen, Pregunta, Hipótesis, Evidencia/fuentes, Afirmaciones, Revisión crítica, Resultados, Artefactos, Auditoría. Las vistas sin datos deben indicarlo.

Explicar por qué no hay VERIFIED: claims no extraídos, revisión no ejecutada/fallida, fuente primaria ausente, fuentes independientes insuficientes, contradicción o fuente inaccesible. Solo mostrar diagnósticos sustentados por los registros; no inventar motivos a partir de un contador cero. completed significa que la ejecución terminó.

URLs propuestas: `/?investigacion=<id>&vista=fuentes`, con parámetros de filtros/página y deep link de claim. Este esquema conserva el servidor actual y evita una reescritura de framework. Puede evolucionar a rutas si existe una necesidad concreta.

Aceptación: abrir enlace directo, recargar y usar atrás/adelante conserva expediente y vista; ID inválido muestra error claro; una ejecución con cero VERIFIED muestra conclusión inconclusa y motivos registrados; guardar notas no pierde borradores durante polling.

## H2 — Saber si una fuente se puede comprobar

Registrar URL original/final, fecha, método, estado HTTP, restricciones, tipo de contenido y snapshot o extracto real. Consultar contenido mediante GET limitado; HEAD puede ser una optimización y no prueba que el texto esté presente. Evitar URLs de redes internas y aplicar límites también en redirecciones cuando se añada un verificador automático.

404/410 implica fuente actualmente inaccesible; 403/login/timeout no demuestra falsedad. HTTP 200 no demuestra que el contenido respalde el claim. Un hash permite comparar contenido, no medir verdad. Buscar una copia archivada o una fuente primaria alternativa, conservando fechas y diferencias. Un resultado de búsqueda o snippet no sustituye una fuente abierta y verificable.

No asumir que una URL caída procede de una base secreta/caché de Google. Conservar esa explicación como hipótesis no demostrada si se plantea. Separar disponibilidad actual, evidencia histórica conservada y apoyo semántico al claim.

Normalizar fuente/evidencia/relación con identificadores estables y postura: apoyo, contradicción, contexto o sin revisar. Migrar con backup y campos desconocidos explícitos, sin rellenar HTTP 200 o fecha de revisión por defecto. Las fuentes históricas sin snapshot/estado quedan pendientes.

Aceptación: fixtures 200, redirect, 404, 410, restricción, timeout y contenido cambiado; no se verifica un claim solo porque exista una URL; evidencia inaccesible sin contenido comprobable no cuenta automáticamente como fuente primaria de apoyo; dos URLs del mismo documento no se cuentan como corroboración independiente.

## H3 — Ver lo ocurrido y entender el veredicto

Mostrar tres capas separadas: plan investigativo, eventos realmente observados y explicación del veredicto con evidencias a favor/en contra. Registrar pasada, ejecución, timestamps, herramienta, destino, resultado/error, claim asociado y regla aplicada. Guardar el log para recuperarlo después de reiniciar.

El código ya conserva eventos crudos al finalizar llamadas; la UI todavía no ofrece una traza persistente por herramienta en vivo. La integración en streaming requiere adaptar lectura del proceso sin perder timeout, raw output y diagnóstico. No inventar una cronología a partir del texto final.

Los resúmenes de razonamiento que entregue explícitamente el proveedor se mostrarán como tales. No equivalen a la cadena interna completa. Una firma cifrada no es pensamiento legible. La [API de Gemini documenta resúmenes opcionales](https://ai.google.dev/gemini-api/docs/thinking); eso no demuestra que el CLI instalado exponga ese campo. Hay que validar el adaptador usando eventos reales de esa versión.

Aceptación: toda explicación enlaza claims/evidencias/reglas; eventos ausentes se muestran como no registrados; un reinicio permite leer la ejecución anterior; los resúmenes del modelo no se presentan como acciones comprobadas; no se mezcla el razonamiento previo en la entrada de Skeptic.

## H4 — Investigación rigurosa e índice de evidencia

Protocolo con pregunta, subpreguntas, hipótesis competidoras, criterios de refutación, cronología cuando sea pertinente, colección, corroboración, contradicción, revisión y límites. No afirmar validación o afiliación FBI; el rigor procede de procedimientos y datos comprobables.

Índice opcional de fuerza de evidencia con factores visibles: primariedad revisada, independencia, apoyo directo, disponibilidad y actualidad pertinente. Componentes desconocidos quedan desconocidos; los pesos no están fijados ni calibrados. Primero una rúbrica y ejemplos revisados por personas; después un indicador. No mostrar probabilidad de verdad ni permitir que una puntuación alta anule una contradicción.

Mantener la política vigente: una fuente primaria adecuada puede bastar para claims generales; sensibles o favorables requieren dos orígenes independientes. En legal, texto oficial. No imponer dos fuentes a todo claim copiando una métrica contradictoria del informe adjunto.

Aceptación: el índice abre su desglose y procedencia; sin datos no se fabrica una puntuación; el resultado no cambia el veredicto por sí solo; las hipótesis descartadas no se omiten silenciosamente.

## H5 — Windows cómodo y diagnosticable

Identificar qué proceso crea cada consola. El código actual invoca Python/agy sin flags explícitos de ocultación; aún no se verificó visualmente cuál origina cada ventana reportada. Separar lanzador de usuario y modo diagnóstico. Conservar stderr y errores visibles dentro de la app.

Aceptación: arranque normal, investigación, retry y sync no crean consolas auxiliares inesperadas; existe una forma clara de apagar el servicio; se puede consultar el diagnóstico aunque no haya consola. La ocultación no debe impedir autenticar interactivamente cuando sea necesario.

## H6 — Móvil

Ahora loopback solo sirve al propio equipo. No basta con abrir la dirección 127.0.0.1 del PC en el móvil. Añadir acceso optativo con autenticación/pairing, binding y validación Host/Origin apropiados, caducidad de sesión y documentación de red privada. No cambiar simplemente a 0.0.0.0 ni exponer puerto a Internet.

Aceptación: desactivado por defecto; móvil autorizado puede consultar y crear expedientes; cliente no autorizado no obtiene biblioteca/token; notas privadas no son públicas; volver a modo local revoca acceso. El usuario revisa el alcance antes de habilitarlo.

## H7 — Versiones e informes

Snapshot/version_id que identifica claims, evidencias, reglas y fuentes utilizados. Informe derivado solo de claims aptos y con sección separada para límites e incertidumbre. Registrar generador, fecha, prompt/versiones y referencias. Si cambia la base, el artefacto queda desactualizado; no se sobrescribe una edición humana sin revisión.

Aceptación: el informe enlaza su versión y cada afirmación factual; marcar stale al cambiar claims/evidencia; regenerar conserva historial. El generador no añade investigación nueva oculta. Exportaciones Word/PDF son una entrega posterior si se autorizan.

## H8 — Mapas y Obsidian

Generar notas de claims/fuentes/eventos pertinentes y wikilinks con tipo de relación explícito. Separar grafo navegable de mapa mental curado. No convertir proximidad en grafo en causalidad, culpabilidad o corroboración. Proteger notas personales y permitir excluir información sensible.

Aceptación: cada nodo factual enlaza evidencia; las relaciones inferidas están marcadas; el mapa cita su versión; no altera el motor interno de Obsidian.

## H9 — Aprendizaje

Flashcards y cuestionario desde snapshots: pregunta, respuesta y evidencia de respaldo. Mantener apartadas incertidumbres y hechos contradichos; no convertirlos en respuestas correctas. Exportación Markdown/JSON inicial y otros formatos después de revisar su necesidad.

Aceptación: cada respuesta enlaza claim y fuente; no memorizar como hecho un UNSUPPORTED; feedback explica respaldo y límites; una investigación actualizada marca las tarjetas desactualizadas.

## H10 — Infografías y visualizaciones

Primero guion y datos citados; luego diseño y revisión. Diagramas/cronologías no deben inventar cantidades, causalidad o imágenes como prueba. Mantener citas, unidades, incertidumbre y snapshot origen. Imágenes ilustrativas se etiquetan como ilustración.

Aceptación: se puede recorrer visual → dato → claim → evidencia; cifras verificables; revisión previa a exportar; no sustituye una auditoría por una imagen convincente.

## Protocolo de entrega por hito

1. Registrar alcance, archivos previstos, campos/migraciones y criterios de aceptación.
2. Crear rama después del baseline publicado y trabajar solo ese hito.
3. Presentar diff, archivos creados/modificados/eliminados y pruebas realmente ejecutadas.
4. Actualizar CHANGELOG y guías; generar manifiesto con referencia Git y hashes.
5. El propietario revisa y realiza commit/push/release manualmente.
6. Comprobar lo publicado y el arranque limpio antes de comenzar el siguiente hito.

Ningún número de tests, porcentaje, plazo o estado publicado se rellena con datos de los mockups. No hay cronograma comprometido: se estimará cada hito tras revisar su implementación y migración concretas.
