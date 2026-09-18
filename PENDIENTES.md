# Pendientes del proyecto

Repositorio oficial: https://github.com/exjade/Obsidian-Gemini-Research

Esta lista describe trabajo por hacer, no funciones ya disponibles. La publicación de cada entrega es manual por el propietario. H1 está implementado localmente; no se presupone que todos sus ajustes posteriores estén publicados.

## Prioridad 1 — Poder revisar una investigación sin conocimientos técnicos

- [x] H1.1: guía dentro del frontend: qué investigar, qué revisar y qué hacer después.
- [x] Ficha individual con evidencia, motivo registrado y siguientes acciones; mejorar aún la explicación automática de motivos.
- [x] Mostrar por afirmación huecos de recuperación comprobados, separados del motivo del modelo. Pendiente: evaluación semántica y revisión humana del apoyo completo.
- [x] Incorporar enlaces/texto de apoyo a una afirmación del mismo expediente con historial de solicitudes.
- [x] Solicitar nueva búsqueda/revisión de una afirmación ya clasificada desde su ficha. El botón general Reintentar conserva su comportamiento para etapas pendientes/Writer.
- [ ] Separar revisión humana del veredicto automático y registrar quién revisó, cuándo, respaldo y límites. No permitir convertir una intuición en VERIFIED.

## Prioridad 2 — H2: fuentes comprobables y correcciones de verificación

- [x] Comprobar URL original/final, estado HTTP, fecha, restricciones y contenido conservado (GET limitado; HTML/texto).
- [x] Mostrar accesible, caída, restringida o pendiente sin convertir accesibilidad en verdad.
- [ ] Conservar extractos/snapshots con origen y fecha; revisar que apoyen exactamente la afirmación.
- [ ] Fuentes y relaciones con IDs estables: apoyo, contradicción, contexto, sin revisar.
- [ ] Revisar primariedad e independencia; dos páginas del mismo origen no son dos corroboraciones independientes.
- [ ] Separar afirmaciones compuestas para no verificar varias conclusiones con una evidencia parcial.
- [ ] Distinguir UNSUPPORTED de CONTRADICTED: ausencia de prueba o falta de detección no equivale por sí sola a refutación.
- [ ] Revisar la política legal: distinguir normas de hechos procesales. Para hechos, considerar documentos judiciales oficiales pertinentes (acusación, resolución, expediente, transcripción), sin admitir resúmenes como texto normativo.
- [ ] Revisar detección de dominios sensibles: una imputación de corrupción no debe depender únicamente de que el modelo se autodetecte como sensible.
- [ ] Backup, migración y reevaluación explícita de expedientes antiguos; nunca cambiar estados silenciosamente.

## Prioridad 3 — H3–H4: trazabilidad y método

- [ ] H3: plan, acciones realmente observadas, herramientas, destinos, resultados/errores y tiempos persistentes.
- [ ] Explicación del veredicto enlazada con evidencia a favor/en contra y regla aplicada.
- [ ] Distinguir explicación del modelo de acción comprobada; resúmenes del proveedor si se exponen, sin prometer pensamiento interno completo.
- [ ] H4: pregunta, subpreguntas, hipótesis competidoras, criterios de refutación, cronología y límites.
- [ ] Rúbrica explicable de fuerza de evidencia; sin inventar probabilidad de verdad ni anular contradicciones con un puntaje.

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
- [ ] Interpretación de imágenes/PDF: hoy se guardan, no se analizan automáticamente. Definir alcance y privacidad antes de incorporarla.
- [ ] Homelab/remoto: no está implementado; la copia local a Obsidian y MCP de lectura son mecanismos diferentes.

Ver ROADMAP.md para criterios de aceptación y dependencias. Próximo bloque recomendado: revisión humana registrada y relaciones fuente/evidencia de H2, antes de Studio.


## Claridad de estados y revisión

Implementado: aviso visible de ejecución y reevaluación, señales de error y pendientes, auditoría estructurada, aclaración de vistas vacías, recorrido de herramientas conservado y avisos nativos en Obsidian. Pendiente: transmisión de herramientas en vivo y atribución exclusiva de acciones a cada afirmación en lotes. Guía: [Estados y recorrido](guides/ESTADOS-Y-RECORRIDO.md).


## Guía y actividad de investigación

Barra de etapas documentadas (separada de certeza), guía de lectura, Actividad reconstruida de registros con enlaces, referencias numeradas con fondos distintos y explicaciones sin banderas de programación en la vista principal. Nuevos ángulos preparan preguntas para investigaciones independientes; no son hallazgos de IA ya ejecutada. [Cómo entender una investigación](guides/COMO-ENTENDER-UNA-INVESTIGACION.md).
