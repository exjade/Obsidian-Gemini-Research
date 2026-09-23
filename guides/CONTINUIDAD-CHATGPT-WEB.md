# Continuar desde ChatGPT web

## Empezar
1. En el proyecto Obsidian-Gemini-Research, sube CODIGO-ACTUAL.zip, MANIFIESTO-CONTINUIDAD.json y ESTADO-CONTINUIDAD.md. Si el chat no puede abrir ZIP, adjunta directamente los archivos de scripts/ y tests/ relevantes de la copia de desarrollo. Exige confirmación de lectura.
2. Sustituye las guías antiguas de continuidad y pega INSTRUCCIONES-PROYECTO-CHATGPT.txt en las instrucciones del proyecto. Adjunta también SKILL.md como referencia; esto no instala acceso a tu disco.
3. Usa conversación normal de ChatGPT si tu cuenta permite continuar. ChatGPT Work y Codex comparten uso: https://learn.chatgpt.com/docs/pricing . Cuatro sesiones que consumieron 25% no establecen cuatro periodos garantizados.
4. El progreso de reintentos ya está implementado; elige el siguiente pendiente actualizado. Pide un parche y sus pruebas; no reconstruir el programa desde documentación.

## Antigravity: aplicar en la copia aislada
La carpeta codigo-desarrollo contiene exactamente los archivos del paquete, sin investigaciones, configuración privada ni vault.
Entrega a Antigravity PROMPT-ANTIGRAVITY.txt, el manifiesto y el parche. Comprueba antes de aplicar:

    python scripts/verify_handoff.py --manifest ../MANIFIESTO-CONTINUIDAD.json --patch RUTA/cambio.patch

El verificador no modifica archivos y comprueba los hashes de TODOS los archivos base, incluidos los nuevos no publicados; también ejecuta git apply --check y bloquea rutas privadas. Si falla, no fuerces: devuelve el error y genera una nueva base cuando haya cambios legítimos.
Tras pasar, Antigravity aplica el parche SOLO en codigo-desarrollo, ejecuta pruebas pertinentes sin IA real y crea ejemplos sintéticos para la interfaz. No copies configuración de Obsidian ni inicies agy sobre datos personales para probar controles.

## Integrar y recuperar
Antes de incorporar: aplicación principal sin trabajos activos y respaldo privado COMPLETO. Antigravity revisa el diff; comprueba que los originales locales afectados todavía coincidan con sus hashes de base. Si cambiaron, detenerse y conciliar; nunca sobrescribir.
Incorpora únicamente archivos revisados y probados. Guarda una copia de los originales afectados y una lista de archivos nuevos. Para revertir, restaura esos originales y retira únicamente archivos nuevos de esa entrega; no toques investigaciones ni notas.
El propietario revisa y hace commit/push. Al finalizar renueva el manifiesto y el estado para el siguiente hito; el manifiesto inicial no sirve como base permanente.

## Respaldo privado
Mientras hay una investigación activa no se copia el estado mutable. Cuando termine, ejecutar desde el proyecto original:

    python scripts/continuity_backup.py --vault Y:/Obsidian/obsidian-gemini-research --destination C:/Users/Trabajo/Documents/Codex/2026-09-17/aqu-tienes-un-prompt-completo-y/work/private-backups

El respaldo incluye código, Git, PDFs y datos de investigación y vault; excluye entornos Python y cachés. Verifica bloqueo/actividad y cambios durante la copia. Sólo COMPLETE.json indica respaldo terminado. No subir estos respaldos a ChatGPT ni GitHub. Un fallo deja un respaldo parcial identificado, sin modificar el original.

## Estado y pruebas
Actualizar ESTADO-CONTINUIDAD después de cada entrega: versión de partida, cambios, archivos, pruebas reales, límites y próximo paso. La disponibilidad de ChatGPT web no implica acceso al disco: https://learn.chatgpt.com/docs/projects .
