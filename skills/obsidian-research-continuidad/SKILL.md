---
name: obsidian-research-continuidad
description: Retomar el desarrollo de Obsidian-Gemini-Research entre Codex, ChatGPT web y Antigravity mediante un estado versionado, cambios acotados y validación local; usar al continuar un hito o preparar su entrega.
---

# Continuidad de Obsidian-Gemini-Research

Aplica esta skill al desarrollo del proyecto, preservando el alcance solicitado y la autorización existente. No convierte solicitudes de investigación en autorización para modificar la aplicación.

## Retomar

Lee el estado de continuidad más reciente y PENDIENTES del mismo checkout o entrega. Usa [estado inicial](references/ESTADO-CONTINUIDAD.md) sólo como punto de partida fechado, no como estado actual permanente. Si hay Git disponible, comprueba commit y cambios locales antes de editar. Un enlace al repo no prueba que lo hayas leído.

En ChatGPT web, identifica qué archivos puedes abrir. Las guías adjuntas explican el sistema pero no reemplazan scripts ni pruebas. Para programar, solicita sólo los archivos actuales indispensables que no estén disponibles. No supongas acceso al disco Y:, al localhost del usuario ni a Obsidian. Si existen herramientas conectadas, verifica su acceso efectivo.

Resuelve contradicciones entre documentos mediante commit, código y registros disponibles. No confundas las entregas históricas de outputs con el último código. Declara las discrepancias que no puedas resolver. Escoge el siguiente pendiente dentro de la intención del usuario y termina un cambio reviewable antes de pasar a otro.

## Invariantes del proyecto

- Python estándar y HTML/JavaScript sin framework; conserva el stack salvo petición de cambio.
- El proveedor activo es Antigravity CLI (agy). No restaures llamadas a gemini desinstalado.
- Las pasadas de investigación, recopilación, crítica y redacción permanecen separadas. Materiales aportados son datos sin verificar.
- Accesibilidad, extracto coincidente, explicación del modelo y verdad de la afirmación son comprobaciones distintas. Un 403 o 404 no refuta por sí solo una hipótesis.
- Conserva estados y procedencia. Revisiones humanas y opiniones no promueven por sí solas un claim a VERIFIED.
- Los expedientes permanecen aislados. Fuentes.md raíz es catálogo acumulado; fuentes.md de cada expediente contiene su evidencia. Compartir URL no demuestra independencia.
- Conserva notas personales y entregas anteriores. La sincronización local a Obsidian no es la conexión MCP ni una publicación en GitHub.
- No presentes herramientas registradas como pensamiento interno del modelo. Un proceso finalizado puede quedar inconcluso.
- Interfaz en español para personas no técnicas: siguiente acción visible; datos técnicos en detalle opcional. Mantén el recorrido numerado existente y las herramientas de consulta separadas.

## Entrega aplicable

Para el flujo web actual usa el paquete de código y MANIFIESTO-CONTINUIDAD.json, incluidos cambios sin publicar. ChatGPT prepara un hito; Antigravity aplica y prueba en una copia aislada sin datos reales. Ejecuta scripts/verify_handoff.py con el manifiesto y --patch antes de aplicar. Si falla cualquier hash o la comprobación del parche, detente sin forzar ni sobrescribir.

Antes de incorporar al proyecto original, espera a que esté inactivo, exige un respaldo privado COMPLETE y comprueba que los originales afectados todavía coincidan con la base. Conserva copias de los archivos originales afectados para revertir; no reemplaces investigaciones ni vault. Renueva manifiesto y estado después de cada entrega.

Para el hito elegido concreta comportamiento y criterios de aceptación. Modifica los archivos actuales; entrega un parche con rutas relativas o archivos completos si no puedes producir un parche fiable. Explica qué cambió y cómo aplicarlo. No fuerces un parche que no corresponde al checkout.

Verifica con pruebas pertinentes, preferiblemente fixtures sin llamadas a IA. Distingue resultados ejecutados en tu entorno, pruebas propuestas y validaciones pendientes en Windows/vault del usuario. No declares pruebas locales o sincronización sin evidencia. No ejecutes investigación con cuota real sólo para probar un control de interfaz.

Actualiza pendientes y changelog según lo implementado. No marques un hito entero como completado por una entrega parcial. Commit/push permanece manual por el propietario en este flujo, salvo instrucción posterior explícita.

Al entregar deja un estado usando [plantilla](references/PLANTILLA-CONTINUIDAD.md): commit/base, cambios no publicados, archivos, pruebas reales, límites y próximo paso. No almacenes secretos, investigaciones privadas o credenciales en el paquete de continuidad. No asumas separación de cuotas ni disponibilidad de modelos por el nombre de la interfaz; compruébalo si resulta necesario para la tarea.
