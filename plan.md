# Git Conflict Resolver

Herramienta externa desarrollada en Python para resolver conflictos de Git mediante una interfaz TUI, orientada principalmente a complementar editores que no cuentan con una experiencia de resolución de conflictos comparable con VS Code.

---

# 1. Objetivo

Construir una herramienta ejecutable desde cualquier repositorio Git que permita:

* Detectar archivos con conflictos.
* Navegar entre archivos conflictivos.
* Navegar entre bloques de conflicto dentro de un archivo.
* Visualizar claramente:

  * `Current`
  * `Incoming`
  * opcionalmente `Base`
* Resolver cada conflicto mediante:

  * `Current`
  * `Incoming`
  * `Both — Current First`
  * `Both — Incoming First`
* Editar manualmente cuando las cuatro opciones anteriores no sean suficientes.
* Deshacer una resolución antes de guardar.
* Guardar los cambios.
* Marcar un archivo como resuelto mediante `git add`.
* Mostrar el progreso global de resolución.
* Detectar correctamente operaciones como:

  * merge
  * rebase
  * cherry-pick
  * revert
* Soportar posteriormente conflictos especiales:

  * binary
  * modify/delete
  * add/add
  * rename/rename

La herramienta **no pretende reemplazar Git ni convertirse en un cliente Git completo**.

Su responsabilidad debe limitarse a la resolución de conflictos.

---

# 2. Principios del proyecto

## 2.1 Git debe seguir siendo la fuente de verdad

La aplicación no debe mantener un estado paralelo que intente representar el repositorio.

Siempre que sea posible debe consultar directamente:

```bash
git status
git diff
git ls-files
git show
git rev-parse
```

La aplicación será una capa de presentación y manipulación encima del CLI oficial de Git.

---

## 2.2 No reimplementar Git

No implementar manualmente:

* detección de ramas
* index de Git
* staging
* merges
* rebases
* resolución de referencias
* detección de worktrees

Git ya proporciona estas capacidades.

Python solamente debe consumirlas.

---

## 2.3 Resoluciones deterministas

Operaciones como:

```text
Current
Incoming
Both Current First
Both Incoming First
```

deben realizar exactamente lo solicitado.

La aplicación **no debe intentar interpretar semánticamente el código**.

Por ejemplo:

```text
Current:
foo()
bar()

Incoming:
foo()
baz()
```

Seleccionar:

```text
Both Current First
```

debe producir:

```text
foo()
bar()
foo()
baz()
```

No se debe intentar deduplicar automáticamente:

```text
foo()
```

porque hacerlo implicaría aplicar heurísticas sobre el código.

---

# 3. Stack

## Lenguaje

```text
Python 3.13+
```

## UI

```text
Textual
```

## Git

```text
Git CLI
```

## Librerías estándar

Principalmente:

```python
subprocess
pathlib
dataclasses
enum
typing
tempfile
shutil
os
```

## Dependencias externas iniciales

```text
textual
```

Rich puede utilizarse indirectamente porque Textual ya está construido sobre Rich.

Evitar inicialmente dependencias como:

```text
GitPython
pygit2
dulwich
```

salvo que aparezca un caso concreto que Git CLI no pueda resolver adecuadamente.

---

# 4. Creación del proyecto

## 4.1 Crear directorio

```bash
mkdir git-conflict-resolver
cd git-conflict-resolver
```

---

# 5. Crear entorno de Python

Usar un entorno virtual local:

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14 \
  -m venv .venv
```

Activarlo:

```bash
source .venv/bin/activate
```

Verificar:

```bash
python --version
```

Debe utilizarse Python 3.13 o superior.

---

# 6. Actualizar herramientas base

```bash
python -m pip install --upgrade pip
```

Opcionalmente:

```bash
python -m pip install --upgrade setuptools wheel
```

---

# 7. Inicializar proyecto Python

Se recomienda utilizar `pyproject.toml`.

Estructura inicial:

```text
git-conflict-resolver/
├── pyproject.toml
├── README.md
├── .gitignore
├── src/
│   └── gconflict/
│       ├── __init__.py
│       └── app.py
└── tests/
```

---

# 8. Dependencias

Instalar Textual:

```bash
pip install textual
```

Para desarrollo:

```bash
pip install pytest
```

Opcionalmente:

```bash
pip install pytest-cov
```

---

# 9. `pyproject.toml`

Ejemplo inicial:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "gconflict"
version = "0.1.0"
description = "Terminal-based Git conflict resolver"
requires-python = ">=3.13"
dependencies = [
    "textual>=1.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov>=6"
]

[project.scripts]
gconflict = "gconflict.app:main"

[tool.setuptools.packages.find]
where = ["src"]
```

Esto permitirá ejecutar:

```bash
gconflict
```

después de instalar el proyecto.

---

# 10. Instalar proyecto en modo desarrollo

```bash
pip install -e ".[dev]"
```

Validar:

```bash
gconflict
```

---

# 11. `.gitignore`

```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.DS_Store
```

---

# 12. Arquitectura

Propuesta:

```text
src/gconflict/
├── __init__.py
├── app.py
│
├── git/
│   ├── __init__.py
│   ├── client.py
│   ├── repository.py
│   ├── index.py
│   └── operation.py
│
├── conflicts/
│   ├── __init__.py
│   ├── parser.py
│   ├── resolver.py
│   └── detector.py
│
├── models/
│   ├── __init__.py
│   ├── conflict.py
│   ├── conflicted_file.py
│   ├── git_operation.py
│   └── resolution.py
│
├── services/
│   ├── __init__.py
│   ├── conflict_service.py
│   └── repository_service.py
│
└── ui/
    ├── __init__.py
    ├── screens/
    │   ├── main.py
    │   └── conflict.py
    │
    └── widgets/
        ├── file_list.py
        ├── diff_view.py
        ├── conflict_actions.py
        └── progress.py
```

---

# 13. Capas

## `git/`

Responsable exclusivamente de comunicarse con Git.

Debe encapsular:

```bash
git rev-parse
git status
git diff
git ls-files
git show
git add
git restore
```

Ninguna otra capa debe ejecutar `subprocess` directamente.

---

## `conflicts/`

Responsable de:

* detectar conflictos
* interpretar markers
* construir objetos de dominio
* aplicar resoluciones
* reconstruir archivos

---

## `models/`

Representaciones internas sin lógica de infraestructura.

---

## `services/`

Orquestación entre:

```text
Git
↓
Conflict engine
↓
UI
```

---

## `ui/`

Responsable exclusivamente de presentación e interacción.

No debe contener lógica Git.

---

# 14. Git Client

Crear un wrapper central:

```python
from dataclasses import dataclass
import subprocess


@dataclass
class GitResult:
    stdout: str
    stderr: str
    returncode: int


class GitClient:
    def run(
        self,
        *args: str,
        check: bool = True,
    ) -> GitResult:
        process = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
        )

        if check and process.returncode != 0:
            raise RuntimeError(process.stderr.strip())

        return GitResult(
            stdout=process.stdout,
            stderr=process.stderr,
            returncode=process.returncode,
        )
```

---

# 15. Regla: nunca ejecutar comandos mediante shell

Evitar:

```python
subprocess.run(
    "git add " + filename,
    shell=True,
)
```

Usar:

```python
subprocess.run(
    ["git", "add", "--", filename],
)
```

Esto evita problemas con:

* espacios
* caracteres especiales
* command injection
* nombres que empiezan con `-`

---

# 16. Validar que estamos dentro de un repositorio

Ejecutar:

```bash
git rev-parse --show-toplevel
```

Si falla:

```text
Not a Git repository.
```

La aplicación debe finalizar sin intentar hacer nada más.

---

# 17. Detectar raíz del repositorio

```bash
git rev-parse --show-toplevel
```

Debe utilizarse esa ruta como raíz lógica del proyecto.

No asumir:

```text
current_directory == repository_root
```

El usuario debe poder ejecutar:

```bash
cd project/lib/accounts
gconflict
```

y la aplicación debe seguir funcionando.

---

# 18. Detectar `.git`

Nunca asumir:

```text
repository/.git/
```

Utilizar:

```bash
git rev-parse --git-dir
```

Esto es obligatorio para soportar correctamente:

* worktrees
* submodules
* configuraciones no estándar

---

# 19. Detectar archivos con conflictos

Comando principal:

```bash
git diff --name-only --diff-filter=U
```

Resultado:

```text
lib/accounts.ex
lib/users/user.ex
config/runtime.exs
```

Regla:

> Solo los archivos actualmente reportados por Git con estado unmerged deben mostrarse como archivos con conflictos.

---

# 20. Información avanzada del index

Utilizar:

```bash
git ls-files -u
```

Git almacena hasta tres stages:

```text
1 = base
2 = ours
3 = theirs
```

Ejemplo:

```text
100644 HASH 1	file.ex
100644 HASH 2	file.ex
100644 HASH 3	file.ex
```

---

# 21. Obtener versiones del archivo

Base:

```bash
git show :1:path/to/file
```

Ours:

```bash
git show :2:path/to/file
```

Theirs:

```bash
git show :3:path/to/file
```

Estas versiones deben utilizarse cuando sea necesario mostrar contexto adicional.

---

# 22. No utilizar `ours` y `theirs` directamente en la UI

La UI debe preferir:

```text
CURRENT
INCOMING
```

pero internamente puede trabajar con:

```text
ours
theirs
```

La relación entre ambos dependerá de la operación Git actual.

---

# 23. Detectar operación Git

La aplicación debe determinar si el usuario está actualmente realizando:

```text
merge
rebase
cherry-pick
revert
```

Orden aproximado de detección:

```text
rebase
cherry-pick
revert
merge
```

debido a que algunos estados pueden coexistir parcialmente.

---

# 24. Merge

Detectar mediante:

```bash
git rev-parse -q --verify MERGE_HEAD
```

Si existe:

```text
operation = MERGE
```

---

# 25. Cherry-pick

Detectar:

```bash
git rev-parse -q --verify CHERRY_PICK_HEAD
```

---

# 26. Revert

Detectar:

```bash
git rev-parse -q --verify REVERT_HEAD
```

---

# 27. Rebase

Utilizar `git rev-parse --git-path` para evitar asumir directamente rutas dentro de `.git`.

Por ejemplo:

```bash
git rev-parse --git-path rebase-merge
```

y:

```bash
git rev-parse --git-path rebase-apply
```

---

# 28. Regla crítica sobre Current e Incoming

Durante un merge normal:

```text
CURRENT ≈ ours
INCOMING ≈ theirs
```

Sin embargo, durante un rebase la semántica puede resultar diferente a la expectativa del usuario.

Por lo tanto:

> Nunca asumir que `ours == current branch` en todos los contextos.

La capa `GitOperation` debe determinar las etiquetas mostradas.

---

# 29. UI contextual

Ejemplo durante merge:

```text
Operation: MERGE

CURRENT
feature/my-work

INCOMING
develop
```

Durante rebase:

```text
Operation: REBASE

CURRENT
Rebased base

INCOMING
Commit being applied
```

Debe favorecerse claridad sobre terminología Git estricta.

---

# 30. Modelo de archivo conflictivo

```python
from dataclasses import dataclass


@dataclass
class ConflictedFile:
    path: str
    conflicts: list["Conflict"]
    resolved: bool = False
```

---

# 31. Modelo de conflicto

```python
from dataclasses import dataclass


@dataclass
class Conflict:
    index: int

    current: list[str]
    incoming: list[str]

    base: list[str] | None

    start_line: int
    end_line: int

    resolution: "Resolution | None" = None
```

---

# 32. Resoluciones

```python
from enum import Enum


class Resolution(Enum):
    CURRENT = "current"
    INCOMING = "incoming"
    BOTH_CURRENT_FIRST = "both_current_first"
    BOTH_INCOMING_FIRST = "both_incoming_first"
    MANUAL = "manual"
```

---

# 33. Conflict markers básicos

Formato estándar:

```text
<<<<<<< HEAD
current
=======
incoming
>>>>>>> feature
```

---

# 34. `diff3`

También debe considerarse:

```text
<<<<<<< HEAD
current
||||||| base
base
=======
incoming
>>>>>>> feature
```

---

# 35. `zdiff3`

Git también soporta:

```text
merge.conflictStyle=zdiff3
```

La primera versión puede limitar el soporte completo, pero la arquitectura del parser no debe asumir exclusivamente el formato estándar.

---

# 36. Parser

El parser debe transformar:

```text
before()

<<<<<<< HEAD
foo()
bar()
=======
foo()
baz()
>>>>>>> feature

after()
```

en una representación estructurada.

Ejemplo:

```python
Conflict(
    current=[
        "foo()\n",
        "bar()\n",
    ],
    incoming=[
        "foo()\n",
        "baz()\n",
    ],
)
```

---

# 37. Preservación exacta

El parser debe preservar:

* saltos de línea
* espacios
* tabs
* líneas vacías
* encoding cuando sea razonablemente posible

La resolución no debe reformatear automáticamente el archivo.

---

# 38. Regla: nunca modificar partes ajenas al conflicto

Si un archivo contiene:

```text
A

<<<<<<<
B
=======
C
>>>>>>>

D
```

resolver ese conflicto solo puede modificar:

```text
<<<<<<<
B
=======
C
>>>>>>>
```

Las líneas:

```text
A
D
```

deben permanecer byte-a-byte equivalentes siempre que sea posible.

---

# 39. Current

Para:

```text
<<<<<<< HEAD
A
=======
B
>>>>>>> feature
```

seleccionar:

```text
Current
```

produce:

```text
A
```

---

# 40. Incoming

Produce:

```text
B
```

---

# 41. Both — Current First

Produce:

```text
A
B
```

---

# 42. Both — Incoming First

Produce:

```text
B
A
```

---

# 43. Regla: no deduplicar

Dado:

```text
Current:
foo()
bar()

Incoming:
foo()
baz()
```

`Both Current First` debe generar:

```text
foo()
bar()
foo()
baz()
```

No:

```text
foo()
bar()
baz()
```

---

# 44. Navegación de conflictos

Cada archivo puede contener:

```text
Conflict 1 / 4
Conflict 2 / 4
Conflict 3 / 4
Conflict 4 / 4
```

Debe poder utilizarse:

```text
Next
Previous
```

sin necesidad de resolver inmediatamente el conflicto actual.

---

# 45. Estado de resolución

Cada conflicto puede encontrarse en:

```text
UNRESOLVED
RESOLVED
MANUAL
```

El archivo solamente puede considerarse completamente resuelto cuando:

```text
unresolved_conflicts == 0
```

---

# 46. Resolución en memoria

Mientras el usuario trabaja sobre un archivo, las decisiones deberían mantenerse inicialmente en memoria.

Ejemplo:

```text
Conflict #1 → CURRENT
Conflict #2 → INCOMING
Conflict #3 → BOTH_CURRENT_FIRST
```

No escribir el archivo necesariamente después de cada click.

---

# 47. Guardar

Una acción explícita:

```text
Save
```

reconstruirá el archivo utilizando todas las resoluciones seleccionadas.

---

# 48. Escritura segura

No escribir directamente de forma destructiva si puede evitarse.

Flujo recomendado:

```text
1. generar contenido
2. escribir archivo temporal
3. validar escritura
4. reemplazar archivo original
```

Por ejemplo utilizando:

```python
tempfile.NamedTemporaryFile()
```

y finalmente:

```python
Path.replace()
```

---

# 49. Backup interno

Antes de la primera escritura de un archivo durante una sesión se puede mantener una copia temporal para implementar:

```text
Undo file
```

No es necesario crear archivos `.bak` dentro del repositorio.

---

# 50. Undo

Debe existir inicialmente:

```text
Undo last resolution
```

Posteriormente:

```text
Reset conflict
Reset file
```

---

# 51. Mark as resolved

Después de guardar:

```bash
git add -- path/to/file
```

Esto será la acción:

```text
Mark as resolved
```

---

# 52. Regla: no realizar commit

La herramienta nunca debe ejecutar automáticamente:

```bash
git commit
git merge --continue
git rebase --continue
git cherry-pick --continue
```

El usuario mantiene control del flujo Git.

---

# 53. Regla: `git add` debe ser explícito

Resolver visualmente un archivo y marcarlo como resuelto son operaciones distintas:

```text
Save
Mark resolved
```

Aunque posteriormente puede existir una opción configurable:

```text
Automatically stage resolved files
```

debe permanecer deshabilitada por defecto inicialmente.

---

# 54. Validar antes de `git add`

Antes de marcar como resuelto:

1. volver a leer el archivo;
2. comprobar que ya no contiene conflictos conocidos;
3. confirmar que Git todavía reporta el archivo como unmerged;
4. ejecutar:

```bash
git add -- path
```

---

# 55. Verificación posterior

Después:

```bash
git diff --name-only --diff-filter=U
```

Si el archivo sigue apareciendo:

```text
Mark as resolved failed.
```

No asumir éxito únicamente porque `git add` devolvió `0`.

---

# 56. UI principal

Diseño aproximado:

```text
┌─ Repository ──────────────────────────────────────────┐
│ lynxwebex                                             │
│ Branch: feature/example                               │
│ Operation: MERGE                                      │
└───────────────────────────────────────────────────────┘

┌─ Conflicted files ──────────┬─ Progress ─────────────┐
│ > lib/users.ex              │ Files: 1 / 3          │
│   lib/accounts.ex           │ Conflicts: 3 / 8      │
│   config/runtime.exs        │                        │
└─────────────────────────────┴────────────────────────┘
```

---

# 57. Conflict viewer

```text
Conflict 2 / 4

┌─ CURRENT ───────────────────┬─ INCOMING ──────────────┐
│                            │                         │
│ user.status                │ user.account.status     │
│                            │                         │
└────────────────────────────┴─────────────────────────┘
```

---

# 58. Acciones

```text
[C] Current
[I] Incoming
[B] Both — Current First
[Shift+B] Both — Incoming First
[E] Edit manually

[N] Next
[P] Previous

[U] Undo
[S] Save
[R] Mark resolved
```

Los bindings reales deben revisarse para evitar combinaciones incómodas.

---

# 59. Keyboard-first

La herramienta estará orientada a desarrolladores.

Todas las operaciones principales deben poder realizarse sin mouse.

Mouse puede soportarse como complemento.

---

# 60. Syntax highlighting

No es requisito del MVP.

Primera versión:

```text
plain text + diff highlighting
```

Posteriormente puede detectarse la extensión:

```text
.ex
.exs
.py
.js
.ts
.dart
.json
.yaml
```

y aplicar syntax highlighting.

---

# 61. Edición manual

Debe existir:

```text
Edit manually
```

Dos estrategias posibles.

## Opción A

Editor interno sencillo.

## Opción B

Abrir editor externo.

La opción B debe priorizarse inicialmente.

---

# 62. Detección de editor

Orden:

```text
$GIT_EDITOR
$VISUAL
$EDITOR
```

Y posteriormente configuraciones explícitas de la aplicación.

Ejemplo:

```text
zed
nvim
vim
code
```

---

# 63. Integración con Zed

Permitir:

```text
Open in Zed
```

ejecutando:

```bash
zed path/to/file
```

Opcionalmente con línea:

```bash
zed path/to/file:123
```

si Zed soporta el formato correspondiente.

---

# 64. Refrescar después de edición externa

Cuando el usuario regrese a la TUI:

1. releer archivo;
2. volver a parsear conflictos;
3. actualizar estado;
4. no reutilizar offsets anteriores.

Los números de línea pueden haber cambiado.

---

# 65. Progreso global

Mostrar:

```text
Files
2 / 5 resolved

Conflicts
8 / 13 resolved
```

---

# 66. Recalcular estado

Git es la autoridad.

Después de:

```text
git add
external edit
file reset
```

debe refrescarse:

```bash
git diff --name-only --diff-filter=U
```

---

# 67. Conflictos binarios

No intentar parsear contenido binario.

Mostrar:

```text
Binary conflict

Use Current
Use Incoming
```

No mostrar:

```text
Both
```

salvo que exista una justificación técnica específica.

---

# 68. Detectar archivos binarios

Puede utilizarse información de Git y/o análisis del archivo.

La detección no debe depender únicamente de la extensión.

---

# 69. Modify/Delete conflict

Ejemplo:

```text
deleted by us
modified by them
```

La UI debe representar la decisión real:

```text
Keep deleted
Keep modified
```

No reutilizar ciegamente:

```text
Current
Incoming
```

si esas etiquetas ocultan el significado real.

---

# 70. Delete/Delete

No requiere merge de contenido.

La aplicación debe identificar que ambas versiones eliminaron el archivo y presentar una acción coherente.

---

# 71. Add/Add

Ambas ramas añadieron un archivo con el mismo path.

Puede utilizarse la misma vista:

```text
CURRENT
INCOMING
```

si ambas versiones contienen texto.

---

# 72. Rename/Rename

Ejemplo:

```text
file.txt

branch A → foo.txt
branch B → bar.txt
```

Este caso requiere una pantalla especializada.

No debe forzarse dentro del parser de bloques de texto.

---

# 73. Tipos de conflicto

Crear una abstracción:

```python
class ConflictType(Enum):
    CONTENT = "content"
    BINARY = "binary"
    MODIFY_DELETE = "modify_delete"
    ADD_ADD = "add_add"
    RENAME_RENAME = "rename_rename"
    OTHER = "other"
```

---

# 74. Unsupported conflicts

Si aparece un conflicto aún no soportado:

```text
Unsupported conflict type.
```

La aplicación debe permitir:

```text
Open in editor
```

pero no improvisar una resolución automática.

---

# 75. Regla de seguridad

Ante incertidumbre:

> No modificar el repositorio.

Es mejor informar:

```text
This conflict type is not supported yet.
```

que aplicar una resolución incorrecta.

---

# 76. Estado externo

El repositorio puede cambiar mientras la TUI está abierta.

Por ejemplo:

```bash
git add
git checkout
git restore
```

desde otra terminal.

Antes de operaciones destructivas debe verificarse que el estado esperado siga siendo válido.

---

# 77. Modificaciones concurrentes

Guardar el hash o metadata del contenido leído inicialmente.

Antes de sobrescribir:

```text
original_hash == current_hash
```

Si cambió:

```text
File changed outside gconflict.
Reload before saving.
```

No sobrescribir silenciosamente.

---

# 78. Symlinks

No seguir symlinks indiscriminadamente.

La herramienta debe respetar cómo Git representa ese path.

---

# 79. Encoding

UTF-8 será el caso principal.

Pero no debe asumirse silenciosamente que todos los archivos son UTF-8.

Ante errores de decoding:

```text
Unsupported text encoding.
```

y ofrecer resolución externa.

---

# 80. Newline preservation

Preservar:

```text
LF
CRLF
```

No convertir todo automáticamente a `LF`.

---

# 81. File permissions

Al reemplazar archivos temporalmente debe preservarse el modo original:

```text
chmod
executable bit
```

especialmente para scripts versionados.

---

# 82. Logging

Agregar logging interno.

Ejemplo:

```text
~/.local/state/gconflict/gconflict.log
```

No imprimir detalles internos en la UI salvo errores relevantes.

---

# 83. Logs sensibles

No almacenar contenido completo de archivos por defecto.

Los logs deben contener principalmente:

```text
repository
path
operation
error
command
return code
```

No código fuente completo.

---

# 84. Configuración

Posteriormente:

```text
~/.config/gconflict/config.toml
```

Ejemplo:

```toml
editor = "zed"

auto_stage = false

show_base = false

conflict_style = "side-by-side"
```

No es necesaria en la primera iteración.

---

# 85. CLI

Inicial:

```bash
gconflict
```

Posteriormente:

```bash
gconflict .
```

```bash
gconflict path/to/file
```

```bash
gconflict --no-ui
```

```bash
gconflict --version
```

---

# 86. Exit codes

Definir comportamiento predecible.

```text
0 = ejecución correcta
1 = error general
2 = no Git repository
3 = unsupported repository state
4 = invalid arguments
```

---

# 87. Cuando no existen conflictos

Mostrar:

```text
No unresolved Git conflicts found.
```

y terminar con:

```text
exit 0
```

No debe considerarse error.

---

# 88. Tests

La lógica Git y la lógica de resolución deben probarse independientemente de Textual.

Prioridad:

```text
conflict parser
resolution engine
Git operation detection
repository state
```

---

# 89. Tests unitarios del parser

Casos mínimos:

```text
single conflict
multiple conflicts
empty current
empty incoming
adjacent conflicts
conflict at beginning
conflict at EOF
blank lines
indentation
diff3
zdiff3
```

---

# 90. Tests de resoluciones

Validar:

```text
Current
Incoming
Both Current First
Both Incoming First
```

para cada bloque.

---

# 91. Tests negativos

Ejemplos:

```text
missing separator
missing closing marker
invalid marker ordering
nested malformed markers
```

El parser no debe producir silenciosamente contenido corrupto.

---

# 92. Tests reales con Git

Crear repositorios temporales mediante:

```python
tempfile.TemporaryDirectory()
```

y ejecutar:

```bash
git init
```

Dentro de los tests.

---

# 93. Escenarios de integración

Crear automáticamente:

```text
main
feature
```

Modificar el mismo archivo en ambas ramas y ejecutar:

```bash
git merge feature
```

Después verificar que:

```bash
gconflict
```

detectaría correctamente el conflicto.

---

# 94. Matriz mínima de integración

Probar:

```text
merge + content conflict
rebase + content conflict
cherry-pick + content conflict
modify/delete
add/add
binary conflict
```

---

# 95. Worktrees

Debe existir al menos un test de integración con:

```bash
git worktree add
```

para comprobar que no existe dependencia incorrecta de:

```text
./.git/
```

---

# 96. Regla sobre comandos Git

Cada comando ejecutado debe:

* utilizar lista de argumentos;
* establecer correctamente el working directory;
* no usar `shell=True`;
* capturar stdout;
* capturar stderr;
* manejar códigos distintos de cero.

---

# 97. GitRepository

Crear una abstracción aproximadamente así:

```python
class GitRepository:
    def root(self) -> Path:
        ...

    def current_branch(self) -> str | None:
        ...

    def operation(self) -> GitOperation:
        ...

    def conflicted_files(self) -> list[ConflictedFile]:
        ...

    def stage_file(self, path: Path) -> None:
        ...
```

---

# 98. RepositoryService

La UI no debe llamar directamente:

```python
GitClient.run(...)
```

Debe utilizar:

```python
RepositoryService
```

Esto simplifica tests y desacopla Textual.

---

# 99. ConflictService

Responsabilidades:

```text
load file
parse conflicts
apply resolution
undo resolution
save
reload
```

---

# 100. MVP — fase 1

Primera versión funcional.

## Alcance

* validar repository;
* detectar root;
* detectar operación Git;
* listar archivos conflictivos;
* abrir archivo;
* detectar conflictos de contenido estándar;
* mostrar Current/Incoming;
* resolver:

  * Current
  * Incoming
  * Both Current First
  * Both Incoming First
* Previous/Next;
* Save;
* Mark resolved;
* progreso.

---

# 101. MVP — exclusiones

No implementar aún:

* inteligencia semántica;
* resolución automática;
* syntax-aware merging;
* GitHub;
* GitLab;
* PRs;
* commits;
* merge continue;
* rebase continue;
* branch management;
* commit history;
* staging general;
* diff de archivos sin conflicto.

Esto evita convertir el proyecto en otro cliente Git.

---

# 102. Fase 2

Agregar:

* diff3;
* zdiff3;
* Base view;
* undo;
* reset conflict;
* reset file;
* editor externo;
* Zed integration;
* detección de modificaciones externas;
* keyboard shortcuts completos.

---

# 103. Fase 3

Conflictos especiales:

* binary;
* modify/delete;
* delete/modify;
* add/add;
* rename/rename;
* file mode conflicts.

---

# 104. Fase 4

Mejoras UX:

* syntax highlighting;
* configurable keybindings;
* search;
* jump to unresolved;
* mouse support;
* configurable layout;
* scroll sincronizado;
* line numbers;
* word-level diff.

---

# 105. Fase 5

Distribución.

Opciones:

```bash
pipx install gconflict
```

o:

```bash
uv tool install gconflict
```

También puede publicarse posteriormente en PyPI.

---

# 106. Ejecución esperada

Desde cualquier carpeta dentro del repo:

```bash
gconflict
```

Ejemplo:

```text
Repository: lynxwebex
Branch: feature/example
Operation: merge

3 unresolved files
8 unresolved conflicts
```

---

# 107. Flujo del usuario

```text
gconflict
    ↓
Validate repository
    ↓
Detect Git operation
    ↓
Load conflicted files
    ↓
Select file
    ↓
Select conflict
    ↓
Resolve
    ↓
Next conflict
    ↓
Save
    ↓
Mark resolved
    ↓
Next file
```

---

# 108. Flujo posterior

Cuando todos los archivos estén resueltos:

```text
All conflicts resolved.

Files staged:
  lib/users.ex
  lib/accounts.ex
```

La aplicación termina ahí.

No ejecuta automáticamente:

```bash
git merge --continue
```

o:

```bash
git rebase --continue
```

---

# 109. Reglas de negocio

## RN-001 — Repositorio requerido

La aplicación solo puede ejecutarse dentro de un repositorio Git válido.

---

## RN-002 — Git es la fuente de verdad

El estado de los conflictos debe obtenerse mediante Git.

---

## RN-003 — Solo conflictos reales

Solo mostrar archivos reportados por Git como `unmerged`.

---

## RN-004 — No commits automáticos

La aplicación nunca debe crear commits.

---

## RN-005 — No continuar operaciones automáticamente

No ejecutar automáticamente:

```text
merge --continue
rebase --continue
cherry-pick --continue
revert --continue
```

---

## RN-006 — Resolución explícita

Cada conflicto debe requerir una decisión del usuario.

---

## RN-007 — Sin merge inteligente

No deduplicar, reordenar ni reinterpretar código automáticamente.

---

## RN-008 — Current

Seleccionar Current conserva exactamente el contenido Current.

---

## RN-009 — Incoming

Seleccionar Incoming conserva exactamente el contenido Incoming.

---

## RN-010 — Both Current First

Debe concatenar:

```text
Current
Incoming
```

en ese orden.

---

## RN-011 — Both Incoming First

Debe concatenar:

```text
Incoming
Current
```

en ese orden.

---

## RN-012 — Preservación de contenido

Resolver un conflicto no debe modificar contenido fuera del bloque correspondiente.

---

## RN-013 — Archivo completo

Un archivo solo está listo para staging cuando todos sus conflictos de contenido estén resueltos.

---

## RN-014 — Stage explícito

Resolver y guardar un archivo no implica automáticamente ejecutar `git add`.

---

## RN-015 — Git add

La acción:

```text
Mark resolved
```

ejecutará:

```bash
git add -- <file>
```

---

## RN-016 — Verificación posterior

Después de staging debe verificarse nuevamente el estado mediante Git.

---

## RN-017 — Operación contextual

Current e Incoming deben interpretarse considerando si existe:

```text
merge
rebase
cherry-pick
revert
```

---

## RN-018 — Conflictos desconocidos

Un conflicto no soportado nunca debe resolverse automáticamente.

---

## RN-019 — Binarios

Los archivos binarios no deben procesarse mediante el parser textual.

---

## RN-020 — Estado externo

Si un archivo cambia fuera de la aplicación antes de guardar, no debe sobrescribirse silenciosamente.

---

## RN-021 — Worktrees

La aplicación debe funcionar correctamente dentro de Git worktrees.

---

## RN-022 — Paths seguros

Todos los comandos Git que reciben paths deben utilizar:

```text
--
```

antes del path cuando corresponda.

Ejemplo:

```bash
git add -- path
```

---

## RN-023 — Sin shell

Nunca utilizar:

```python
shell=True
```

para ejecutar Git.

---

## RN-024 — Fallo seguro

Si no puede determinarse de forma confiable cómo manipular un conflicto, no debe modificarse el archivo.

---

## RN-025 — Usuario mantiene control de Git

La herramienta facilita la resolución de conflictos, pero no decide:

* cuándo continuar;
* cuándo abortar;
* cuándo hacer commit;
* cuándo hacer push.

---

# 110. Criterios de aceptación del MVP

El MVP puede considerarse terminado cuando se cumpla todo lo siguiente:

* [ ] `gconflict` funciona desde cualquier directorio dentro de un repo.
* [ ] Detecta correctamente que no está dentro de un repo.
* [ ] Lista todos los archivos con conflictos.
* [ ] Permite seleccionar un archivo.
* [ ] Detecta múltiples conflictos dentro del mismo archivo.
* [ ] Muestra Current.
* [ ] Muestra Incoming.
* [ ] Permite Current.
* [ ] Permite Incoming.
* [ ] Permite Both Current First.
* [ ] Permite Both Incoming First.
* [ ] Permite navegar Next/Previous.
* [ ] Muestra conflictos resueltos y pendientes.
* [ ] Guarda correctamente el archivo.
* [ ] No modifica contenido ajeno al conflicto.
* [ ] Puede marcar un archivo como resuelto.
* [ ] Utiliza `git add -- <path>`.
* [ ] Refresca la lista después del staging.
* [ ] Detecta cuando todos los archivos están resueltos.
* [ ] No crea commits.
* [ ] No continúa merges/rebases automáticamente.
* [ ] Funciona dentro de worktrees.
* [ ] Tiene tests unitarios del parser.
* [ ] Tiene tests unitarios del resolver.
* [ ] Tiene tests de integración con repositorios Git temporales.

---

# 111. Orden recomendado de implementación

## Iteración 1 — Infraestructura

Implementar:

```text
pyproject.toml
GitClient
GitRepository
repository detection
repository root
```

---

## Iteración 2 — Git state

Implementar:

```text
operation detection
conflicted files
ls-files -u
stage information
```

---

## Iteración 3 — Conflict engine

Implementar:

```text
Conflict model
parser
Current
Incoming
Both Current First
Both Incoming First
```

Sin UI todavía.

---

## Iteración 4 — Tests del engine

Crear tests exhaustivos antes de integrar Textual.

El resolver debe poder utilizarse independientemente de la UI.

---

## Iteración 5 — Textual

Crear:

```text
MainScreen
FileList
ConflictViewer
Actions
Progress
```

---

## Iteración 6 — Persistence

Agregar:

```text
Save
safe writes
external modification detection
```

---

## Iteración 7 — Git staging

Agregar:

```text
Mark resolved
refresh repository
```

---

## Iteración 8 — UX

Agregar:

```text
keyboard bindings
scroll
error dialogs
status bar
```

---

## Iteración 9 — Zed

Agregar:

```text
Open in editor
Open in Zed
reload after external edit
```

---

## Iteración 10 — Conflictos especiales

Agregar individualmente:

```text
diff3
zdiff3
binary
modify/delete
add/add
rename
```

Cada tipo debe incorporarse con sus respectivos tests.

---

# 112. Objetivo arquitectónico final

```text
                          Git Repository
                                │
                                ▼
                     ┌─────────────────────┐
                     │      GitClient      │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   GitRepository     │
                     │                     │
                     │ status              │
                     │ operation           │
                     │ index stages        │
                     │ conflicted files    │
                     │ stage               │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   ConflictService   │
                     │                     │
                     │ parse               │
                     │ resolve             │
                     │ undo                │
                     │ save                │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │     Textual UI      │
                     │                     │
                     │ file list           │
                     │ diff viewer         │
                     │ actions             │
                     │ progress            │
                     └─────────────────────┘
```

---

# 113. Definición de éxito

El proyecto será exitoso si permite que el flujo habitual:

```text
Zed
↓
Git conflict
↓
manual marker editing
↓
git add
```

sea reemplazado por:

```text
Zed
↓
Git conflict
↓
gconflict
↓
resolve Current / Incoming / Both
↓
mark resolved
↓
return to Zed
```

sin intentar reemplazar:

```text
Zed
Git
terminal
GitHub
```

La herramienta debe mantenerse deliberadamente pequeña y especializada:

> **Un resolvedor de conflictos Git externo, keyboard-first, confiable y construido encima del comportamiento real de Git.**
