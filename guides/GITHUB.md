# Preparar y publicar en GitHub

Publicar el repositorio comparte el programa y sus guías. No enciende el servidor local ni publica automáticamente la biblioteca personal. Esta guía no realiza el push por ti.

## 1. Qué se incluye

README, GEMINI.md, scripts, frontend HTML, lanzador, guías, pruebas, configuración de ejemplo, .gitignore y .gitattributes. Los wrappers de la raíz delegan al pipeline activo de Antigravity.

## 2. Qué queda fuera

`.project-intelligence/` completo contiene expedientes, adjuntos, fuentes crudas, logs, estado, rutas y configuración local. También se excluyen documentos generados de arquitectura/research, decisiones y changelog, archivos .env, cachés y entornos virtuales. Los datos iniciales se recrean con setup.py.

Excluir decisiones/changelogs por defecto protege el contenido de las investigaciones. Si deseas publicar un ADR o resultado concreto, prepara una copia revisada y saneada en una carpeta pública: no fuerces todo el directorio privado a Git.

Gitignore solo evita incorporar archivos no rastreados. No elimina datos ya publicados del historial. Si una credencial se publica, retirarla del último archivo no revoca su acceso.

## 3. Estado local preparado

El proyecto puede tener un repositorio Git local inicializado en rama main y archivos preparados sin commit. Confírmalo:

```powershell
Set-Location 'Y:\ChatGPT\obsidian-gemini-research\my_docs'
git status
git branch --show-current
git remote -v
```

Si una copia nueva todavía no tiene Git:

```powershell
git init -b main
```

No repitas init en otra carpeta por error. Usa el repositorio operativo del proyecto, no la carpeta temporal del asistente.

## 4. Elegir identidad y licencia

Usa tu nombre y un correo adecuado para commits. GitHub permite un correo noreply asociado a tu cuenta. Configura la identidad solo para este repositorio si prefieres:

```powershell
git config user.name 'TU NOMBRE'
git config user.email 'TU CORREO DE COMMITS'
```

El propietario todavía debe elegir una licencia. No se añadió una licencia abierta por suposición. Puedes empezar con un repositorio privado; si quieres permitir reutilización pública, decide y añade LICENSE antes de anunciarlo como software abierto.

## 5. Revisar exactamente lo que subirás

```powershell
git add README.md ROADMAP.md CHANGELOG.md GEMINI.md .gitignore .gitattributes Abrir-investigacion.cmd .gemini config guides scripts tests docs/README.md docs/decisions/.gitkeep docs/changelog/.gitkeep src/.gitkeep research.sh document.sh changelog.sh chatgpt_document.sh
git diff --cached --stat
git diff --cached
git diff --cached --name-only
git check-ignore .project-intelligence/state.json .project-intelligence/obsidian.json
```

No uses `git add -f` para saltarte las exclusiones. Revisa títulos, ejemplos, capturas y texto manual antes de hacer público el repositorio; gitignore no entiende datos personales escritos dentro de una guía.

Como comprobación adicional del índice:

```powershell
git ls-files .project-intelligence docs/research.md docs/architecture.md
```

Debe devolver vacío. Una ruta impresa indica que se incluyó contenido local y requiere revisión antes del push.

## 6. Crear el primer commit

```powershell
git commit -m 'Add local research library, evidence pipeline and documentation'
```

Esto guarda una versión local, no la sube. El changelog del pipeline requiere que existan commits y que los cambios de código estén guardados.

## 7. Crear un repositorio vacío en GitHub

En tu cuenta, crea un repositorio con el nombre que prefieras, por ejemplo `obsidian-gemini-research`. Elige su visibilidad. Si vas a subir el historial local, créalo vacío, sin README, gitignore o licencia generados desde la web, para evitar dos historiales iniciales. [Crear repositorio](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository).

No se presupone una cuenta, URL o nombre de propietario. Copia la URL HTTPS de tu repositorio real.

## 8. Conectar el remoto y subir

Sustituye TU_USUARIO por tu propietario real:

```powershell
git remote add origin https://github.com/TU_USUARIO/obsidian-gemini-research.git
git remote -v
git push -u origin main
```

Si origin ya existe, inspecciónalo antes de cambiarlo. No uses force push para resolver un conflicto inicial sin comprender el historial remoto.

GitHub requiere autenticación compatible con Git; la contraseña normal de la cuenta no es un token para Git HTTPS. Usa el gestor de credenciales configurado, GitHub CLI o SSH según tu entorno. No pegues tokens dentro de una URL, guía o archivo del proyecto. [Autenticación oficial](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).

## 9. Comprobar el resultado publicado

En la web verifica que README y guías abren, el código está en main y no hay expedientes, adjuntos, logs o configuración personal. Después prueba un clon independiente:

```powershell
git clone https://github.com/TU_USUARIO/obsidian-gemini-research.git
Set-Location obsidian-gemini-research
python scripts/setup.py
python tests/test_library.py
python tests/validate_pipeline.py
python scripts/frontend.py
```

Una instalación nueva debe abrir una biblioteca vacía. Configura autenticación, permisos y vault propios antes de investigar. Las pruebas simuladas no llaman al proveedor de IA; una investigación real sí.

## 10. Actualizaciones posteriores

Revisa cambios, ejecuta pruebas relevantes, selecciona archivos, crea commit y usa git push. Los datos privados seguirán fuera del índice. Para distribuir una versión, puedes crear una etiqueta de Git y una release después de comprobar su contenido; no adjuntes backups privados.

## 11. GitHub Pages y despliegue

GitHub Pages sirve sitios estáticos. No ejecuta este servidor Python ni el CLI autenticado de tu computadora. Para compartir el uso entre dispositivos haría falta diseñar autenticación, transporte remoto, permisos, concurrencia y almacenamiento; no basta con subir frontend.html. El alcance soportado sigue siendo uso local.
