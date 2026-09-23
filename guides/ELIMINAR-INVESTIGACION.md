# Eliminar una investigación y comenzar desde cero

1. Abre la investigación en la biblioteca.
2. Pulsa Eliminar investigación junto a los botones de comprobar fuentes y reintentar.
3. Lee la confirmación: incluye el nombre exacto del expediente. Puedes cancelar.
4. Al confirmar, desaparece de la biblioteca activa y se abre el formulario de una investigación nueva.

La eliminación se bloquea mientras haya una ejecución activa, incluso de otra investigación. Espera a que termine para evitar perder avances o interferir con los registros.

## Qué se conserva

La función retira la investigación del uso activo con copia recuperable; no destruye permanentemente sus datos. Se conserva el expediente completo, incluidos adjuntos, versiones, revisiones y notas locales. La carpeta de Obsidian se guarda por separado para preservar las notas editadas allí.

Los originales PDF y registros de evidencia compartidos permanecen. No se eliminan las otras investigaciones. Las afirmaciones pertenecientes al expediente retirado dejan de formar parte de los registros activos y del catálogo de la biblioteca.

Copias de recuperación:

- Proyecto: `.project-intelligence/deleted-investigations/<identificador>/case/`.
- Obsidian: `.research-trash/<identificador>/<investigación>/`.
- El archivo `removal.json` del proyecto registra el nombre, fecha y ubicaciones de ambas copias.

La función vuelve a generar los índices y solicita sincronización local. Si falla la sincronización, verás un aviso: la eliminación ya está guardada, pero falta actualizar los índices de Obsidian. Usa Publicar biblioteca en Obsidian para reintentarlo.

## Recuperación

Todavía no hay un botón Restaurar ni vaciado definitivo de papelera. La recuperación requiere revisar el expediente y reintegrar sus afirmaciones sin sobrescribir las investigaciones nuevas. No copies encima de los registros activos las copias completas de registros anteriores: podrías perder avances de otros expedientes. El botón de restauración es un pendiente independiente.

Comenzar otra investigación no reutiliza automáticamente el alcance ni los veredictos eliminados. Puedes volver a aportar los mismos documentos si los necesitas.
