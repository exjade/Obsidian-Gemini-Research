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
