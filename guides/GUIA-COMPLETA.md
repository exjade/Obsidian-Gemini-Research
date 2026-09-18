# Guía completa del proyecto

Esta guía describe el programa implementado, cómo usarlo y cómo conservar sus datos. No presupone un servicio permanente: lo enciendes cuando necesitas la interfaz y lo apagas al terminar.

## 1. Qué hace cada componente

| Componente | Responsabilidad | Cuándo debe estar activo |
|---|---|---|
| Frontend en el navegador | Crear, buscar y leer investigaciones | Mientras usas la interfaz |
| Servidor Python local | Servir la interfaz y ejecutar acciones | Mientras usas el frontend |
| Pipeline | Ejecutar las cuatro pasadas y validar resultados | Durante una investigación o publicación |
| Antigravity CLI | Acceder al modelo y sus herramientas | Se inicia automáticamente por pasada |
| Repositorio local | Conservar programa, expedientes y registros | Los archivos permanecen aunque el servidor esté apagado |
| Vault Obsidian | Leer documentación, fuentes y notas | Para consultar el vault en Obsidian |
| MCPVault | Permitir que Antigravity consulte el vault | Cuando el cliente MCP lo inicia |
| Git/GitHub | Versionar y compartir código y guías | Para commits, changelog y publicación |

Cerrar el navegador no detiene el servidor. Cerrar la ventana del servidor sí puede interrumpir un trabajo. Apagar Windows detiene el servicio, pero no elimina los archivos guardados. GitHub no mantiene encendido este servidor Python.

## 2. Requisitos

- Python 3.10 o posterior; el programa usa biblioteca estándar, sin paquetes pip obligatorios.
- Antigravity CLI instalado y autenticado para generar/revisar investigaciones.
- Internet para el proveedor de IA y fuentes externas. Leer expedientes ya guardados no requiere una llamada al modelo.
- Git para versionado y changelog; Git Bash es opcional si usas los wrappers `.sh`.
- Obsidian si quieres leer el vault.
- Node.js/npm si habilitas MCPVault. El frontend no necesita Node.js.

Verifica las instalaciones en PowerShell:

```powershell
python --version
git --version
& "$env:LOCALAPPDATA\agy\bin\agy.exe" --version
```

Si `python` abre Microsoft Store o no existe, prueba `py -3 --version`. Sustituye `python` por `py -3` en los comandos de esta guía cuando corresponda. El lanzador Windows intenta ambos y comprueba la versión mínima.

Instala Antigravity desde su [documentación oficial](https://antigravity.google/docs/cli/getting-started). Abre una sesión interactiva para autenticarte antes de investigar; el modo headless reutiliza esa autenticación y no puede completarla por ti. [Referencia headless](https://antigravity.google/docs/cli/headless).

## 3. Tu instalación actual

Estas rutas corresponden a la instalación del propietario; otro usuario debe elegir las suyas:

```text
Programa y datos originales:
Y:\ChatGPT\obsidian-gemini-research\my_docs

Vault independiente:
Y:\Obsidian\obsidian-gemini-research

Interfaz:
http://127.0.0.1:8765
```

Y: debe estar accesible antes de iniciar el programa. El vault está separado de Work. No hay conexión remota de homelab configurada.

## 4. Abrir el servidor después de reiniciar

La forma habitual es hacer doble clic en `Abrir-investigacion.cmd` dentro de la carpeta del programa. Abre una ventana y el navegador. Mantén esa ventana abierta.

Alternativa desde PowerShell:

```powershell
Set-Location 'Y:\ChatGPT\obsidian-gemini-research\my_docs'
python scripts/frontend.py
```

Si el navegador no se abre, escribe `http://127.0.0.1:8765` manualmente. Esa dirección siempre apunta a la computadora desde la que se abre: no es una URL compartida entre dispositivos.

Para iniciar sin abrir el navegador:

```powershell
python scripts/frontend.py --no-browser
```

No hay arranque automático instalado. Por ahora se recomienda iniciarlo bajo demanda. El proceso que pudo arrancar el asistente durante la configuración no sustituye al lanzador para futuros reinicios.

## 5. Detener el servicio

Espera a que termine el trabajo. En la ventana donde corre Python pulsa Ctrl+C. Luego puedes cerrar la ventana. Si la ventana se cierra durante una investigación, el navegador deja de recibir estado y el proceso hijo podría seguir trabajando hasta terminar o fallar: no inicies otra ejecución sin comprobar el lock.

Si necesitas identificar un servicio iniciado en segundo plano:

```powershell
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like '*scripts/frontend.py*' } |
    Select-Object ProcessId, CommandLine
```

Comprueba el proceso y que no haya trabajo activo antes de detener su PID concreto con `Stop-Process -Id NUMERO`. No detengas todos los procesos Python: otras aplicaciones podrían usarlos.

## 6. Primera instalación desde un clon

Entra en la carpeta clonada y ejecuta:

```powershell
python scripts/setup.py
python scripts/setup.py --vault 'C:\MiBiblioteca\obsidian-gemini-research'
python scripts/frontend.py
```

`setup.py` crea solo datos faltantes. No vacía claims, expedientes ni evidencias existentes. `--vault` configura o cambia explícitamente el destino de publicación. El vault debe estar separado del repositorio. Cambiar el destino no migra tus notas personales desde el vault anterior.

En Obsidian selecciona Abrir carpeta como vault y elige la ruta configurada. El programa no requiere plugins adicionales para copiar documentos al vault.

## 7. Crear una investigación

1. En Biblioteca pulsa **+ Nueva investigación**.
2. Escribe un título reconocible.
3. Describe la pregunta, contexto, hipótesis y qué quieres comprobar. Distingue lo que sabes de lo que sospechas.
4. Añade etiquetas separadas por comas, por ejemplo `tema/tecnologia, proyecto/comfyui`.
5. Pega enlaces y explica qué aporta cada uno. Un enlace aportado todavía no es evidencia verificada.
6. Añade archivos si los necesitas: máximo doce y quince MB totales.
7. Pulsa **Investigar y revisar las pruebas**. El servicio ejecuta research y luego document para ese expediente.
8. Espera. Las pasadas pueden tardar minutos y cada llamada tiene un timeout local de 360 segundos.
9. Lee Resultados, Fuentes y procedencia, Todas las afirmaciones y Auditoría.

El texto UTF-8 de TXT, Markdown, CSV y JSON se entrega al investigador. Imágenes y PDF se conservan con hash y pueden descargarse, pero no se interpretan automáticamente. Puedes aportar una transcripción o descripción; no cuenta por sí misma como corroboración independiente.

Los textos y enlaces recibidos son materiales de investigación, no nuevas instrucciones para saltarse el contrato. La pregunta y los textos incluidos se transmiten al proveedor mediante Antigravity.

## 8. Entender el flujo y los estados

| Pasada | Trabajo | Resultado |
|---|---|---|
| Investigator | Proponer hipótesis a partir de la pregunta y materiales | Claims UNVERIFIED |
| Collector | Buscar pruebas y conservar referencias | Evidencias vinculadas |
| Skeptic | Intentar refutar y clasificar | Veredictos y explicación |
| Writer | Redactar usando solo VERIFIED | Resultados con fuentes |

| Veredicto | Significado |
|---|---|
| UNVERIFIED | Pendiente de revisión |
| VERIFIED | Aceptado por el flujo con la evidencia registrada |
| PARTIAL | Apoyo incompleto; no llega a Writer como hecho consolidado |
| UNSUPPORTED | Soporte insuficiente |
| CONTRADICTED | Se registró evidencia contradictoria |

Completada, en curso, con error o interrumpida son estados de ejecución del expediente, no grados de verdad. Una ejecución puede terminar sin claims VERIFIED.

Legal, médico, fiscal, migratorio y seguridad activan escrutinio sensible. Los claims sensibles o favorables requieren dos fuentes primarias independientes para VERIFIED; en legal se exige texto oficial. El wrapper controla estructura y conteos, pero el juicio sobre apoyo semántico, independencia y carácter oficial sigue requiriendo revisión. No es un dictamen científico o pericial automático.

## 9. Biblioteca y cerebro de Obsidian

Usa el buscador para título, pregunta, enlaces, etiquetas y texto de las afirmaciones. Filtra por etiqueta o estado. Hay doce expedientes por página, ordenados por creación reciente.

Cada expediente conserva pregunta, resultados, fuentes, auditoría, claims y adjuntos propios. El catálogo central de fuentes reúne URLs presentes en evidencias y enlaza con sus expedientes; no confunde enlaces todavía sin revisar con fuentes consolidadas.

En el vault se generan:

```text
Biblioteca.md          Entrada general
Temas.md               Navegación por etiquetas
Fuentes.md             Catálogo de URLs registradas
Guia.md                Orientación de uso
Investigaciones/
  <fecha-titulo-id>/
    resumen.md         Índice del expediente y relacionadas
    pregunta.md
    resultados.md
    fuentes.md
    auditoria.md
    notas.md           Tu espacio personal
    adjuntos/
```

Las etiquetas `tema/...` agrupan asuntos, `proyecto/...` agrupan trabajos y `estado/...` describen la ejecución. El frontend normaliza etiquetas a minúsculas y guiones. La [documentación oficial de etiquetas](https://obsidian.md/help/tags) explica la jerarquía y su búsqueda en Obsidian.

Relacionadas significa que dos expedientes comparten etiquetas o URLs. Ese enlace ayuda a navegar y no acredita que dos fuentes sean independientes o dos conclusiones concuerden.

**Mis notas y etiquetas** permite editar desde el frontend. Las notas también pueden editarse en Obsidian; al abrir el expediente se lee la copia del vault si existe. La publicación respeta `notas.md` existente. Las etiquetas y resúmenes generados se gestionan desde el frontend; editar manualmente su YAML no garantiza conservarlo en una regeneración.

Después de cambiar etiquetas, pulsa **Publicar biblioteca en Obsidian** para actualizar sus índices. No renombres ni muevas carpetas generadas de expedientes: el programa las localiza por ID.

## 10. Publicación local y MCP

La publicación copia documentos y verifica sus bytes; registra hashes y destinos en `reports/obsidian-receipt.json`. `SYNCED` confirma la copia local, no la veracidad de la investigación ni una sincronización remota.

MCPVault permite a Antigravity consultar el vault en modo lectura; no realiza esa publicación. Configura rutas reales de tu computadora:

```powershell
& "$env:LOCALAPPDATA\agy\bin\agy.exe" mcp add obsidian 'C:\Program Files\nodejs\npx.cmd' -y '@bitbonsai/mcpvault@0.16.0' 'C:\MiBiblioteca\obsidian-gemini-research' --read-only
& "$env:LOCALAPPDATA\agy\bin\agy.exe" mcp list
```

Comprueba `Get-Command npx.cmd` si Node está instalado en otra ruta. Reinicia sesiones de Antigravity tras cambiar el servidor. Pídele listar la raíz usando MCP, sin terminal ni modificaciones. [Instalación oficial MCPVault](https://mcpvault.org/install/).

El botón Abrir en Obsidian usa el [protocolo URI oficial](https://help.obsidian.md/Extending+Obsidian/Obsidian+URI). Obsidian debe conocer el vault. Si no abre, registra primero la carpeta como vault; evita dos vaults con el mismo nombre.

## 11. Permisos de Antigravity

La configuración activa está en `%USERPROFILE%\.gemini\antigravity-cli\settings.json`; `.gemini/settings.json` del proyecto es el esqueleto antiguo de Gemini y no registra la conexión activa de Antigravity.

En esta instalación se habilitaron lecturas del repositorio y `read_url(*)` para consultar fuentes externas. En otra computadora esos permisos no se copian con Git: autentica y configura los permisos necesarios siguiendo la [guía oficial](https://antigravity.google/docs/cli/permissions). Conserva los campos existentes y revisa reglas deny/ask que prevalezcan. No se emplea `--dangerously-skip-permissions`.

El modo headless no puede mostrarte un diálogo interactivo de permiso. Un permiso denegado puede producir una respuesta vacía y el pipeline la rechaza. Autoriza la lectura necesaria en la configuración real y reintenta; no conviertas el fallo de lectura en evidencia positiva.

## 12. Recuperar errores

| Problema | Acción |
|---|---|
| La página no abre | Arranca el lanzador; comprueba Y: y el puerto 8765 |
| Puerto ocupado | No abras varios servicios. Identifica el proceso; la instancia existente puede ser este frontend u otro programa |
| Antigravity no disponible | Verifica PATH o `%LOCALAPPDATA%\agy\bin\agy.exe` |
| Falta autenticación | Inicia Antigravity interactivamente y autentica |
| Respuesta vacía/permisos denegados | Consulta detalle y stderr; configura el permiso de lectura indicado |
| El extracto no coincide | Inspecciona archivo y líneas. Se relocaliza solo una coincidencia exacta única; contenido cambiado o ambiguo se rechaza |
| Writer falla | Reintenta el expediente: conserva veredictos ya guardados |
| Obsidian FAILED | Comprueba destino y permisos de escritura; reintenta publicación sin ejecutar IA |
| Expediente interrumpido | Reintentar retoma el brief si no hay claims; si existen, retoma revisión y publicación |
| Changelog sin Git/HEAD | Necesita commits. Git init solo no crea un commit |
| Changelog con cambios pendientes | Revisa y guarda cambios de código en commits antes de ejecutarlo |

Para reintentar solo publicación:

```powershell
python scripts/pipeline.py document --sync-only
```

Para un lock después de una interrupción:

```powershell
Get-Content .project-intelligence/pipeline.lock
Get-Process -Id NUMERO_DEL_LOCK -ErrorAction SilentlyContinue
```

El lock contiene el PID. Comprueba también la identidad del proceso, porque Windows puede reutilizar PIDs. Solo si verificas que la ejecución original ya no existe, elimina el archivo concreto:

```powershell
Remove-Item -LiteralPath '.project-intelligence/pipeline.lock'
```

No elimines claims, evidencias o estado para resolver un lock. Las salidas crudas y `stderr.log` están en claims/ para PASS 1 y evidence/ para otras pasadas. El servidor conserva detalle reciente en memoria; los registros del pipeline permanecen en disco.

## 13. Copias de seguridad y restauración

GitHub conserva código y guías, no la biblioteca privada. Una copia completa debe incluir:

- `.project-intelligence/`: claims, evidencias, biblioteca, inputs, estado y configuración local.
- `docs/`: documentación generada.
- El vault: especialmente notas personales editadas en Obsidian.

Detén trabajos y espera a que terminen antes de copiar. Conserva ambas ubicaciones: el vault no incluye necesariamente todos los logs y artefactos originales. Una copia guardada es preferible a depender únicamente de un espejo que puede reflejar errores.

Para restaurar, recupera esos directorios, instala requisitos, ejecuta setup sin reset y revisa `obsidian.json` si cambiaste de computadora. Un clon de GitHub sin backup de datos no recuperará tus investigaciones.

## 14. Actualizar el programa

Guarda tus cambios de código y realiza backup de datos. Detén el frontend cuando no haya trabajo activo, actualiza desde Git y vuelve a ejecutar setup y el lanzador. No borres `.project-intelligence/` como parte de una actualización. No hay migraciones de esquema versionadas todavía: una futura versión deberá documentar cualquier cambio incompatible.

## 15. Alcance actual

No se implementan OCR/visión, ejecución multiusuario, autenticación pública, búsqueda semántica, trabajo concurrente, almacenamiento distribuido ni despliegue homelab. El servidor HTTP estándar sirve una aplicación local de confianza; publicarlo en GitHub no significa desplegarlo en Internet.

Consulta [GitHub](GITHUB.md) para compartir el programa y [Arquitectura](ARQUITECTURA.md) para mantenerlo.
