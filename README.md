# Obsidian Gemini Research

Biblioteca local de investigaciones con Antigravity CLI, verificación por afirmación y publicación en un vault independiente de Obsidian.

La interfaz permite plantear preguntas largas, aportar enlaces y adjuntos, buscar expedientes, consultar evidencia y guardar notas personales. Cada investigación conserva sus propios resultados y fuentes. El flujo propone hipótesis, recopila evidencia, intenta refutarla y publica solo claims VERIFIED.

## Empezar

Requiere Python 3.10 o posterior. Antigravity CLI autenticado e Internet son necesarios para investigar. Git permite versionar el código y producir changelogs. Node.js/npm solo son necesarios para la conexión opcional MCPVault.

```powershell
python scripts/setup.py
python scripts/frontend.py
```

En Windows también puedes hacer doble clic en **Abrir-investigacion.cmd**. Abre http://127.0.0.1:8765. Mantén la ventana del servicio abierta mientras trabajas; no necesitas abrir la terminal interactiva de Antigravity.

Para configurar Obsidian, usa tu propia ruta:

```powershell
python scripts/setup.py --vault 'C:\ruta\a\un-vault-independiente'
```

## Documentación

- [Guía completa: instalación, uso, servidor, datos y recuperación](guides/GUIA-COMPLETA.md)
- [Preparar y publicar en GitHub](guides/GITHUB.md)
- [Arquitectura técnica y límites del sistema](guides/ARQUITECTURA.md)
- [Contrato de investigación](GEMINI.md)
- [Referencia de los scripts](scripts/README.md)
- [Validación sin consumir IA](tests/README.md)
- [Roadmap por hitos](ROADMAP.md)
- [Control manual de cambios](guides/CONTROL-DE-CAMBIOS.md)
- [Changelog del programa](CHANGELOG.md)

## Datos y privacidad

Los expedientes, adjuntos, evidencias, logs, estado y configuración de tu computadora se generan localmente en `.project-intelligence/` y se excluyen de Git. La documentación generada también se excluye. Un clon contiene el programa y las guías, no tu biblioteca personal.

La interfaz escucha únicamente en 127.0.0.1. Los datos usados en una investigación se envían a Antigravity y a su proveedor de IA: no es inferencia local sin Internet. No expongas este servidor directamente como una web pública.

## Límites actuales

- VERIFIED es un veredicto del flujo sobre la evidencia registrada; no garantiza verdad absoluta, custodia pericial ni revisión humana.
- El carácter primario/oficial, independencia y apoyo semántico de las fuentes requieren revisión.
- Imágenes y PDF se conservan, pero todavía no se interpretan automáticamente.
- Solo se ejecuta una investigación a la vez. La biblioteca admite búsqueda y paginación.
- La publicación en Obsidian usa copia local verificada; MCPVault permite leer el vault. No hay servidor remoto de homelab implementado.
- Las etiquetas se gestionan desde el frontend; los índices y resúmenes generados se reconstruyen. Las notas personales no se sobrescriben.

## Licencia

Todavía no se ha elegido una licencia de distribución. Antes de permitir reutilización pública del código, el propietario debe elegir y añadir LICENSE; no se presupone una licencia abierta.

## Lista de trabajo

[Pendientes por prioridad](PENDIENTES.md), complementados por los criterios de aceptación del [roadmap](ROADMAP.md).

[Cómo se comprueban fuentes y qué significa VERIFIED](guides/VERIFICACION-DE-FUENTES.md).

[Reevaluar una afirmación](guides/REEVALUACION.md) · [Investigar externamente en ChatGPT](guides/INVESTIGAR-EN-CHATGPT.md).

[Investigación automática por agentes](guides/INVESTIGACION-AUTOMATICA-POR-AGENTES.md): diferencia la comprobación técnica de la búsqueda automática, explica las tres rondas y el cierre con límites.


Consulta [Estados y recorrido comprobable](guides/ESTADOS-Y-RECORRIDO.md) para distinguir ejecución, veredicto, pendientes y vistas vacías.


## Guía y actividad de investigación

Barra de etapas documentadas (separada de certeza), guía de lectura, Actividad reconstruida de registros con enlaces, referencias numeradas con fondos distintos y explicaciones sin banderas de programación en la vista principal. Nuevos ángulos preparan preguntas para investigaciones independientes; no son hallazgos de IA ya ejecutada. [Cómo entender una investigación](guides/COMO-ENTENDER-UNA-INVESTIGACION.md).


## PDFs digitales opcionales

La interfaz puede conservar originales, preparar texto por página y vincular pasajes comprobables a una reevaluación. Instala el extra con `powershell -ExecutionPolicy Bypass -File scripts/install-documents.ps1`; `-Lite` instala sólo la extracción ligera. Docling usa CPU y modelos descargados en su primera ejecución. La preparación del documento no verifica afirmaciones. [Guía de PDFs y prueba Docling](guides/ENTREGA-PDF-Y-DOCLING.md). OCR y NotebookLM siguen pendientes.


## Aprobar qué se investigará

Los nuevos expedientes preparan una propuesta y revisión de hipótesis antes de buscar evidencia. En Pregunta y alcance selecciona una a tres, aprueba y después inicia la investigación. Los expedientes anteriores necesitan revisión explícita del alcance para reevaluar. [Guía de alcance y siguientes features](guides/ALCANCE-Y-NUEVAS-FEATURES.md).

Guía del control de consolidación e informes provisionales: [Cierre científico](guides/CIERRE-CIENTIFICO.md). La barra de etapas registradas no equivale a cierre.

Guía: [Ampliar el alcance sin reiniciar](guides/AMPLIAR-ALCANCE.md). Tres hipótesis nuevas por lote; historial y evidencia conservados.

Guía: [Eliminar investigación y empezar desde cero](guides/ELIMINAR-INVESTIGACION.md). La eliminación conserva una copia recuperable; restauración desde la interfaz todavía pendiente.
