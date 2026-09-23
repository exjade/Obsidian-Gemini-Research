# PDFs locales: guía de uso y prueba Docling

Entrega local del 18 de septiembre de 2026. Pendiente de commit/push por el propietario. Esta entrega implementa lectura de PDFs digitales; no completa todo H2.

## Para empezar al despertar

1. Abre http://127.0.0.1:8767/. Es la instancia actualizada preparada para esta entrega. La anterior en 8765 sigue intacta.
2. Abre la investigación de aprendizaje y entra en **Evidencia y fuentes → Documentos PDF del expediente**. Los dos papers aportados ya están incorporados y preparados.
3. **Abrir PDF** muestra el original. **Leer página** muestra la extracción de esa página física. No confundas página física con la numeración impresa de la revista.
4. En **Registrar revisión del documento**, compara título, autores, DOI y editorial con el documento y registra tu nombre, tipo de publicación y lo que comprobaste. El primer paper es un estudio original; el segundo es una revisión de literatura. No registres una comprobación que no hayas realizado.
5. Ve a **Afirmaciones → Abrir ficha → Aportar nuevas fuentes y reevaluar**. Solicita la reevaluación de una afirmación delimitada. Los documentos del expediente se recuperan automáticamente; subirlos o revisar su identidad no inicia esta evaluación.
6. Consulta **Actividad**, estado de la ejecución y **Revisión crítica**. Si no hay soporte suficiente, el resultado puede seguir inconcluso: no demuestra falsedad.

Tus siete afirmaciones actuales conservan sus veredictos. No se ejecutó una investigación real con Antigravity para cambiarlos durante esta entrega. Las pruebas del pipeline usaron un proveedor simulado y expedientes temporales.

## Incorporar otro documento

Desde el panel PDF elige el archivo, pega su enlace editorial y DOI si los conoces y selecciona el método. El formulario admite hasta 15 MB por archivo. El importador interno admite 50 MB y la conversión está limitada a 300 páginas.

- **Extracción ligera:** pypdf; rápida para documentos con texto. No reconstruye tablas ni entiende semánticamente el contenido.
- **Docling nativo:** alternativa sin los modelos de layout del pipeline estándar. No garantiza tablas ni orden complejo.
- **Docling estructurado:** CPU, sin OCR; intenta reconstruir layout y tablas. Su primera ejecución descarga modelos públicos y necesita internet. No envía el PDF a NotebookLM.

Preparar texto se ejecuta aparte de Antigravity. Si la conversión falla, conserva el error y las versiones anteriores válidas. Repreparar un documento crea otra versión; las citas antiguas siguen apuntando a su extracción original.

## Cómo sabemos de dónde salió una respuesta

La ruta observable es:

`afirmación → documento → SHA-256 → extracción/versiones → página física → fragmento → cita literal → entrada de Collector/Skeptic → veredicto`

El SHA identifica los bytes, no demuestra autenticidad. El cotejo literal comprueba que el pasaje está en la extracción conservada, no que apoye toda la afirmación. Skeptic debe evaluar alcance, contexto y contradicciones. Los fragmentos enviados y entradas exactas del proveedor quedan registrados; son una traza auditable, no el pensamiento interno privado del modelo.

Un PDF cuenta como candidato a fuente primaria únicamente con revisión de identidad registrada en ese expediente, clasificación documental adecuada y justificación del modelo. La revisión humana de identidad nunca cambia por sí sola un claim a VERIFIED. Una revisión de literatura orienta hacia originales; no cuenta como estudio original. DOI coincidente evita contar el mismo paper en PDF y en web como dos corroboraciones.

La independencia completa entre estudios y la revisión humana del apoyo semántico siguen pendientes. Para claims sensibles o favorables se mantiene la exigencia de dos fuentes primarias independientes. Dos direcciones del mismo documento no cumplen esa exigencia.

## Prueba realizada con los dos papers

Se conservaron los originales y se comprobó que sus hashes no cambiaron. Los registros de claims tampoco cambiaron durante el benchmark. Se probaron tres métodos sobre exactamente los mismos archivos, sin OCR ni GPU.

| Documento | Páginas físicas | pypdf | Docling nativo | Docling estructurado |
| --- | ---: | ---: | ---: | ---: |
| Which “working memory” are we talking about? | 15 | 1,45 s / 36 MiB | 36,60 s / 506 MiB | 93,70 s / 1759 MiB |
| Working Memory and Instructional Fit | 24 | 1,51 s / 34 MiB | 19,71 s / 559 MiB | 62,66 s / 1855 MiB |

RAM: pico aproximado del proceso medido con psutil. Tiempo: una ejecución por combinación; cachés, importaciones y descargas influyen. No es un ensayo controlado de rendimiento. Versiones: Docling 2.129.0, pypdf 6.19.0. La instalación del extra ocupa bastante más que el núcleo estándar.

Todos los métodos recuperaron texto en las 39 páginas. Docling estructurado detectó las dos tablas del primer paper y ninguna en el segundo. Se revisaron visualmente páginas iniciales, limitaciones, una página con ambas tablas y pasajes de referencia. Esto no equivale a verificar todas las celdas ni todas las páginas.

Cinco marcadores del primer paper aparecieron en los tres métodos. Cuatro de cinco del segundo coincidieron literalmente: el restante, en la página física 19, aparece partido como `vali-` / `dation` en el original. Se conserva ese límite tipográfico; no se corrigió silenciosamente para aparentar una coincidencia perfecta.

Los pasajes fueron elegidos y revisados por el agente, después de iniciar la extracción. No son ground truth humano independiente ni prueba ciega. Puedes cotejarlos personalmente antes de apoyar conclusiones en ellos.

La tabla de estadísticas en la página física 8 del primer documento conserva, en la extracción estructurada, encabezados y valores inspeccionados. La detección de tablas es una capacidad observada en este archivo, no una garantía general.

Hubo un intento fallido de descarga de modelos por una credencial previa de Hugging Face. El worker ahora desactiva el envío implícito de ese token para descargar modelos públicos, sin modificar credenciales guardadas. El historial del fallo queda conservado.

## Dónde se guarda

- `pdfs/`: los archivos aportados; excluida de Git.
- `.project-intelligence/documents/<sha>/`: original canónico, procedencia, revisiones de identidad y extracciones versionadas con hashes.
- `.project-intelligence/benchmarks/docling-cpu/`: mediciones y cotejos de la prueba, privados.
- Expediente local: `documentos.md` y copia del PDF en `adjuntos/`.
- Obsidian: el expediente recibe su nota de documentos y adjuntos; las notas personales se conservan aparte.
- Logs de la evaluación: manifiesto de recuperación, entradas y salidas exactas del proveedor. No se publica automáticamente nada en internet.

Las importaciones y revisiones de identidad se restringen al expediente. Compartir almacenamiento por hash no concede acceso a otro expediente. El servidor exige el token local para descargar originales o leer pasajes.

## Arranque después de apagar el equipo

En PowerShell, desde el repositorio:

```powershell
Set-Location 'Y:\ChatGPT\obsidian-gemini-research\my_docs'
python scripts/frontend.py --port 8767
```

También puedes usar el lanzador habitual, que utiliza 8765, después de cerrar manualmente la instancia antigua. No ejecutes dos investigaciones simultáneas desde servidores distintos. La preparación documental y una evaluación necesitan recursos y pueden tardar.

Para instalar en otra máquina:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-documents.ps1
# Alternativa ligera:
powershell -ExecutionPolicy Bypass -File scripts/install-documents.ps1 -Lite
```

El extra vive en `.venv-documents/`, excluida de Git. Sin él, la biblioteca y funciones básicas siguen disponibles; la preparación PDF explica la dependencia faltante. Usa Python 3.10 o posterior. Los modelos pueden necesitar descargarse antes de una ejecución sin internet.

## Lo que sigue pendiente

OCR y PDFs escaneados/mixtos; integración NotebookLM MCP; búsqueda semántica avanzada; esquema completo fuente/evidencia/relación; identificación automática de todas las copias del mismo documento; revisión humana del respaldo de cada claim y cierre formal del expediente. La extracción actual usa búsqueda léxica inicial y contexto limitado: no garantiza encontrar todos los pasajes relevantes.

No se integró NotebookLM ni se conectó una cuenta nueva. Su futura función será localizar pasajes; una respuesta del servicio deberá cotejarse contra el documento local antes de contar como evidencia.

Referencias de implementación: [opciones oficiales de Docling](https://docling-project.github.io/docling/reference/pipeline_options/), [configuración avanzada](https://docling-project.github.io/docling/usage/advanced_options/). Las mediciones anteriores son observaciones locales de esta entrega.


## Mejora de interfaz: controles y siguientes pasos

Los paneles y cada documento muestran controles Abrir/Cerrar. El aviso verde de texto disponible es un estado informativo; la acción de consulta es Leer página. La revisión del documento tiene campos completos y ayudas. Los detalles técnicos y la repreparación quedan desplegables. El botón Iniciar reevaluación con Antigravity es la acción que ejecuta la IA; incorporar un PDF o guardar su revisión no la inicia. Las 15 y 24 páginas corresponden a los PDFs ya incorporados por el agente a partir de los archivos aportados, no a un libro nuevo. El límite vigente es 300 páginas; procesamiento automático de libros mayores por partes sigue pendiente.
