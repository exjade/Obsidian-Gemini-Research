# Cómo entender y continuar una investigación

## Dos preguntas diferentes

«¿Terminó el proceso?» significa que el sistema ejecutó sus tareas y guardó registros. «¿Quedó resuelta la pregunta?» exige evidencia suficiente y una revisión de alcance y límites. Un proceso puede finalizar con una conclusión inconclusa.

La barra del frontend cuenta cinco etapas documentadas. No mide porcentaje de verdad, probabilidad de acierto ni cumplimiento completo del método científico. El sistema organiza una revisión documental; no sustituye un experimento, un peritaje ni una revisión humana.

## Qué significa cada etapa

| Etapa | Qué contiene | Qué no demuestra por sí sola |
| --- | --- | --- |
| Pregunta | Duda, alcance, fechas, enlaces y materiales aportados | Que sus premisas sean verdaderas |
| Hipótesis | Respuestas candidatas o afirmaciones que se ponen a prueba | Que la IA haya encontrado un hecho |
| Evidencia y fuentes | Origen del documento, pasaje relevante, comprobación de lectura y procedencia | Que una URL accesible respalde todo el texto |
| Revisión crítica | Evaluación del respaldo, independencia, pertinencia, contradicciones y límites | Que la explicación del modelo sea infalible |
| Publicación local | Informe guardado en Resultados y copia al vault configurado | Que se haya publicado en internet o en GitHub |

Una fuente es el origen: una entrevista, una sentencia, una página, un archivo. La evidencia es el contenido específico de ese origen que permite apoyar o refutar una afirmación. Un titular y una URL no reemplazan el pasaje relevante.

Hipótesis conserva los candidatos aún pendientes de evaluación. Cuando reciben veredicto dejan esa vista, pero permanecen en Afirmaciones. Una vista vacía no significa que todo se haya comprobado.

## Orden de lectura

El recorrido principal y los botones usan exactamente este orden:

1. Resumen: estado general, actividad reciente y lo que requiere atención (no es una pasada).
2. 1. Pregunta: duda, alcance y materiales.
3. 2. Hipótesis: candidatos pendientes de evaluación.
4. 3. Evidencia y fuentes: referencias y pasajes para ponerlos a prueba.
5. 4. Revisión crítica: veredictos, motivos y contradicciones.
6. 5. Resultados: informe generado mediante la publicación local.

Las herramientas de consulta aparecen en otra fila. Fichas de afirmaciones reúne todos los candidatos, pendientes y evaluados, y permite abrir sus fuentes y reevaluarlos. Auditoría prioriza revisiones; Actividad explica qué ocurrió. Ninguna es una etapa adicional. Artefactos es una función futura.

Actividad recibe del backend la misma proyección temporal canónica que se muestra en la cronología completa de cada afirmación. La vista de Actividad sólo presenta esa lista ya ordenada junto con eventos persistidos del expediente que no pertenecen a una afirmación; no vuelve a reconstruir revisiones, operaciones ni comprobaciones desde arrays paralelos. El resumen de Actividad en Inicio usa un subconjunto de esa lista. Refrescar reemplaza el snapshot completo, por lo que no acumula copias. Los enlaces de eventos de afirmación abren su ficha. Una ejecución vieja sin fecha conserva «Fecha no registrada».

Estos registros contestan preguntas distintas y permanecen separados:

| Registro | Qué significa | Qué no significa |
| --- | --- | --- |
| Investigación automática | Una operación `claim_research` con entradas, modo, estado, resultado o error. | No equivale a un cambio del veredicto y puede terminar sin resolver la afirmación. |
| Veredicto histórico | Una transición de evaluación persistida para el claim. | Una búsqueda, fallo o respuesta HTTP no lo cambia por sí sola. |
| Resolución científica | La conclusión, dimensiones cubiertas y límites asociados a una evaluación científica. | No reemplaza ni reescribe el veredicto histórico. |
| Comprobación técnica (`technical_check`) | Acceso, redirecciones y presencia/recuperabilidad de pasajes conocidos. | No busca estudios nuevos ni decide pertinencia científica. |
| Revisión humana | Decisión, fuentes examinadas y límites declarados por una persona. | No se vuelve evidencia automática ni modifica por sí sola el veredicto. |
| Reformulación | Propuesta versionada y relación explícita entre claim padre e hijo si se aprueba. | No modifica el padre ni hereda evidencia o veredicto automáticamente. |

La ficha conserva además historiales especializados por tipo de registro. Son vistas para consultar esos datos; Actividad y la cronología completa usan la proyección común para evitar que un mismo evento aparezca con distinto orden o significado. No incluye acciones en vivo que no hayan quedado persistidas.

Una nueva investigación deliberada crea otro identificador y conserva el resultado anterior. Un reintento de una operación fallida reutiliza su identidad y checkpoints. Si el último intento falla, el bloque **Resultado científico vigente** sigue señalando el último resultado terminado y **Último intento** muestra el error de esa operación. No hace falta leer registros técnicos para distinguirlos. Las herramientas observables de evaluaciones históricas se consultan en «Recorrido comprobable».

Auditoría prioriza claims sensibles o potencialmente favorables; no prueba que un auditor externo los haya revisado. Artefactos corresponde a Studio, todavía sin implementar.

## Cómo se verifica una afirmación

1. Escribe exactamente qué se está afirmando. Separa una declaración, una sospecha y el hecho subyacente.
2. Localiza el origen más directo pertinente: documento, entrevista original, registro o archivo.
3. Abre la fuente y conserva el pasaje y su localización. El programa registra recuperación, fecha y contenido; un extracto coincidente es sólo una primera comprobación.
4. Pregunta si ese pasaje respalda todo el texto: quién, qué, cuándo, lugar, condiciones y grado de certeza.
5. Busca activamente documentos que contradigan o limiten la interpretación. Fuentes que se copian entre sí no son independientes.
6. Registra un veredicto con sus límites. Para claims sensibles o favorables la política exige respaldo adicional; contar fuentes no garantiza una conclusión correcta.

El programa no puede demostrar autenticidad o pertinencia sólo porque una página exista. La clasificación de fuente primaria/oficial y parte de la revisión siguen dependiendo del modelo y de auditoría humana.

## Qué significa cada veredicto

- Pendiente de evaluar: todavía no se registró una evaluación final.
- Sin respaldo suficiente: no alcanza para sostenerla; no significa que se haya demostrado falsa.
- Respaldo parcial: existe apoyo limitado o faltan requisitos.
- Evidencia contradictoria: se registró una contradicción; revisa cuál. La ausencia de respaldo no basta para refutar una hipótesis.
- Verificada: la evaluación la consideró respaldada conforme a la política disponible. Es revisable y no equivale a verdad absoluta.

Un VERIFIED histórico con fuentes o extractos pendientes se señala como pendiente de comprobación independiente. No se modifica silenciosamente su veredicto anterior.

## Tu ejemplo: página bloqueada

Un 403 indica que la página rechazó la lectura automática. No se confirmó el extracto mediante esa recuperación. No sabemos sólo por eso si el artículo contiene el pasaje ni si la afirmación es verdadera o falsa.

Abre la página si puedes acceder normalmente. Busca un documento original accesible y un pasaje pertinente. Aporta el enlace y explica qué sustenta en «Aportar nuevas fuentes y reevaluar». Una transcripción o copia aportada por ti se conserva como material sin verificar hasta comprobar su procedencia. No se eluden restricciones de acceso.

La reevaluación conserva el estado anterior y usa la IA para revisar esa afirmación. Puede terminar correctamente con «Sin respaldo suficiente». Consulta Actividad y el historial de solicitudes para saber si terminó, si se guardaron los resultados y si se confirmó Obsidian.

## Cuándo darla por completa

Puedes considerar cerrado un trabajo dentro de su alcance cuando la pregunta está delimitada, todas sus hipótesis relevantes fueron examinadas, los veredictos tienen respaldo y límites trazables, se revisaron contradicciones y existe un informe que distingue hechos, incertidumbres y cuestiones abiertas.

No todas las hipótesis tienen que resultar verdaderas. Un resultado negativo o inconcluso puede ser un resultado válido; debe explicarse por qué y qué faltaría para avanzar. En esta versión no hay una aprobación humana de cierre registrada: la barra no decide ese cierre.

Si la pregunta principal sigue sin respuesta y buscas resolverla, continúa con las fuentes faltantes o redefine el alcance. Si decides cerrar como inconclusa, documenta esa decisión en tus notas personales.

## Nuevas ideas y ángulos

La IA puede sugerir hipótesis alternativas, preguntas, contraejemplos, fuentes que buscar y aspectos omitidos. Son propuestas, no hechos.

En Resumen abre «Nuevos ángulos». Las preguntas iniciales son plantillas basadas en el expediente. El botón prepara una nueva investigación independiente; puedes editarla y pedir a la IA una lluvia de ideas antes de ejecutarla. No modifica el expediente anterior ni consume una ejecución por el mero hecho de prepararla.

Ejemplo de pregunta: «¿Qué dijo literalmente la persona en la entrevista original, qué interpretación hicieron los titulares y qué evidencia adicional haría falta para comprobar la acusación subyacente? Separa esos tres niveles y busca explicaciones alternativas».
