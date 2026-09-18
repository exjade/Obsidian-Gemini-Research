# Control manual de cambios

El usuario controla los push y releases. El asistente prepara cambios revisables, pruebas, documentación y manifiestos; no publica automáticamente.

## Dos historiales distintos

- CHANGELOG.md de la raíz: evolución del programa.
- docs/changelog/: resultados privados del pipeline sobre commits; no es la lista de cambios editada por el desarrollador.

## Primer baseline

Revisa el índice actual con git diff --cached. No existe HEAD hasta crear el primer commit. El manifiesto inicial indica commit null; los hashes corresponden a bytes del índice, no a sus versiones con distintos finales de línea en el disco.

Después de hacer el primer commit/push siguiendo GITHUB.md, conserva una referencia:

```powershell
git tag baseline-local
git push origin baseline-local
```

Ese push también lo hace el propietario. Una etiqueta no despliega el servidor.

## Antes de un nuevo hito

Define objetivo, fuera de alcance, archivos previstos, migraciones, backup y pruebas. Comprueba que no hay cambios ajenos sin guardar. Usa una rama concreta, por ejemplo:

```powershell
git switch -c hito/flujo-y-navegacion
```

Si la rama ya existe, inspecciónala en vez de recrearla. No reutilices una investigación real como fixture pública.

## Revisar la entrega

```powershell
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
git diff --name-status baseline-local
git ls-files .project-intelligence docs/research.md docs/architecture.md
```

La última comprobación debe estar vacía. Los cambios respecto a baseline incluyen lo ya commiteado más cambios del working tree; revisa separadamente el índice que subirás.

Registro de entrega recomendado:

```text
Hito:
Referencia base real:
Commit final real, o pendiente:
Archivos creados/modificados/eliminados:
Cambios fuera de alcance y motivo:
Migración y cómo revertirla:
Pruebas ejecutadas y resultado:
Limitaciones sin comprobar:
Revisión del propietario:
Push/release manual y URL real, o pendiente:
```

Una revisión de Git no muestra cambios en datos ignorados. Si un hito migra .project-intelligence, se debe registrar también versión de esquema, conteos, hashes apropiados, backup y comprobación de preservación, sin publicar los datos privados.

## Recuperar una versión

Haz backup de datos antes de cambiar versiones. Para probar código anterior utiliza una copia o worktree aislado y no sueltes un git reset --hard sobre cambios sin revisar. Un rollback de código no revierte automáticamente una migración de datos ni ediciones personales del vault.
