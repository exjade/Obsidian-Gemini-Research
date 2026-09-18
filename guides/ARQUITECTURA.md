# Arquitectura técnica

Descripción del código implementado; distinta de los documentos de investigación generados en docs/.

## Componentes y flujo

```text
Navegador local
   ↓ HTTP 127.0.0.1:8765 + token de sesión
scripts/frontend.py
   ↓ proceso Python, sin shell interpolada
scripts/pipeline.py --brief ... --case ...
   ↓ proceso agy independiente por pasada
Antigravity CLI / proveedor de IA / fuentes externas
   ↓ NDJSON y arrays validados
Claims y evidencias canónicas + expediente
   ↓ scripts/obsidian_sync.py
Vault independiente + índices de navegación
   ↑ MCPVault de solo lectura consultado por Antigravity
```

## Archivos del programa

| Archivo | Función |
|---|---|
| GEMINI.md | Contrato íntegro más extensiones de riesgo y procedencia |
| scripts/setup.py | Crear datos faltantes y configurar destino local |
| scripts/frontend.py | API local, uploads, jobs y lecturas de expedientes |
| scripts/frontend.html | Biblioteca, filtros, formulario, lectores y notas |
| scripts/pipeline.py | Pasadas, validaciones, publicación y lock |
| scripts/library.py | Metadatos, asociación de claims, catálogo e índices |
| scripts/obsidian_sync.py | Copia local con comprobación de bytes |
| scripts/*.sh y wrappers raíz | Delegar al pipeline con Python funcional |
| Abrir-investigacion.cmd | Inicio en Windows |

## Datos persistentes

`.project-intelligence/claims/{architecture,dependencies,changes}.json` guarda los registros canónicos. Su categoría procede del diseño original y no sustituye a las etiquetas de organización. `investigation_id` asocia claims de nuevas investigaciones con expedientes.

`evidence/` y `claims/` conservan respuestas crudas, resultados parseados y stderr. Aunque algunas salidas se llaman raw.json, el transporte real puede ser NDJSON. No se reutiliza una conversación previa entre pasadas.

`library/<id>/case.json` guarda pregunta, materiales, tags, estado, fechas, claim_ids y contadores. `claims.json` del expediente es una copia seleccionada de los registros canónicos, no otro mecanismo independiente de verificación. Resultados, fuentes y auditoría se generan solo con ese subconjunto.

`library/sources.json` agrupa URLs externas sin fragmentos. Biblioteca.md, Temas.md y Fuentes.md son índices regenerables. Relaciones por tags o URLs son navegación.

`inputs/` conserva brief, archivos originales y hashes. El expediente conserva adjuntos para publicación y descarga; estas copias no equivalen a un protocolo pericial de custodia.

## Ejecución y consistencia

Un job del frontend ejecuta research seguido de document. Un pipeline.lock creado exclusivamente contiene PID y evita ejecuciones simultáneas del pipeline. El frontend también rechaza iniciar un segundo job. El estado detallado del job vive en memoria; claims y artefactos ya guardados sobreviven al cierre.

La escritura usa temporales y reemplazo para muchos archivos. No hay una transacción completa entre claims, índices, docs y vault. Un fallo puede dejar resultados parciales legítimos; los reintentos conservan veredictos, colas y evidencias. No se afirma atomicidad de toda la investigación.

## Validación

El pipeline comprueba IDs, cantidad y texto original de los claims, estados admitidos y evidencia. Verifica archivos dentro del repositorio, rangos y extractos, commits reales y metadatos externos. Relocaliza un extracto desplazado únicamente si coincide exactamente en una ubicación.

Skeptic recibe solo claim, evidence e ID, además del contrato; no recibe el razonamiento del Investigator. Writer recibe únicamente VERIFIED con política de riesgo vigente. Los controles de riesgo exigen estructura y conteos apropiados; no prueban automáticamente independencia documental, identidad oficial o interpretación correcta.

## Interfaz y seguridad local

El servidor estándar está ligado a loopback y valida Host y token para acciones/lecturas API. Las rutas de expediente y descarga se acotan. Se limita el tamaño de la solicitud y los adjuntos. Las vistas de texto evitan interpretar HTML aportado como markup libre.

El token protege la API local frente a peticiones ajenas simples; no es una autenticación multiusuario. No hay TLS, cuentas, proxy remoto o endurecimiento de producción. Personas/procesos con acceso al equipo pueden acceder a sus archivos. Las fuentes o respuestas del agente siguen siendo datos no confiables que necesitan revisión.

## Obsidian

La configuración local ignorada por Git guarda vault_path. Publicar copia docs, reportes, índices, expedientes y adjuntos, comprueba bytes y registra recibo. Un archivo notas.md existente en el vault se omite para proteger ediciones personales. Guardar notas desde el frontend actualiza explícitamente el original y su copia en el vault.

OBSIDIAN_SYNC_HOOK explícito mantiene prioridad sobre el adaptador local. El hook es un ejecutable que recibe el manifiesto; el proyecto no implementa un protocolo de homelab.

MCP reside en la configuración global de Antigravity, no en la API del frontend. El servidor MCPVault read-only permite consultar los documentos publicados, pero no es responsable de la copia automática.

## Pruebas y límites

Las pruebas simulan el agente en directorios temporales para verificar pasadas, exclusión de estados no VERIFIED, aislamiento, procedencia, reintentos, commits incrementales, notas protegidas y búsqueda/paginación de 100 expedientes. No demuestran calidad factual del modelo ni evalúan su juicio semántico.

El protocolo real de Antigravity y una publicación local se comprobaron durante la configuración. Después de actualizar el CLI conviene probar compatibilidad de sus eventos. No hay CI con credenciales del usuario ni llamadas automáticas al modelo.
