# Primera prueba de PDFs locales — 2026-09-18

## Resultado

Los dos archivos aportados en `Y:\ChatGPT\obsidian-gemini-research\my_docs\pdfs` tienen capa de texto. La primera extracción paginada pudo realizarse sin OCR, con pypdf 6.10.0 disponible en el entorno de Codex. No se instaló Docling ni NotebookLM y no se ejecutó Antigravity.

| Documento | Páginas físicas | Páginas con texto | Extracción de texto |
| --- | ---: | ---: | ---: |
| Which working memory… Complex span versus N-back | 15 | 15 | 0,843 s |
| Working Memory and Instructional Fit… | 24 | 24 | 1,028 s |

Los tiempos son una ejecución inicial, incluyendo apertura y extracción, no renderizado ni benchmark estadístico. RAM máxima no medida. Recuperar texto en todas las páginas no certifica fidelidad completa, tablas ni orden de lectura.

## Identidad conservada

Primer archivo: 1.531.139 bytes; DOI impreso `10.3758/s13423-024-02622-0`.

SHA-256: `5e0a5eae6dfacc01c807084a561137d800a6c761f05f1e0c645ed83df8544849`.

Segundo archivo: 332.614 bytes; DOI impreso `10.3390/bs15060765`.

SHA-256: `7f2bc5deba7000d396d1eb14ec5c6dd6f1b4830640a38af85c1ebe7770fd0aa2`.

Se verificó que los originales no cambiaron durante la extracción. Se conservaron copias byte-identical, manifiestos y texto por página en `.project-intelligence/benchmarks/pdf-native-baseline/<sha256>/`, dentro del repositorio operativo. Son artefactos privados de prueba, no evidencia canónica registrada en claims.

## Revisión visual y referencias de prueba

Se renderizaron y revisaron las primeras dos páginas de ambos PDFs. El primer paper combina un resumen a ancho completo con cuerpo a dos columnas. El segundo tiene cuerpo principal y datos editoriales laterales. Estos layouts requieren comprobar el orden de lectura, además de presencia de palabras.

Se prepararon cuatro marcadores breves por documento, asociados a página física y hash del texto de esa página, en `passages.json`. Son referencias elegidas mediante revisión visual del agente después de la extracción inicial: no son ground truth humano ni una prueba ciega. Deben complementarse con pasajes internos, tablas y revisión humana antes de aprobar un extractor.

## Qué significa para la investigación

El bloqueo de PubMed no impide leer estas copias locales. Todavía falta que la aplicación las importe al expediente y permita al Collector/Skeptic recuperar y citar sus pasajes.

El segundo documento se identifica como Review en su primera página: debe distinguirse una revisión de los estudios originales que cita. Un documento serio y un hash válido no prueban por sí solos una afirmación amplia.

No se modificaron los veredictos de la investigación. Los PDFs no están todavía integrados en las fichas ni han eliminado sus avisos históricos de acceso restringido. Se añadió `/pdfs/` a las exclusiones Git para evitar publicar los documentos originales accidentalmente.

## Siguiente prueba

1. Elegir 3–5 pasajes humanos, incluyendo resultados/limitaciones internos y una tabla si corresponde.
2. Comparar Docling CPU nativo y estándar sin OCR con esta extracción base: páginas, orden, fidelidad, tablas, tiempo y RAM.
3. Integrar un importador opcional con identidad documental y fragmentos paginados; después reevaluar claims contra esos fragmentos.

NotebookLM MCP puede evaluarse posteriormente como recuperación opcional, sin reemplazar el cotejo local. Ninguna conclusión de esta prueba autoriza marcar automáticamente claims VERIFIED.
# Nota de continuidad — 2026-09-18

Este informe conserva el baseline inicial. Las menciones a Docling no instalado o integración pendiente describen aquella prueba, no el estado actual. La implementación y el benchmark posteriores están en [Entrega PDF y Docling](ENTREGA-PDF-Y-DOCLING.md).
