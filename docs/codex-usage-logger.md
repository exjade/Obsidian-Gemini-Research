# Registro local de consumo de Codex por tarea

`scripts/codex_usage_logger.py` conserva snapshots versionados en
`.project-intelligence/codex-usage/<task_id>.json`. Sólo consulta el lector
aceptado `scripts/codex_usage_reader.py`; si la medición falla, registra una
captura `unavailable` con cuotas desconocidas y continúa sin guardar detalles
de error potencialmente sensibles.

Desde la raíz del proyecto:

```powershell
python scripts/codex_usage_logger.py start --task-id "TASK 31"
python scripts/codex_usage_logger.py snapshot --task-id "TASK 31" --phase PLAN
python scripts/codex_usage_logger.py snapshot --task-id "TASK 31" --phase EXECUTED
python scripts/codex_usage_logger.py close --task-id "TASK 31" --status DONE
python scripts/codex_usage_logger.py inspect --task-id "TASK 31"
```

Use `--status BLOCKED` o `--status ABORTED` para cerrar una tarea en esos
estados. `inspect` sólo lee el registro y recalcula la vista derivada en
memoria. Para pruebas aisladas, se puede anteponer `--root <carpeta temporal>`
a cualquier subcomando. `--snapshot-id` permite reintentar una captura con una
clave estable: repetir la misma captura es idempotente y reutilizar la clave
con datos distintos se rechaza.

Los timestamps se normalizan a UTC ISO-8601. Cada ventana conserva su
porcentaje restante y hora de reset por separado. El consumo derivado se
expresa en puntos porcentuales, nunca tokens. Si se detecta un reset dentro de
un intervalo, ese intervalo no recibe un consumo calculado; las mediciones
anterior y posterior y el evento detectado permanecen disponibles. Los huecos
de fase y las mediciones desconocidas permanecen `null`.
