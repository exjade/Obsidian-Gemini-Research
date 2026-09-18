# Changelog del programa

Registra cambios del código y documentación del producto. Es distinto de docs/changelog/, que contiene resultados privados del pipeline sobre commits. Las publicaciones y push a GitHub los realiza manualmente el propietario.

## Baseline local — pendiente de primer commit y release

### Implementado

- Interfaz local y biblioteca con búsqueda, filtros, etiquetas y paginación.
- Expedientes separados con pregunta, resultados, fuentes, auditoría, claims y adjuntos.
- Cuatro pasadas independientes mediante Antigravity headless y transporte NDJSON.
- Publicación exclusiva de VERIFIED y controles estructurales de dominios sensibles/favorabilidad.
- Procedencia por claim, extractos y referencias Collector/Skeptic/Writer.
- Publicación local verificada en vault independiente, índices y notas personales protegidas.
- Lectura opcional del vault mediante MCPVault configurado externamente.
- Inicialización portable de datos faltantes sin reset; lanzador Windows Python/py.
- Wrappers raíz actualizados para delegar al pipeline activo.
- Exclusiones Git de datos, adjuntos, evidencias, configuración local y documentación generada.
- Guías de instalación, servidor, recuperación, arquitectura y GitHub.
- Pruebas simuladas de pipeline y biblioteca, con cien expedientes temporales.

### Validación observada

Las dos suites pasaron en una copia limpia formada por los archivos del índice Git; setup fue idempotente y la API devolvió una biblioteca vacía. No se ejecutó una investigación real para probar el clon limpio. Las simulaciones no demuestran veracidad semántica del modelo.

### Pendiente

No hay primer commit, remoto, tag o release del baseline creados. No hay OCR/visión, comprobación HTTP independiente de fuentes, URLs persistentes de navegación, trazabilidad de herramientas en vivo, score de evidencia, LAN autenticada o Studio implementados. Consulta ROADMAP.md.
