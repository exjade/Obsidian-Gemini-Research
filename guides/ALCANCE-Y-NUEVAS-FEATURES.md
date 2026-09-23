# Alcance y nuevas features

## Acuerdos registrados

Conservar funciones, mejorar accesibilidad y automatizar la evaluación de fuentes. Dos entradas futuras: pregunta o documentos, con búsqueda externa opcional. Agentes especializados con entregables comprobables. Auditoría final de respuesta contra pregunta, alcance y fragmentos. Cierre estricto para todas las hipótesis admitidas; no fabricar consenso ni confundir falta de evidencia con refutación. Todo ello figura en PENDIENTES.md.

## Primera entrega implementada

Una nueva investigación prepara candidatos y ejecuta una revisión separada de utilidad. No ejecuta automáticamente Collector ni Writer. El revisor recomienda entre una y tres hipótesis y explica por qué cada propuesta responde, o no, a tu pregunta. Su contrato está en skills/hypothesis-review/SKILL.md.

En **Pregunta y alcance** o **Resumen**, selecciona entre una y tres hipótesis y pulsa **Aprobar estas hipótesis**. Después pulsa **Investigar el alcance aprobado**. Aprobar sólo delimita el trabajo: no comprueba ninguna afirmación.

La revisión de pertinencia no equivale a revisión científica ni a auditoría externa. El origen declarado por Investigator y las corridas de generación/revisión quedan visibles. El sistema conserva propuestas descartadas, evidencia y veredictos históricos, sin considerarlos resueltos.

## Investigaciones anteriores

Abre el expediente y pulsa **Revisar qué hipótesis vale la pena investigar**. Esta acción usa Antigravity, pero sólo revisa el alcance. No aplica cambios hasta que aceptes una selección. La reevaluación desde terminal y frontend requiere ese alcance aprobado.

No se han generado propuestas nuevas ni reclasificado los expedientes reales durante esta entrega. Puedes revisar y aprobar el alcance cuando quieras. La versión anterior de resultados conserva su carácter histórico; todavía falta implementar la nueva puerta de cierre científica y su presentación visual.

## Servicio actualizado

La instancia con esta entrega está en http://127.0.0.1:8768/. Los servicios anteriores se conservan. Si usas uno anterior, la interfaz indica dónde abrir la versión con soporte de alcance. Después de reiniciar el equipo:

```powershell
Set-Location 'Y:\ChatGPT\obsidian-gemini-research\my_docs'
python scripts/frontend.py --port 8768
```

Para CLI: `python scripts/pipeline.py document --case ID --review-scope` prepara la propuesta; `--approve-scope ID1,ID2` sólo registra la selección; `document --case ID` investiga únicamente las hipótesis admitidas. Nueva investigación por CLI con `research --case ID` también requiere aprobación posterior.

## Límites y siguientes entregas

Esta entrega NO implementa todavía edición de formulaciones, comprobación automática de identidad editorial, recuperación con presupuesto, cierre estricto de todas las hipótesis, auditor semántico final ni la reorganización completa de pantallas. La selección puede incluir un candidato no recomendado, con motivo registrado, pero no lo convierte en una hipótesis científicamente válida. La edición/revisión de formulaciones será el siguiente paso del control de alcance.

Luego se abordará recuperación automática de fuentes y el control de cierre en servidor. Hasta entonces, ejecución terminada e informe generado no certifican investigación científicamente cerrada. Los límites actuales de PDF siguen vigentes: 15 MB en formulario y 300 páginas en conversión, sin OCR.
