# Estados y recorrido de una investigación

La pantalla separa dos preguntas: ¿terminó la ejecución? y ¿qué respaldo tiene cada afirmación?

| Señal | Significado | Acción |
| --- | --- | --- |
| Azul | En espera o en ejecución | Esperar; no enviar otra solicitud |
| Verde | Ejecución finalizada | Leer el veredicto; finalizar no significa verificar |
| Ámbar | Evidencia insuficiente o pendiente | Abrir la ficha, comprobar enlaces y aportar respaldo |
| Rojo | Error o interrupción | Consultar Detalle de ejecución; conservar el historial y reintentar |

## Reevaluación

La ficha conserva cuándo se solicitó, su última actualización, el estado anterior y el nuevo, y si Obsidian se sincronizó. Una revisión puede acabar correctamente con UNSUPPORTED. Si falla Writer, el veredicto puede estar guardado mientras Resultados conserva la publicación anterior.

Las futuras ejecuciones muestran la pasada activa: hipótesis, evidencia, revisión crítica y publicación. No estimamos porcentajes ni tiempo restante. Si el servicio se desconecta, el frontend avisa que no puede confirmar la finalización.

## Recorrido comprobable

En la ficha abre «Recorrido comprobable». Se muestran eventos de herramientas conservados en la última evaluación: búsquedas, lecturas, destinos y estados del proveedor. Si la ejecución fue un lote, algunas acciones pueden corresponder a otras afirmaciones. No son un registro exclusivo por afirmación ni prueban que la fuente respalde todo el texto. Una llamada DONE puede contener un fallo comunicado por la herramienta.

No se reconstruye pensamiento interno. La explicación del veredicto, los eventos observables y los pasajes comprobados son registros distintos. Esta versión presenta las acciones conservadas al terminar cada pasada; aún no transmite cada herramienta en vivo.

## Vistas vacías

- Hipótesis: puede quedar vacía cuando todas recibieron un veredicto; los claims sin respaldo siguen en Afirmaciones.
- Auditoría: sin banderas significa que no se marcaron riesgos prioritarios, no que una auditoría externa haya aprobado la investigación. La revisión de evidencia insuficiente aparece aparte.
- Artefactos: Studio está pendiente de implementar. No es un error de tu investigación.

## Obsidian

Resumen contiene avisos nativos con color y estado por afirmación. Un VERIFIED con fuentes externas pendientes aparece en ámbar. Tus notas personales no se regeneran. Los colores dependen del tema de Obsidian; siempre hay texto que explica el estado.
