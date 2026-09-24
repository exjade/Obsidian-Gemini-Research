# Lectura local del uso de Codex

## Resultado

La vía programática probada es el método JSON-RPC `account/rateLimits/read` de `codex app-server`, transportado como JSONL por stdin/stdout. La respuesta contiene ventanas estructuradas por `limitId`; el bucket `codex` expone ventanas `primary` y `secondary` con `usedPercent`, `windowDurationMins` y `resetsAt`. En la instalación observada, las duraciones son 300 minutos y 10080 minutos. El prototipo identifica las ventanas por su duración, calcula restante como `100 - usedPercent` y convierte los resets Unix a UTC.

La prueba local real confirmó que la versión instalada devuelve ambas duraciones y resets por este método sin abrir la TUI. La prueba sólo informó disponibilidad de campos; no conservó valores personales de cuota.

## Qué sabemos de `/status`

La ayuda de la CLI instalada ofrece `/status` dentro de la TUI, pero no un subcomando shell `status` o `usage` ni una salida JSON equivalente. La documentación oficial describe `/status` como información de configuración/sesión y documenta `account/rateLimits/read` en App Server para límites de cuenta. Sin código fuente legible de la versión instalada, no se confirmó que el renderer de `/status` invoque exactamente ese método. Por ello, el prototipo lee el endpoint estructurado documentado del App Server, no analiza la pantalla ni afirma reproducir todos sus campos.

Fuentes oficiales consultadas:

- [Codex App Server](https://learn.chatgpt.com/docs/app-server): protocolo JSON-RPC, inicialización, `account/rateLimits/read`, `rateLimitsByLimitId`, `usedPercent`, duración y reset.
- [Developer commands](https://learn.chatgpt.com/docs/developer-commands): propósito de `/status`, `/usage` y `/statusline`.
- [Codex CLI](https://learn.chatgpt.com/docs/codex/cli): comandos y uso de la CLI.
- [Changelog](https://learn.chatgpt.com/docs/changelog): versión publicada actual en el momento de la revisión.

La instalación local observada fue `codex-cli 0.155.0-alpha.16`; App Server se anuncia como experimental. La documentación del protocolo es oficial, pero el método puede evolucionar y el esquema incluido en la versión local es la comprobación práctica de compatibilidad.

## Alternativas y riesgos

| Método | Estructurado | Riesgo/limitación | Evaluación |
| --- | --- | --- | --- |
| Subcomando CLI `status`/`usage` | No disponible en la versión observada | No se puede automatizar desde shell con una interfaz oficial existente | Descartado por evidencia de `--help` |
| App Server `account/rateLimits/read` | Sí, JSON-RPC | App Server es experimental; el esquema podría cambiar entre versiones | Método recomendado mientras el contrato pase validación |
| Leer caché/estado privado local | No se necesitó | Puede contener secretos o formatos internos | Evitar |
| Parsear `/status` por PTY | Texto renderizado | Acoplado a TUI, idioma y versión | Fallback sólo si el método estructurado deja de estar disponible |
| Automatización visual/OCR | No | Frágil y menos auditable | Último recurso; no usar mientras App Server funcione |

El prototipo no lee archivos de configuración/autenticación, no reproduce headers ni llama endpoints privados directamente. Arranca el App Server local y solicita su método documentado. Descarta campos desconocidos y nunca muestra salida bruta del proceso.

## Contrato aislado

`scripts/codex_usage_reader.py` expone `read_codex_usage()` y devuelve:

- `five_hour_remaining_percent`, `five_hour_reset_at`;
- `weekly_remaining_percent`, `weekly_reset_at`;
- `captured_at`, `source`, `parser_version`, `codex_version`;
- `session_context_remaining_percent`, `model` y `configuration`, actualmente `null` porque esta consulta no los proporciona.

Ventanas o resets ausentes permanecen `null`; no se infieren. El adaptador falla cerrado ante respuesta desconocida, porcentajes fuera de rango o ventanas ambiguas. Las pruebas usan fixtures sintéticos y comprueban que los campos adicionales no salen en el resultado.

Si App Server o el schema cambia, la alternativa segura inmediata es revisar manualmente `/status`; no se deben leer credenciales, copiar tokens ni imitar una petición privada. El prototipo no está conectado al flujo C2C, a Sheets ni al sistema de investigación.
