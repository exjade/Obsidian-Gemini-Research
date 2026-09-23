# Qué falta para concluir una investigación

La ejecución puede terminar sin que la investigación esté resuelta. La aplicación comprueba todas las hipótesis del alcance que aprobaste antes de permitir consolidar resultados.

## Qué verás

- **Investigación inconclusa:** hay hipótesis pendientes. El panel muestra cuáles, el motivo y un enlace a la ficha para continuar.
- **Lista para consolidar resultados:** todas las hipótesis admitidas pasan los controles actuales; falta generar el informe.
- **Resultados consolidados:** el informe corresponde al alcance y a los veredictos vigentes, y pasó esos controles.

La barra de cinco etapas sólo mide trabajo registrado. No demuestra que haya respaldo suficiente ni sustituye este control.

## Qué permite avanzar

Una hipótesis VERIFIED debe cumplir la política actual y conservar evidencia comprobable, revisión crítica y búsqueda de contradicciones. Una hipótesis CONTRADICTED necesita un pasaje identificado explícitamente como refutación y comprobado contra la evidencia conservada. No basta con que no se haya encontrado apoyo.

PARTIAL, UNSUPPORTED y UNVERIFIED mantienen la investigación inconclusa. Un 403, 404 o tiempo agotado no demuestra falsedad ni justifica automáticamente un resultado indeterminado. Los candidatos fuera del alcance aprobado permanecen disponibles; excluirlos no significa resolverlos.

## Cómo continuar

1. Abre el panel **¿Qué falta para concluir?** en Resumen, Revisión crítica o Resultados.
2. Si falta alcance, revisa las propuestas y aprueba cuáles responden a tu pregunta.
3. Si falta respaldo, abre la ficha indicada. Puedes comprobar fuentes, aportar documentos o pedir reevaluación.
4. Cuando estén resueltas todas las hipótesis admitidas, vuelve a ejecutar revisión y publicación para consolidar el informe.

El sistema es responsable de recuperar y evaluar el respaldo. En esta entrega aún no implementa búsqueda alternativa automática ni la evaluación automática de identidad editorial: la interfaz explica esta limitación, no afirma haber hecho ese trabajo.

## Informes provisionales e historial

Cuando hay bloqueos, Collector y Skeptic conservan sus revisiones y se guarda un informe provisional con pendientes. Writer no redacta un subconjunto como conclusión final. Los informes reemplazados se conservan en `resultados-anteriores/` dentro del expediente local. Esta carpeta todavía no se exporta como archivo de versiones a Obsidian.

Obsidian recibe el informe provisional y avisos de cierre en el resumen después de sincronizar. Sus avisos reflejan la última ejecución; el frontend calcula los controles actuales al abrir el expediente. No se reclasifican automáticamente expedientes antiguos ni sus afirmaciones.

## Límites del control

El control verifica integridad, vigencia y reglas registradas; no garantiza verdad absoluta. Parte de la pertinencia semántica y de la independencia de fuentes todavía depende de la revisión del modelo. Falta el auditor de respuesta y la normalización completa de identidad documental.

Una **indeterminación justificada** puede ser una conclusión válida, pero necesita criterios explícitos y revisión de los motivos. Su registro y aceptación como resolución siguen pendientes; esta primera versión permanece bloqueada antes que inventar un cierre.
