# Fuentes y umbral de verificación

## Qué fallaba

El pipeline comprobaba que Gemini devolviera searched/fetched=true, fecha y extracto. No era una comprobación independiente de la página ni del extracto. Una URL bien formada y un resumen convincente no prueban una consulta real.

## Qué se comprueba ahora

El programa realiza GET público sin credenciales. Registra URL original/final, HTTP, fecha, redirecciones, formato, extracto esperado, texto recuperado y snapshot limitado con SHA-256. Se bloquean direcciones locales/privadas/reservadas, puertos distintos de 80/443 y destinos de redirección no públicos; la conexión fija una IP ya validada y TLS verifica el hostname original. Hasta cinco redirecciones, timeout de socket de ocho segundos, lectura máxima de 512 KiB. El timeout no es un límite global de lote ni de resolución DNS.

HTML/texto: busca coincidencia del extracto normalizado por Unicode y espacios, con mínimo de 40 caracteres. Ese mínimo evita coincidencias triviales: no es una medida científica de certeza. Si la página cambia, resume el texto con otras palabras, requiere JavaScript/login, bloquea robots, devuelve PDF u otro formato, o el extracto queda fuera del límite, se muestra no confirmado. No se concluye automáticamente que el modelo mintió.

404/410: enlace no disponible ahora. 403/429: acceso restringido. HTTP 200: página recuperada, aún sin probar apoyo al claim. Snapshot/hash: registro técnico local, no custodia pericial ni prueba de autenticidad de la institución.

## Cuándo se permite VERIFIED

El wrapper exige un registro local de comprobación cuyo URL/extracto/snapshot coincidan. Una declaración del modelo o un source_check_id inventado no bastan. Sólo referencias externas con extracto confirmado pueden contar como fuentes primarias. Después se mantiene la política: primaria pertinente, apoyo al texto exacto, independencia cuando corresponda y búsqueda de contradicciones. Sensibles/favorables requieren dos orígenes primarios; un origen limita VERIFIED a PARTIAL. La política legal vigente aún sólo acepta law/regulation/jurisprudence: revisar hechos procesales está pendiente.

No hay un porcentaje de verdad calibrado. Primariedad, oficialidad, independencia y apoyo semántico aún incluyen evaluaciones del modelo que requieren auditoría humana. Un extracto real puede interpretarse mal, contener una acusación en vez de un hecho probado o respaldar sólo parte de una afirmación. La comprobación técnica reduce un fallo, no elimina las alucinaciones.

Si toda la evidencia externa carece de contenido/extracto confirmados, incluso CONTRADICTED se limita a UNSUPPORTED: no se usa una referencia inaccesible como refutación comprobada. No detección o falta de evidencia no es por sí sola una contradicción; Skeptic recibe esa instrucción explícita, pero su cumplimiento semántico todavía exige revisión.

## Investigaciones anteriores

Sus estados se conservan. La ficha distingue veredicto histórico de comprobación independiente actual. Comprobar fuentes sin IA no cambia statuses ni sustituye extractos. La política source-v2 obliga a reevaluar claims con política antigua antes de Writer cuando se ejecute document; no se ejecutó esa reevaluación automáticamente. Se conservan resultados previos y registros de revisiones. El botón Comprobar sólo hace recuperación y comparación técnica, no una nueva investigación ni una revisión humana. La reevaluación selectiva con enlaces/texto nuevos ya está disponible en la ficha; ver REEVALUACION.md.

## Usarlo

Biblioteca → Afirmaciones → Abrir ficha. La ficha contiene origen, fechas, enlaces, disponibilidad, extractos, motivo del veredicto, búsqueda contradictoria declarada, historial y siguientes pasos. Fuentes ofrece estas referencias como tarjetas. El JSON queda como detalle opcional. Descargar texto comprobado permite conservar una copia de lectura con URL, fecha, HTTP y hash; nunca se abre el HTML remoto como contenido activo dentro de la aplicación. Las explicaciones del modelo no se presentan como pensamiento interno completo ni como acciones corroboradas.

Registros y snapshots: .project-intelligence/source-checks/, excluidos de Git. Deben incluirse en backups privados. El acceso móvil, una búsqueda de fuentes alternativas automática, la revisión humana persistente, migraciones completas y una traza de herramientas en vivo siguen pendientes.

## Tests

python tests/test_source_check.py
python tests/validate_pipeline.py
python tests/test_library.py

Fixtures: 200, 404/410, restricción, servidor, timeout, contenido cambiado, soft 404, formato no soportado, destinos privados, redirección privada, integridad de snapshot, falsificación de recibo y gate de publicación. Biblioteca y pipeline simulados; no se presupone ejecución real del modelo por estos tests.
