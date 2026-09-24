# Qué falta para concluir una investigación

La ejecución puede terminar sin que la investigación esté resuelta. La aplicación comprueba todas las hipótesis del alcance que aprobaste antes de permitir consolidar resultados.

## Qué verás

- **Investigación inconclusa:** hay hipótesis pendientes. El panel muestra cuáles, el motivo y un enlace a la ficha para continuar.
- **Lista para consolidar resultados:** todas las hipótesis admitidas pasan los controles actuales; falta generar el informe.
- **Resultados consolidados:** el informe corresponde al alcance y a los veredictos vigentes, y pasó esos controles.

La barra de cinco etapas sólo mide trabajo registrado. No demuestra que haya respaldo suficiente ni sustituye este control.

La fecha en que una investigación termina no equivale a la fecha en que cambió el veredicto ni a la fecha en que se registró una resolución científica. La ficha conserva esas tres historias por separado, junto con comprobaciones técnicas, revisiones humanas y reformulaciones. Una comprobación de página no cierra una hipótesis.

## Qué permite avanzar

Una hipótesis VERIFIED debe cumplir la política actual y conservar evidencia comprobable, revisión crítica y búsqueda de contradicciones. Una hipótesis CONTRADICTED necesita un pasaje identificado explícitamente como refutación y comprobado contra la evidencia conservada. Una ficha con resolución científica v1 usa esa resolución separada del veredicto histórico, pero el cierre vuelve a validar su política, versión, identidad/hash del claim, matriz de dimensiones, pasajes y criterios. Los registros antiguos sin esa proyección siguen usando el control compatible con su veredicto histórico. No basta con que no se haya encontrado apoyo.

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

Una **indeterminación justificada** puede ser una conclusión válida si la proyección v1 conserva dimensiones irresueltas, búsqueda acotada completada o presupuesto legítimamente agotado, consultas de apoyo y contradicción para los huecos, materiales aportados considerados, criterios del auditor y límites explícitos. El cierre vuelve a comprobar esos datos y la identidad del claim; una etiqueta `indeterminate` aislada, obsoleta o incompleta no resuelve el alcance. Los expedientes con la versión histórica del control no se reclasifican automáticamente.

## Resolución científica versionada (entrega 2026-09-22)

La ficha conserva el texto original. Antes de recuperar evidencia, el planificador estructura intervención, espaciamiento, comparación, población, material, resultado y horizonte. Una dimensión vacía significa que el claim no la declara; no se rellena en silencio.

Cada dimensión puede quedar respaldada, contradicha o sin resolver mediante relaciones con pasajes identificables. La rúbrica es categórica (`direct`, `partial`, `indirect`, `contradictory`, `mixed`, `unreported`); no expresa una probabilidad de verdad.

`VERIFIED` requiere que el auditor y Skeptic aprueben la formulación completa, que cada dimensión declarada tenga respaldo de fuente primaria confirmada y que la búsqueda contradictoria prevista esté registrada. `CONTRADICTED` requiere concordancia entre el auditor y Skeptic más un pasaje directamente contradictorio de fuente primaria. Un `mismatch`, dato no informado, enlace bloqueado o resultado nulo no refuta por sí mismo. La evaluación de cierre reconoce una proyección científica v1 válida de respaldo, refutación o indeterminación sin reescribir el veredicto histórico de la ficha.

El sistema registra indeterminación sólo cuando el auditor identifica las dimensiones pendientes, los recibos muestran los huecos y contradicciones buscados y los materiales asociados fueron considerados. En cualquier otro caso el resultado sigue sin resolver. La indeterminación limita la pregunta respondible; no afirma que no existan estudios.

Una conclusión más estrecha es una formulación hija explícita, con texto, dimensiones, razón, autor y versión. Nunca hereda evidencia ni veredicto. La afirmación original, sus evaluaciones y pasajes permanecen como historial.

Los modos de entrada son: búsqueda desde la pregunta; sólo PDFs locales asociados; PDFs locales con búsqueda complementaria. Extraer texto localiza pasajes, pero la evaluación de pertinencia sigue separada. La matriz acumulada y los recibos permiten ver qué dimensión quedó cubierta y qué se intentó.

Las pruebas automáticas usan fixtures sintéticos para verificar contratos y reglas. No estiman calidad científica ni sustituyen validación bibliográfica independiente.
