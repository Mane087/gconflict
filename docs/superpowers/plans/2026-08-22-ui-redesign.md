# Rediseño de la UI de gconflict — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la UI actual de `GConflictApp` (una `ListView` y tres `Label`) por la dirección A del rediseño: tabs de archivos, sidebar con progreso, editor a dos paneles con vista previa del resultado, y un panel de acciones agrupado por ámbito.

**Architecture:** Todo el trabajo nuevo vive en un paquete `src/gconflict/ui/` de widgets tontos —reciben datos ya calculados y no saben nada de Git ni del sistema de archivos—, más tres métodos nuevos en `ConflictService` y dos en `GitRepository` que producen esos datos. `app.py` queda reducido a cableado: traduce eventos de teclado a llamadas al servicio y reparte el resultado entre widgets. La dirección de dependencias del proyecto no cambia: `ui → app → services → {git, conflicts, filesystem} → models`.

**Tech Stack:** Python 3.13+, Textual 8.x, pytest + pytest-asyncio, Git CLI vía `subprocess` sin shell.

**Spec:**
- Diseño visual: canvas publicado en `https://claude.ai/code/artifact/a1773ccc-fad9-4450-80cb-66dd012f1cf1` (página «Diseño»: Pantalla principal, Sistema visual, Panel de opciones, Estados).
- Reglas de negocio: `plan.md` en la raíz del repositorio, secciones 22, 28, 45–55, 56–66 y RN-001…RN-025. **Este plan no modifica `plan.md`.**

## Global Constraints

Copiadas literalmente de `plan.md` y del código existente. Aplican a **todas** las tareas:

- Python `>=3.13`. El venv del proyecto es `.venv/` (Python 3.14); usar `.venv/bin/python` explícitamente, no está activado.
- Dependencia de runtime única: `textual>=1.0`. No añadir dependencias de runtime nuevas en este plan.
- Nunca `shell=True` (RN-023). Todo comando Git se ejecuta a través de `GitClient.run(["..."], cwd=...)`.
- Todo comando Git que reciba un path usa `--` antes del path (RN-022).
- Ninguna capa fuera de `src/gconflict/git/` ejecuta `subprocess` (plan.md §13).
- La UI dice `CURRENT` / `INCOMING`, nunca `ours` / `theirs` como etiqueta principal (plan.md §22).
- Nunca asumir que `ours == rama actual`: las etiquetas las decide `GitOperation` (plan.md §28, RN-017).
- Nada muta el repositorio sin acción explícita del usuario: `Save` (disco) y `Mark resolved` (`git add`) son acciones separadas (RN-014, RN-015).
- La aplicación nunca hace commit ni continúa merges/rebases (RN-004, RN-005).
- Resolver un conflicto no modifica ni un byte fuera de su bloque (RN-012).
- Nunca deduplicar, reordenar ni reinterpretar contenido (RN-007).
- Ante incertidumbre, no modificar el archivo (RN-024).
- Códigos de salida existentes, no cambian: `0` correcto o sin conflictos, `2` no es repositorio Git, `4` argumentos inválidos.
- Cadenas de la interfaz en inglés (`CURRENT`, `INCOMING`, `Save`, `Mark resolved`), igual que hoy en `app.py`. Los comentarios y docstrings también en inglés. Este documento está en español porque `plan.md` y `README.md` lo están.
- Docstrings de una línea, imperativas. Comentarios escasos, y solo para explicar *por qué*.
- Los tests espejan el árbol de fuentes: `src/gconflict/ui/widgets/status_line.py` ↔ `tests/ui/widgets/test_status_line.py`.

## Antes de empezar

**Este directorio no es un repositorio Git.** `git rev-parse --show-toplevel` falla desde la raíz del proyecto. Los pasos «Commit» de cada tarea asumen que existe uno.

Decisión del usuario antes de la Tarea 1, una de dos:

```bash
# Opción A — versionar el proyecto (necesario para los pasos de commit)
cd "/Users/mane_alaniz/Documents/Visual Studio Code/git-merger"
git init
git add .
git commit -m "chore: initial commit before UI redesign"
```

**Opción B** — no versionar todavía: saltarse el paso «Commit» de todas las tareas. El resto del plan funciona igual.

## Paleta del sistema visual

Valores exactos del artboard «Sistema visual». Toda tarea que necesite un color lo toma de aquí, nunca inventa uno nuevo.

| Rol | Hex | Uso |
|---|---|---|
| `surface-0` | `#0b0d12` | fondo de la pantalla |
| `surface-1` | `#10131a` | sidebar, paneles |
| `surface-2` | `#12151d` | header, barras |
| `surface-3` | `#1c202b` | fila seleccionada, tab activa |
| `line` | `#272c39` | bordes |
| `text` | `#d6dae3` | primario |
| `text-2` | `#a4abba` | secundario |
| `text-3` | `#79808f` | metadatos, rutas, ramas |
| `text-4` | `#4d5462` | hints de teclado |
| `text-5` | `#343b48` | código de contexto |
| `current` | `#e8a44c` | CURRENT, foco activo |
| `current-bg` | `#241c10` | fondo de línea CURRENT |
| `current-line` | `#8a6b34` | número de línea CURRENT |
| `current-text` | `#f0d3a4` | código CURRENT |
| `incoming` | `#4ca8e8` | INCOMING |
| `incoming-bg` | `#10202c` | fondo de línea INCOMING |
| `incoming-line` | `#35708f` | número de línea INCOMING |
| `incoming-text` | `#a8d6f5` | código INCOMING |
| `ok` | `#6fbf73` | resuelto, guardado, staged |
| `danger` | `#d9645f` | bloqueado, no soportado |

Glifos, legibles sin color: `◆` CURRENT (relleno), `◇` INCOMING (hueco), `●` archivo pendiente, `✓` resuelto, `○` sin tocar, `⚠` no soportado.

## Estructura de archivos

**Se crean:**

| Archivo | Responsabilidad |
|---|---|
| `src/gconflict/models/repository_context.py` | `RepositoryContext`: raíz, nombre, rama, operación y etiquetas de los dos lados. |
| `src/gconflict/models/file_progress.py` | `FileProgress`: un descriptor de archivo más su número de conflictos de contenido. |
| `src/gconflict/ui/__init__.py` | Paquete de presentación. |
| `src/gconflict/ui/tokens.py` | `TOKENS` (la única fuente de los colores) y `TokenApp`, que los publica como variables CSS. |
| `src/gconflict/ui/app.tcss` | El layout de la pantalla y las clases utilitarias. |
| `src/gconflict/ui/widgets/__init__.py` | Reexporta los widgets. |
| `src/gconflict/ui/widgets/status_line.py` | `StatusLine`: la línea de estado de cuatro variantes. |
| `src/gconflict/ui/widgets/action_bar.py` | `ActionBar` y `Action`: acciones agrupadas por ámbito con motivo de bloqueo. |
| `src/gconflict/ui/widgets/file_tabs.py` | `FileTabs` y `TabEntry`: tabs de archivo con contador. |
| `src/gconflict/ui/widgets/file_sidebar.py` | `FileSidebar` y `SidebarEntry`: lista de archivos y progreso global. |
| `src/gconflict/ui/widgets/conflict_panes.py` | `ConflictPanes`: los dos paneles CURRENT / INCOMING. |
| `src/gconflict/ui/widgets/result_pane.py` | `ResultPane`: vista previa de lo que se escribirá. |
| `src/gconflict/ui/widgets/repository_header.py` | `RepositoryHeader`: nombre, operación y rama. |
| `tests/ui/widgets/test_*.py` | Un archivo de test por widget. |
| `tests/models/test_repository_context.py` | Etiquetas por operación. |

**Se modifican:**

| Archivo | Cambio |
|---|---|
| `pyproject.toml` | Config de pytest, `pytest-asyncio` en `dev`, package-data del `.tcss`. |
| `src/gconflict/git/repository.py` | Corregir `stage`; añadir `current_branch` e `incoming_ref`. |
| `src/gconflict/services/conflict_service.py` | Añadir `context`, `preview_resolution`, `file_progress`. |
| `src/gconflict/app.py` | Reescritura de `compose` y del cableado; `GConflictApp` pasa a heredar de `TokenApp`. `main()` no cambia. |
| `tests/git/test_repository.py` | Tests de las tres cosas de arriba. |
| `tests/services/test_conflict_service.py` | Tests de los tres métodos nuevos. |
| `tests/test_app.py` | Adaptar a la nueva composición. |

**Fuera de alcance de este plan** (no lo intentes, no está pedido): syntax highlighting, resaltado a nivel de carácter, paleta de comandos `ctrl+p`, `diff3`/`zdiff3`, conflictos binarios, `modify/delete`, `rename/rename`, configuración en `~/.config`, logging.

---

## Fase 0 — Desbloquear

### Task 1: Configurar pytest para tests asíncronos

Hoy `.venv/bin/python -m pytest -q` reporta `25 failed, 92 passed`: todos los tests `async def` de `tests/test_app.py` fallan con «async def functions are not natively supported». `pytest-asyncio` está instalado en el venv pero no está declarado en las dependencias de desarrollo ni configurado. Cada tarea de UI de este plan añade tests asíncronos, así que esto va primero.

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nada.
- Produces: `.venv/bin/python -m pytest` corre la suite completa sin flags extra. Todas las tareas siguientes dependen de ello.

- [ ] **Step 1: Confirmar el fallo actual**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: `25 failed, 92 passed`

- [ ] **Step 2: Confirmar que la causa es la configuración, no el código**

Run: `.venv/bin/python -m pytest -q --asyncio-mode=auto 2>&1 | tail -3`
Expected: `117 passed`

- [ ] **Step 3: Declarar la dependencia y la configuración**

En `pyproject.toml`, sustituir el bloque `[project.optional-dependencies]` por:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov>=6",
    "pytest-asyncio>=1",
]
```

Y añadir al final del archivo:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 4: Verificar que ahora pasa sin flags**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: `117 passed`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "build: configure pytest-asyncio so the Textual tests run"
```

---

### Task 2: Corregir `GitRepository.stage`

`src/gconflict/git/repository.py:79` llama `self.client.run("add", "--", relative_path, cwd=root)`, pero `GitClient.run` (`src/gconflict/git/client.py:22`) recibe **una** secuencia de argumentos. Contra un `GitClient` real esto lanza `TypeError`, así que «Mark resolved» está roto de punta a punta. El test actual (`tests/git/test_repository.py:79`) usa un `Mock()`, que acepta cualquier firma y no lo detecta.

La tarea añade primero un test contra Git real —el que sí lo habría cazado— y después corrige.

**Files:**
- Modify: `src/gconflict/git/repository.py:79`
- Test: `tests/git/test_repository.py:79-93`

**Interfaces:**
- Consumes: `GitClient.run(args: Sequence[str], *, cwd, check) -> GitResult`.
- Produces: `GitRepository.stage(path, cwd=None) -> None` funcionando contra Git real. La Tarea 16 depende de ello.

- [ ] **Step 1: Escribir el test de integración que falla**

Añadir a `tests/git/test_repository.py`:

```python
def test_stage_adds_a_real_file_to_a_real_index(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "file.txt").write_text("content\n", encoding="utf-8")

    GitRepository().stage(Path("nested/file.txt"), cwd=tmp_path)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert staged.stdout.splitlines() == ["nested/file.txt"]
```

- [ ] **Step 2: Ejecutarlo y ver el fallo real**

Run: `.venv/bin/python -m pytest tests/git/test_repository.py::test_stage_adds_a_real_file_to_a_real_index -v`
Expected: FAIL con `TypeError: GitClient.run() takes 2 positional arguments but 4 were given`

- [ ] **Step 3: Corregir la llamada**

En `src/gconflict/git/repository.py`, dentro de `stage`, sustituir:

```python
        self.client.run("add", "--", relative_path, cwd=root)
```

por:

```python
        self.client.run(["add", "--", str(relative_path)], cwd=root)
```

- [ ] **Step 4: Actualizar el test con `Mock` para que exija la firma correcta**

En `tests/git/test_repository.py`, dentro de `test_stage_uses_repository_root_and_relative_path`, sustituir la aserción final por:

```python
    assert client.run.call_args_list == [
        call(["rev-parse", "--show-toplevel"], cwd=tmp_path),
        call(["add", "--", "nested/file.txt"], cwd=root),
    ]
```

- [ ] **Step 5: Verificar los dos tests**

Run: `.venv/bin/python -m pytest tests/git/test_repository.py -q`
Expected: PASS, sin fallos

- [ ] **Step 6: Verificar que no se rompió nada más**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: `118 passed`

- [ ] **Step 7: Commit**

```bash
git add src/gconflict/git/repository.py tests/git/test_repository.py
git commit -m "fix: pass git add arguments to GitClient as a single list"
```

---

## Fase 1 — Los datos que la UI necesita

### Task 3: Leer el nombre de la rama y de la referencia entrante

El header del diseño muestra `MERGE · feature/user-status ← main`. `GitRepository` hoy no sabe leer ninguno de los dos nombres.

Reglas: en HEAD desacoplado `current_branch` devuelve `None`, no revienta. `incoming_ref` cae al SHA corto cuando la referencia no tiene nombre de rama, y devuelve `None` cuando no hay operación en curso.

**Files:**
- Modify: `src/gconflict/git/repository.py`
- Test: `tests/git/test_repository.py`

**Interfaces:**
- Consumes: `GitClient.run`, `GitRepository.operation(cwd) -> GitOperation`.
- Produces:
  - `GitRepository.current_branch(cwd: str | Path | None = None) -> str | None`
  - `GitRepository.incoming_ref(cwd: str | Path | None = None) -> str | None`
  La Tarea 4 consume ambos.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/git/test_repository.py`:

```python
def test_current_branch_returns_the_checked_out_branch() -> None:
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess([], 0, stdout="feature/user-status\n")

    assert GitRepository(client).current_branch("/repo") == "feature/user-status"
    client.run.assert_called_once_with(
        ["symbolic-ref", "--quiet", "--short", "HEAD"], cwd="/repo", check=False
    )


def test_current_branch_returns_none_on_detached_head() -> None:
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess([], 1, stdout="")

    assert GitRepository(client).current_branch() is None


def test_incoming_ref_names_the_merged_branch() -> None:
    repository = GitRepository(Mock())
    repository.operation = Mock(return_value=GitOperation.MERGE)
    repository.client.run.return_value = subprocess.CompletedProcess([], 0, stdout="main\n")

    assert repository.incoming_ref("/repo") == "main"
    repository.client.run.assert_called_once_with(
        ["name-rev", "--name-only", "--refs=refs/heads/*", "MERGE_HEAD"],
        cwd="/repo",
        check=False,
    )


def test_incoming_ref_strips_the_distance_suffix() -> None:
    repository = GitRepository(Mock())
    repository.operation = Mock(return_value=GitOperation.CHERRY_PICK)
    repository.client.run.return_value = subprocess.CompletedProcess([], 0, stdout="main~3\n")

    assert repository.incoming_ref() == "main"


def test_incoming_ref_falls_back_to_the_short_sha() -> None:
    repository = GitRepository(Mock())
    repository.operation = Mock(return_value=GitOperation.REVERT)
    repository.client.run.side_effect = [
        subprocess.CompletedProcess([], 0, stdout="undefined\n"),
        subprocess.CompletedProcess([], 0, stdout="a1b2c3d\n"),
    ]

    assert repository.incoming_ref() == "a1b2c3d"


def test_incoming_ref_reads_the_rebase_head_name(tmp_path: Path) -> None:
    head_name = tmp_path / "head-name"
    head_name.write_text("refs/heads/feature/user-status\n", encoding="utf-8")
    repository = GitRepository(Mock())
    repository.operation = Mock(return_value=GitOperation.REBASE)
    repository.client.run.return_value = subprocess.CompletedProcess(
        [], 0, stdout=f"{head_name}\n"
    )

    assert repository.incoming_ref(tmp_path) == "feature/user-status"


def test_incoming_ref_returns_none_without_an_operation() -> None:
    repository = GitRepository(Mock())
    repository.operation = Mock(return_value=GitOperation.NONE)

    assert repository.incoming_ref() is None
    repository.client.run.assert_not_called()
```

- [ ] **Step 2: Ejecutarlos y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/git/test_repository.py -q -k "current_branch or incoming_ref"`
Expected: FAIL con `AttributeError: 'GitRepository' object has no attribute 'current_branch'`

- [ ] **Step 3: Implementar los dos métodos**

Añadir a la clase `GitRepository` en `src/gconflict/git/repository.py`, justo después de `root`:

```python
    def current_branch(self, cwd: str | Path | None = None) -> str | None:
        """Return the checked-out branch, or None on a detached HEAD."""
        result = self.client.run(
            ["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=cwd, check=False
        )
        return result.stdout.strip() or None

    def incoming_ref(self, cwd: str | Path | None = None) -> str | None:
        """Name the reference being applied by the operation in progress."""
        operation = self.operation(cwd)
        if operation is GitOperation.NONE:
            return None

        if operation is GitOperation.REBASE:
            located = self.client.run(
                ["rev-parse", "--git-path", "rebase-merge/head-name"],
                cwd=cwd,
                check=False,
            )
            head_name = Path(located.stdout.strip())
            if not head_name.is_absolute():
                head_name = (Path.cwd() if cwd is None else Path(cwd)) / head_name
            try:
                reference = head_name.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            return reference.removeprefix("refs/heads/") or None

        marker = {
            GitOperation.MERGE: "MERGE_HEAD",
            GitOperation.CHERRY_PICK: "CHERRY_PICK_HEAD",
            GitOperation.REVERT: "REVERT_HEAD",
        }[operation]

        named = self.client.run(
            ["name-rev", "--name-only", "--refs=refs/heads/*", marker],
            cwd=cwd,
            check=False,
        )
        name = named.stdout.strip()
        if name and name != "undefined":
            # name-rev appends a distance suffix such as "main~3".
            return name.partition("~")[0]

        short = self.client.run(["rev-parse", "--short", marker], cwd=cwd, check=False)
        return short.stdout.strip() or None
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/python -m pytest tests/git/test_repository.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gconflict/git/repository.py tests/git/test_repository.py
git commit -m "feat: read the current branch and the incoming reference name"
```

---

### Task 4: `RepositoryContext` y las etiquetas de los dos lados

`plan.md` §28 y RN-017: nunca asumir que `ours == rama actual`; la capa `GitOperation` decide las etiquetas. Este modelo es donde vive esa decisión, y es una función pura, testeable sin Git.

**Files:**
- Create: `src/gconflict/models/repository_context.py`
- Create: `tests/models/test_repository_context.py`
- Modify: `src/gconflict/services/conflict_service.py`
- Test: `tests/services/test_conflict_service.py`

**Interfaces:**
- Consumes: `GitRepository.root`, `current_branch`, `incoming_ref`, `operation`; `GitOperation`.
- Produces:
  - `RepositoryContext(root: Path, name: str, branch: str | None, operation: GitOperation, current_label: str, incoming_label: str)` — dataclass congelada.
  - `side_labels(operation: GitOperation, branch: str | None, incoming: str | None) -> tuple[str, str]`
  - `ConflictService.context(cwd: str | Path | None = None) -> RepositoryContext`
  Las Tareas 12 y 14 consumen `RepositoryContext`.

- [ ] **Step 1: Escribir el test del modelo**

Crear `tests/models/test_repository_context.py`:

```python
from pathlib import Path

import pytest

from gconflict.git.operation import GitOperation
from gconflict.models.repository_context import RepositoryContext, side_labels


@pytest.mark.parametrize(
    ("operation", "branch", "incoming", "expected"),
    [
        (GitOperation.MERGE, "feature/x", "main", ("ours - feature/x", "theirs - main")),
        (GitOperation.MERGE, None, "main", ("ours - detached HEAD", "theirs - main")),
        (GitOperation.MERGE, "feature/x", None, ("ours - feature/x", "theirs")),
        (
            GitOperation.REBASE,
            "feature/x",
            "feature/x",
            ("rebased base", "commit being applied"),
        ),
        (
            GitOperation.CHERRY_PICK,
            "feature/x",
            "main",
            ("ours - feature/x", "picked commit - main"),
        ),
        (
            GitOperation.REVERT,
            "feature/x",
            "main",
            ("ours - feature/x", "reverted commit - main"),
        ),
        (GitOperation.NONE, "feature/x", None, ("ours - feature/x", "theirs")),
    ],
)
def test_side_labels_depend_on_the_operation(
    operation: GitOperation, branch: str | None, incoming: str | None, expected: tuple[str, str]
) -> None:
    assert side_labels(operation, branch, incoming) == expected


def test_context_names_itself_after_the_repository_root() -> None:
    context = RepositoryContext(
        root=Path("/work/lynxweb"),
        name="lynxweb",
        branch="feature/x",
        operation=GitOperation.MERGE,
        current_label="ours - feature/x",
        incoming_label="theirs - main",
    )

    assert context.name == "lynxweb"
    assert context.operation is GitOperation.MERGE
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/models/test_repository_context.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.models.repository_context'`

- [ ] **Step 3: Escribir el modelo**

Crear `src/gconflict/models/repository_context.py`:

```python
"""Repository state the interface needs to label the two sides of a conflict."""

from dataclasses import dataclass
from pathlib import Path

from gconflict.git.operation import GitOperation


def side_labels(
    operation: GitOperation, branch: str | None, incoming: str | None
) -> tuple[str, str]:
    """Describe the CURRENT and INCOMING sides for the operation in progress."""
    ours = f"ours - {branch}" if branch else "ours - detached HEAD"

    if operation is GitOperation.REBASE:
        # During a rebase "ours" is the base being replayed onto, not the user's branch.
        return "rebased base", "commit being applied"

    if operation is GitOperation.CHERRY_PICK:
        theirs = f"picked commit - {incoming}" if incoming else "picked commit"
    elif operation is GitOperation.REVERT:
        theirs = f"reverted commit - {incoming}" if incoming else "reverted commit"
    else:
        theirs = f"theirs - {incoming}" if incoming else "theirs"

    return ours, theirs


@dataclass(frozen=True)
class RepositoryContext:
    """Everything the header and the conflict panes need about the repository."""

    root: Path
    name: str
    branch: str | None
    operation: GitOperation
    current_label: str
    incoming_label: str
```

- [ ] **Step 4: Verificar que el modelo pasa**

Run: `.venv/bin/python -m pytest tests/models/test_repository_context.py -q`
Expected: PASS

- [ ] **Step 5: Escribir el test del servicio**

Añadir a `tests/services/test_conflict_service.py`:

```python
def test_context_composes_repository_state_into_labels() -> None:
    repository = Mock()
    repository.root.return_value = Path("/work/lynxweb")
    repository.current_branch.return_value = "feature/user-status"
    repository.incoming_ref.return_value = "main"
    repository.operation.return_value = GitOperation.MERGE

    context = ConflictService(repository).context("/work/lynxweb/lib")

    assert context.root == Path("/work/lynxweb")
    assert context.name == "lynxweb"
    assert context.branch == "feature/user-status"
    assert context.operation is GitOperation.MERGE
    assert context.current_label == "ours - feature/user-status"
    assert context.incoming_label == "theirs - main"
    repository.root.assert_called_once_with("/work/lynxweb/lib")
```

Y añadir los imports que falten al principio del archivo:

```python
from gconflict.git.operation import GitOperation
```

- [ ] **Step 6: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/services/test_conflict_service.py -q -k context`
Expected: FAIL con `AttributeError: 'ConflictService' object has no attribute 'context'`

- [ ] **Step 7: Implementar `ConflictService.context`**

Añadir el import en `src/gconflict/services/conflict_service.py`:

```python
from gconflict.models.repository_context import RepositoryContext, side_labels
```

Y el método, después de `root`:

```python
    def context(self, cwd: str | Path | None = None) -> RepositoryContext:
        """Gather the repository state the interface labels its two sides with."""
        root = self.repository.root(cwd)
        branch = self.repository.current_branch(root)
        incoming = self.repository.incoming_ref(root)
        operation = self.repository.operation(root)
        current_label, incoming_label = side_labels(operation, branch, incoming)
        return RepositoryContext(
            root=root,
            name=root.name,
            branch=branch,
            operation=operation,
            current_label=current_label,
            incoming_label=incoming_label,
        )
```

- [ ] **Step 8: Verificar la suite completa**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: PASS, sin fallos

- [ ] **Step 9: Commit**

```bash
git add src/gconflict/models/repository_context.py tests/models/test_repository_context.py src/gconflict/services/conflict_service.py tests/services/test_conflict_service.py
git commit -m "feat: derive CURRENT and INCOMING labels from the Git operation"
```

---

### Task 5: `preview_resolution` — reconstruir sin escribir

El panel `RESULT` del diseño muestra lo que se va a escribir **antes** de guardar. Hoy `ConflictService.resolve_file` reconstruye y escribe en el mismo paso, así que no hay forma de mirar el resultado sin tocar el disco.

Esta tarea separa las dos responsabilidades. `resolve_file` conserva su firma y su comportamiento exactos; solo delega la parte de reconstrucción.

**Files:**
- Modify: `src/gconflict/services/conflict_service.py:73-96`
- Test: `tests/services/test_conflict_service.py`

**Interfaces:**
- Consumes: `resolve_conflict`, `reconstruct_text`, `TextFileSnapshot`.
- Produces: `ConflictService.preview_resolution(snapshot, conflicts, resolutions, manual=None) -> str` — devuelve el texto completo del archivo resuelto y **no toca el disco**. La Tarea 13 lo consume.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/services/test_conflict_service.py`:

```python
def test_preview_resolution_returns_text_without_touching_disk(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text(
        "before\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> main\nafter\n",
        encoding="utf-8",
    )
    service = ConflictService(Mock())
    snapshot, conflicts = service.load_conflicts(path)

    text = service.preview_resolution(snapshot, conflicts, [Resolution.INCOMING])

    assert text == "before\ntheirs\nafter\n"
    assert path.read_text(encoding="utf-8") == (
        "before\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> main\nafter\n"
    )


def test_preview_resolution_rejects_mismatched_lengths(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> main\n", encoding="utf-8")
    service = ConflictService(Mock())
    snapshot, conflicts = service.load_conflicts(path)

    with pytest.raises(ValueError, match="same length"):
        service.preview_resolution(snapshot, conflicts, [])


def test_resolve_file_writes_exactly_what_preview_returned(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text(
        "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> main\n", encoding="utf-8"
    )
    service = ConflictService(Mock())
    snapshot, conflicts = service.load_conflicts(path)
    expected = service.preview_resolution(snapshot, conflicts, [Resolution.CURRENT])

    saved = service.resolve_file(snapshot, conflicts, [Resolution.CURRENT])

    assert saved.text == expected
    assert path.read_text(encoding="utf-8") == expected
```

- [ ] **Step 2: Ejecutarlos y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/services/test_conflict_service.py -q -k preview`
Expected: FAIL con `AttributeError: 'ConflictService' object has no attribute 'preview_resolution'`

- [ ] **Step 3: Extraer el método**

En `src/gconflict/services/conflict_service.py`, sustituir el cuerpo entero de `resolve_file` por estos dos métodos:

```python
    def preview_resolution(
        self,
        snapshot: TextFileSnapshot,
        conflicts: Sequence[Conflict],
        resolutions: Sequence[Resolution],
        manual: Sequence[list[str] | None] | None = None,
    ) -> str:
        """Reconstruct the resolved text in memory without writing anything."""
        if len(conflicts) != len(resolutions):
            raise ValueError("conflicts and resolutions must have the same length")
        if manual is not None and len(manual) != len(conflicts):
            raise ValueError("conflicts and manual content must have the same length")

        resolved: list[list[str]] = []
        for expected_index, (conflict, resolution) in enumerate(
            zip(conflicts, resolutions)
        ):
            if conflict.index != expected_index:
                raise ValueError("conflict indices must be ordered and contiguous")
            manual_content = None if manual is None else manual[expected_index]
            resolved.append(resolve_conflict(conflict, resolution, manual_content))

        return reconstruct_text(snapshot.text, conflicts, resolved)

    def resolve_file(
        self,
        snapshot: TextFileSnapshot,
        conflicts: Sequence[Conflict],
        resolutions: Sequence[Resolution],
        manual: Sequence[list[str] | None] | None = None,
    ) -> TextFileSnapshot:
        """Resolve, reconstruct, and save a previously loaded snapshot."""
        text = self.preview_resolution(snapshot, conflicts, resolutions, manual)
        return save_text_file(snapshot, text)
```

- [ ] **Step 4: Verificar que pasan los nuevos y los viejos**

Run: `.venv/bin/python -m pytest tests/services/test_conflict_service.py -q`
Expected: PASS

- [ ] **Step 5: Verificar la suite completa**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: PASS, sin fallos

- [ ] **Step 6: Commit**

```bash
git add src/gconflict/services/conflict_service.py tests/services/test_conflict_service.py
git commit -m "refactor: split conflict reconstruction from writing to disk"
```

---

### Task 6: `FileProgress` — cuántos conflictos tiene cada archivo

Las tabs y el sidebar muestran el número de conflictos por archivo (`user.ex ● 2`). Hoy nadie los cuenta: `conflicted_file_descriptors` solo devuelve path y tipo.

Los archivos que no son `CONTENT` cuentan `0` y se marcan como no soportados. Un archivo `CONTENT` que ya no se puede leer (borrado desde otra terminal) cuenta `0` en vez de reventar: RN-024, ante la duda no rompemos la interfaz.

**Files:**
- Create: `src/gconflict/models/file_progress.py`
- Modify: `src/gconflict/services/conflict_service.py`
- Test: `tests/services/test_conflict_service.py`

**Interfaces:**
- Consumes: `ConflictService.conflicted_file_descriptors`, `load_conflicts`, `ConflictedFile`, `ConflictType`.
- Produces:
  - `FileProgress(file: ConflictedFile, total: int)` — dataclass congelada, con propiedad `supported: bool`.
  - `ConflictService.file_progress(cwd: str | Path | None = None) -> list[FileProgress]`
  Las Tareas 10, 11 y 14 lo consumen.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/services/test_conflict_service.py`:

```python
def test_file_progress_counts_conflicts_per_content_file(tmp_path: Path) -> None:
    two = tmp_path / "two.txt"
    two.write_text(
        "<<<<<<< HEAD\na\n=======\nb\n>>>>>>> main\n"
        "<<<<<<< HEAD\nc\n=======\nd\n>>>>>>> main\n",
        encoding="utf-8",
    )
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")

    repository = Mock()
    repository.root.return_value = tmp_path
    repository.conflicted_file_descriptors.return_value = [
        ConflictedFile(Path("two.txt"), ConflictType.CONTENT),
        ConflictedFile(Path("logo.png"), ConflictType.ADD_ADD),
    ]

    progress = ConflictService(repository).file_progress(tmp_path)

    assert [(entry.file.path, entry.total, entry.supported) for entry in progress] == [
        (Path("two.txt"), 2, True),
        (Path("logo.png"), 0, False),
    ]


def test_file_progress_counts_zero_for_an_unreadable_content_file(tmp_path: Path) -> None:
    repository = Mock()
    repository.root.return_value = tmp_path
    repository.conflicted_file_descriptors.return_value = [
        ConflictedFile(Path("gone.txt"), ConflictType.CONTENT),
    ]

    progress = ConflictService(repository).file_progress(tmp_path)

    assert [(entry.file.path, entry.total) for entry in progress] == [(Path("gone.txt"), 0)]
```

Y añadir los imports que falten al principio del archivo:

```python
from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.models.file_progress import FileProgress
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/services/test_conflict_service.py -q -k file_progress`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.models.file_progress'`

- [ ] **Step 3: Escribir el modelo**

Crear `src/gconflict/models/file_progress.py`:

```python
"""How many conflicts a conflicted file holds."""

from dataclasses import dataclass

from gconflict.models.conflicted_file import ConflictedFile, ConflictType


@dataclass(frozen=True)
class FileProgress:
    """A conflicted file and the number of content conflicts inside it."""

    file: ConflictedFile
    total: int

    @property
    def supported(self) -> bool:
        """Report whether gconflict can resolve this file at all."""
        return self.file.conflict_type is ConflictType.CONTENT
```

- [ ] **Step 4: Implementar `ConflictService.file_progress`**

Añadir el import en `src/gconflict/services/conflict_service.py`:

```python
from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.models.file_progress import FileProgress
```

(la línea de `ConflictedFile` ya existe; extenderla con `ConflictType`.)

Y el método, después de `conflicted_file_descriptors`:

```python
    def file_progress(self, cwd: str | Path | None = None) -> list[FileProgress]:
        """Count the content conflicts inside every unresolved file."""
        root = self.repository.root(cwd)
        progress: list[FileProgress] = []
        for descriptor in self.repository.conflicted_file_descriptors(root):
            if descriptor.conflict_type is not ConflictType.CONTENT:
                progress.append(FileProgress(descriptor, 0))
                continue
            try:
                _snapshot, conflicts = self.load_conflicts(root / descriptor.path)
            except (OSError, ValueError, UnicodeDecodeError):
                # A file that cannot be parsed is reported, never resolved (RN-024).
                progress.append(FileProgress(descriptor, 0))
                continue
            progress.append(FileProgress(descriptor, len(conflicts)))
        return progress
```

- [ ] **Step 5: Verificar que pasan**

Run: `.venv/bin/python -m pytest tests/services/test_conflict_service.py -q`
Expected: PASS

- [ ] **Step 6: Verificar la suite completa**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: PASS, sin fallos

- [ ] **Step 7: Commit**

```bash
git add src/gconflict/models/file_progress.py src/gconflict/services/conflict_service.py tests/services/test_conflict_service.py
git commit -m "feat: count content conflicts per unresolved file"
```

---

## Fase 2 — Sistema visual y widgets

### Task 7: El archivo de estilos

Los tokens de la tabla «Paleta del sistema visual», más el layout de la pantalla. Todas las tareas de widget consumen estas variables; ninguna escribe un hex a mano.

**Corregido durante la ejecución.** La versión original de esta tarea ponía los tokens dentro de `app.tcss` y los usaba desde el `DEFAULT_CSS` de cada widget. Eso no funciona: Textual resuelve el `DEFAULT_CSS` de un widget solo con las variables que publica la app en ejecución vía `get_css_variables()`, así que un `$surface-1` definido en `app.tcss` revienta con `UnresolvedVariableError`. La única fuente pasa a ser `src/gconflict/ui/tokens.py`, que expone el diccionario `TOKENS` y una clase base `TokenApp` que los publica; `app.tcss` conserva solo el layout. Los harness de los tests de widget heredan de `TokenApp`, no de `App`.

Ojo con el empaquetado: `pyproject.toml` usa `setuptools.packages.find`, que **no** incluye archivos no-Python. Sin `package-data` el `.tcss` no viaja en el wheel y la app instalada arranca sin estilos.

**Files:**
- Create: `src/gconflict/ui/__init__.py`
- Create: `src/gconflict/ui/tokens.py`
- Create: `src/gconflict/ui/app.tcss`
- Create: `src/gconflict/ui/widgets/__init__.py`
- Create: `tests/ui/__init__.py` (vacío, para que pytest no colisione nombres)
- Create: `tests/ui/test_stylesheet.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `TOKENS: dict[str, str]` en `gconflict.ui.tokens` — los 20 valores de la tabla.
  - `TokenApp(App[None])` en el mismo módulo, que los publica vía `get_css_variables()`. **`GConflictApp` y todos los harness de test de widget heredan de ella.**
  - Las variables `$surface-0`…`$danger` y las clases `.-ok`, `.-danger`, `.-current`, `.-incoming`, `.-muted`, `.-dim`, `.-keycap`, `.-disabled`. Todas las tareas siguientes las usan.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/ui/__init__.py` y `tests/ui/widgets/__init__.py` vacíos, y `tests/ui/test_stylesheet.py`:

```python
from pathlib import Path

import gconflict.ui
from gconflict.ui.tokens import TOKENS, TokenApp


STYLESHEET = Path(gconflict.ui.__file__).parent / "app.tcss"


def test_stylesheet_ships_with_the_package() -> None:
    assert STYLESHEET.is_file()


def test_tokens_carry_every_design_value() -> None:
    assert TOKENS == {
        "surface-0": "#0b0d12",
        "surface-1": "#10131a",
        "surface-2": "#12151d",
        "surface-3": "#1c202b",
        "line": "#272c39",
        "text-1": "#d6dae3",
        "text-2": "#a4abba",
        "text-3": "#79808f",
        "text-4": "#4d5462",
        "text-5": "#343b48",
        "current": "#e8a44c",
        "current-bg": "#241c10",
        "current-line": "#8a6b34",
        "current-text": "#f0d3a4",
        "incoming": "#4ca8e8",
        "incoming-bg": "#10202c",
        "incoming-line": "#35708f",
        "incoming-text": "#a8d6f5",
        "ok": "#6fbf73",
        "danger": "#d9645f",
    }


async def test_token_app_publishes_the_tokens_as_css_variables() -> None:
    async with TokenApp().run_test() as pilot:
        variables = pilot.app.get_css_variables()
    for name, value in TOKENS.items():
        assert variables[name] == value
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/test_stylesheet.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui'`

- [ ] **Step 3: Crear el paquete, los tokens y la hoja de estilos**

Crear `src/gconflict/ui/__init__.py`:

```python
"""Presentation layer for gconflict."""
```

Crear `src/gconflict/ui/widgets/__init__.py`:

```python
"""Widgets used by the gconflict interface."""
```

Crear `src/gconflict/ui/tokens.py` — **la única fuente de los colores**:

```python
"""The single source of the design tokens every widget styles itself with.

Textual parses a widget's ``DEFAULT_CSS`` with only the variables the running
app publishes through ``get_css_variables``, so the tokens cannot live in
``app.tcss`` alone: a widget mounted by any other app would fail to parse.
"""

from textual.app import App

TOKENS: dict[str, str] = {
    "surface-0": "#0b0d12",
    "surface-1": "#10131a",
    "surface-2": "#12151d",
    "surface-3": "#1c202b",
    "line": "#272c39",
    "text-1": "#d6dae3",
    "text-2": "#a4abba",
    "text-3": "#79808f",
    "text-4": "#4d5462",
    "text-5": "#343b48",
    "current": "#e8a44c",
    "current-bg": "#241c10",
    "current-line": "#8a6b34",
    "current-text": "#f0d3a4",
    "incoming": "#4ca8e8",
    "incoming-bg": "#10202c",
    "incoming-line": "#35708f",
    "incoming-text": "#a8d6f5",
    "ok": "#6fbf73",
    "danger": "#d9645f",
}


class TokenApp(App[None]):
    """Base application that publishes the design tokens to every stylesheet."""

    def get_css_variables(self) -> dict[str, str]:
        """Add the design tokens to the variables Textual resolves CSS with."""
        return {**super().get_css_variables(), **TOKENS}
```

Crear `src/gconflict/ui/app.tcss` — solo layout:

```css
/* Layout only. The color tokens live in tokens.py, which publishes them as
   CSS variables so widget DEFAULT_CSS can resolve them too. */

Screen {
    background: $surface-0;
    color: $text-1;
    layout: vertical;
}

.-muted { color: $text-3; }
.-dim { color: $text-4; }
.-ok { color: $ok; }
.-danger { color: $danger; }
.-current { color: $current; }
.-incoming { color: $incoming; }
.-disabled { text-style: dim; }
.-keycap { color: $text-3; background: $surface-3; }
```

- [ ] **Step 4: Declarar el package-data**

Añadir al final de `pyproject.toml`:

```toml
[tool.setuptools.package-data]
gconflict = ["ui/*.tcss"]
```

- [ ] **Step 5: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/ui/test_stylesheet.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/gconflict/ui pyproject.toml tests/ui
git commit -m "feat: add the design token stylesheet"
```

---

### Task 8: `StatusLine`

El artboard «Panel de opciones», sección 4. Hoy los mensajes son cadenas sueltas que sobrescriben el `Label` `#conflict-count`, que también muestra el contador: dos responsabilidades en un widget. `StatusLine` es un widget aparte con cuatro variantes, y cada mensaje lleva **qué pasó, por qué, y la tecla que lo desbloquea**.

**Files:**
- Create: `src/gconflict/ui/widgets/status_line.py`
- Create: `tests/ui/widgets/__init__.py` (vacío)
- Create: `tests/ui/widgets/test_status_line.py`

**Interfaces:**
- Consumes: los tokens de la Tarea 7.
- Produces:
  - `class StatusKind(Enum)`: `INFO`, `SUCCESS`, `WARNING`, `BLOCKED`.
  - `StatusLine(Static)` con `show(kind: StatusKind, title: str, detail: str = "") -> None` y `clear() -> None`.
  - `StatusLine.rendered_text` (propiedad, `str`) para los tests.
  La Tarea 14 la consume.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/ui/widgets/__init__.py` vacío y `tests/ui/widgets/test_status_line.py`:

```python
from textual.app import ComposeResult

from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.status_line import StatusKind, StatusLine


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield StatusLine()


async def test_status_line_starts_empty() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        assert line.rendered_text == ""


async def test_blocked_status_shows_glyph_title_and_detail() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        line.show(
            StatusKind.BLOCKED,
            "No puedes guardar todavia",
            "el conflicto 4 de 4 sigue sin eleccion",
        )
        await pilot.pause()
        assert line.rendered_text == (
            "! No puedes guardar todavia\n  el conflicto 4 de 4 sigue sin eleccion"
        )
        assert line.has_class("-blocked")


async def test_success_status_replaces_the_previous_one() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        line.show(StatusKind.BLOCKED, "Bloqueado")
        line.show(StatusKind.SUCCESS, "Guardado - user.ex", "4 conflictos resueltos")
        await pilot.pause()
        assert line.rendered_text == "+ Guardado - user.ex\n  4 conflictos resueltos"
        assert line.has_class("-success")
        assert not line.has_class("-blocked")


async def test_clear_removes_text_and_variant() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        line.show(StatusKind.WARNING, "Ojo")
        line.clear()
        await pilot.pause()
        assert line.rendered_text == ""
        assert not line.has_class("-warning")
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_status_line.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui.widgets.status_line'`

- [ ] **Step 3: Implementar el widget**

Crear `src/gconflict/ui/widgets/status_line.py`:

```python
"""One-line explanation of what just happened and what unblocks it."""

from enum import Enum

from rich.text import Text
from textual.widgets import Static


class StatusKind(Enum):
    """Severity of a status message."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    BLOCKED = "blocked"


_GLYPHS = {
    StatusKind.INFO: "i",
    StatusKind.SUCCESS: "+",
    StatusKind.WARNING: "~",
    StatusKind.BLOCKED: "!",
}

_STYLES = {
    StatusKind.INFO: "#4ca8e8",
    StatusKind.SUCCESS: "#6fbf73",
    StatusKind.WARNING: "#e8a44c",
    StatusKind.BLOCKED: "#d9645f",
}

_VARIANTS = tuple(f"-{kind.value}" for kind in StatusKind)


class StatusLine(Static):
    """Report an outcome with its reason and its remedy."""

    DEFAULT_CSS = """
    StatusLine {
        height: auto;
        padding: 0 1;
        background: $surface-1;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._rendered_text = ""

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed."""
        return self._rendered_text

    def show(self, kind: StatusKind, title: str, detail: str = "") -> None:
        """Replace the message with one of the given severity."""
        self.remove_class(*_VARIANTS)
        self.add_class(f"-{kind.value}")

        text = Text()
        text.append(_GLYPHS[kind], style=_STYLES[kind])
        text.append(f" {title}", style=_STYLES[kind])
        if detail:
            text.append(f"\n  {detail}", style="#79808f")

        self._rendered_text = text.plain
        self.update(text)

    def clear(self) -> None:
        """Remove the message and its severity."""
        self.remove_class(*_VARIANTS)
        self._rendered_text = ""
        self.update("")
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_status_line.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gconflict/ui/widgets/status_line.py tests/ui/widgets
git commit -m "feat: add the StatusLine widget"
```

---

### Task 9: `ActionBar`

El artboard «Panel de opciones», secciones 1 y 2. Tres filas: `CONFLICT` (solo memoria), `FILE` (escribe en disco o en el index) y `REPO` (navegación, no muta nada). Una acción bloqueada se ve bloqueada **y muestra su motivo al lado**, nunca lo esconde.

**Files:**
- Create: `src/gconflict/ui/widgets/action_bar.py`
- Create: `tests/ui/widgets/test_action_bar.py`

**Interfaces:**
- Consumes: los tokens de la Tarea 7.
- Produces:
  - `Action(key: str, label: str, scope: str, enabled: bool = True, reason: str = "", active: bool = False)` — dataclass congelada. `scope` es `"CONFLICT"`, `"FILE"` o `"REPO"`.
  - `ActionBar(Static)` con `set_actions(actions: Sequence[Action]) -> None` y la propiedad `rendered_text: str`.
  La Tarea 14 la consume.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/ui/widgets/test_action_bar.py`:

```python
from textual.app import ComposeResult

from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.action_bar import Action, ActionBar


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield ActionBar()


async def test_action_bar_groups_actions_by_scope() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        bar.set_actions(
            [
                Action("c", "Current", "CONFLICT", active=True),
                Action("i", "Incoming", "CONFLICT"),
                Action("s", "Save", "FILE", enabled=False, reason="faltan 1 de 4 conflictos"),
                Action("q", "Salir", "REPO"),
            ]
        )
        await pilot.pause()
        assert bar.rendered_text == (
            "CONFLICT  [c] Current  [i] Incoming\n"
            "FILE      [s] Save - faltan 1 de 4 conflictos\n"
            "REPO      [q] Salir"
        )


async def test_action_bar_omits_a_scope_with_no_actions() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        bar.set_actions([Action("q", "Salir", "REPO")])
        await pilot.pause()
        assert bar.rendered_text == "REPO      [q] Salir"


async def test_action_bar_preserves_the_given_order_inside_a_scope() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        bar.set_actions(
            [
                Action("b", "Both C-I", "CONFLICT"),
                Action("c", "Current", "CONFLICT"),
            ]
        )
        await pilot.pause()
        assert bar.rendered_text == "CONFLICT  [b] Both C-I  [c] Current"


async def test_action_bar_rejects_an_unknown_scope() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        try:
            bar.set_actions([Action("x", "Nope", "BRANCH")])
        except ValueError as error:
            assert "BRANCH" in str(error)
        else:
            raise AssertionError("set_actions accepted an unknown scope")
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_action_bar.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui.widgets.action_bar'`

- [ ] **Step 3: Implementar el widget**

Crear `src/gconflict/ui/widgets/action_bar.py`:

```python
"""Available actions, grouped by what they are allowed to touch."""

from collections.abc import Sequence
from dataclasses import dataclass

from rich.text import Text
from textual.widgets import Static

SCOPES = ("CONFLICT", "FILE", "REPO")
_SCOPE_WIDTH = max(len(scope) for scope in SCOPES) + 2


@dataclass(frozen=True)
class Action:
    """One keyboard action and whether the user may take it right now."""

    key: str
    label: str
    scope: str
    enabled: bool = True
    reason: str = ""
    active: bool = False


class ActionBar(Static):
    """Show one row per scope, in SCOPES order, with blocking reasons."""

    DEFAULT_CSS = """
    ActionBar {
        height: auto;
        padding: 0 1;
        background: $surface-2;
        border-top: solid $line;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._rendered_text = ""

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed."""
        return self._rendered_text

    def set_actions(self, actions: Sequence[Action]) -> None:
        """Replace every action shown."""
        for action in actions:
            if action.scope not in SCOPES:
                raise ValueError(f"unknown action scope: {action.scope}")

        text = Text()
        for scope in SCOPES:
            in_scope = [action for action in actions if action.scope == scope]
            if not in_scope:
                continue
            if text.plain:
                text.append("\n")
            text.append(scope.ljust(_SCOPE_WIDTH), style="#4d5462")
            for position, action in enumerate(in_scope):
                if position:
                    text.append("  ")
                self._append_action(text, action)

        self._rendered_text = text.plain
        self.update(text)

    @staticmethod
    def _append_action(text: Text, action: Action) -> None:
        """Append one action, dimmed when it is unavailable."""
        if not action.enabled:
            key_style = label_style = "#4d5462"
        elif action.active:
            key_style = label_style = "#e8a44c"
        else:
            key_style, label_style = "#d6dae3", "#a4abba"

        text.append(f"[{action.key}]", style=key_style)
        text.append(f" {action.label}", style=label_style)
        if action.reason:
            text.append(f" - {action.reason}", style="#4d5462")
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_action_bar.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gconflict/ui/widgets/action_bar.py tests/ui/widgets/test_action_bar.py
git commit -m "feat: add the ActionBar widget grouped by scope"
```

---

### Task 10: `FileTabs`

La fila de tabs del artboard principal: `● user.ex 2 │ ✓ index.ex │ ○ runtime.exs 1`. Se construye sobre `textual.widgets.Tabs`, que ya trae navegación con `tab`/`shift+tab` y emite `Tabs.TabActivated`; no reimplementamos eso.

**Files:**
- Create: `src/gconflict/ui/widgets/file_tabs.py`
- Create: `tests/ui/widgets/test_file_tabs.py`

**Interfaces:**
- Consumes: `FileProgress` (Tarea 6), `ConflictType`.
- Produces:
  - `TabEntry(name: str, remaining: int, glyph: str)` — dataclass congelada.
  - `FileTabs(Tabs)` con `set_files(entries: Sequence[TabEntry]) -> None` y las propiedades `labels: list[str]` y `tab_ids: list[str]`.
  - `FileTabs.entry_for(tab_id: str) -> TabEntry` para traducir un `Tabs.TabActivated` de vuelta al archivo. Los ids llevan un número de generación (`file-1-0`, `file-2-0`, …) porque `Tabs.clear()` elimina de forma diferida y los ids se solaparían entre llamadas.
  - `tab_entries(progress: Sequence[FileProgress], resolved_paths: Container[Path]) -> list[TabEntry]` — función pura de módulo.
  La Tarea 14 la consume.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/ui/widgets/test_file_tabs.py`:

```python
from pathlib import Path

from textual.app import App, ComposeResult

from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.models.file_progress import FileProgress
from gconflict.ui.widgets.file_tabs import FileTabs, TabEntry, tab_entries


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield FileTabs()


def test_tab_entries_mark_pending_resolved_and_unsupported() -> None:
    progress = [
        FileProgress(ConflictedFile(Path("lib/user.ex"), ConflictType.CONTENT), 2),
        FileProgress(ConflictedFile(Path("lib/index.ex"), ConflictType.CONTENT), 1),
        FileProgress(ConflictedFile(Path("priv/logo.png"), ConflictType.ADD_ADD), 0),
    ]

    assert tab_entries(progress, {Path("lib/index.ex")}) == [
        TabEntry("user.ex", 2, "*"),
        TabEntry("index.ex", 0, "+"),
        TabEntry("logo.png", 0, "!"),
    ]


async def test_file_tabs_render_glyph_name_and_count() -> None:
    async with Harness().run_test() as pilot:
        tabs = pilot.app.query_one(FileTabs)
        tabs.set_files(
            [TabEntry("user.ex", 2, "*"), TabEntry("index.ex", 0, "+")]
        )
        await pilot.pause()
        assert tabs.labels == ["* user.ex 2", "+ index.ex"]


async def test_file_tabs_map_an_activated_tab_back_to_its_entry() -> None:
    async with Harness().run_test() as pilot:
        tabs = pilot.app.query_one(FileTabs)
        entries = [TabEntry("user.ex", 2, "*"), TabEntry("index.ex", 0, "+")]
        tabs.set_files(entries)
        await pilot.pause()
        assert tabs.entry_for(tabs.tab_ids[1]) == entries[1]


async def test_setting_files_twice_replaces_the_previous_tabs() -> None:
    async with Harness().run_test() as pilot:
        tabs = pilot.app.query_one(FileTabs)
        tabs.set_files([TabEntry("user.ex", 2, "*")])
        await pilot.pause()
        tabs.set_files([TabEntry("runtime.exs", 1, "o")])
        await pilot.pause()
        assert tabs.labels == ["o runtime.exs 1"]
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_file_tabs.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui.widgets.file_tabs'`

- [ ] **Step 3: Implementar el widget**

Crear `src/gconflict/ui/widgets/file_tabs.py`:

```python
"""One tab per conflicted file, carrying how many conflicts remain."""

from collections.abc import Container, Sequence
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.widgets import Tab, Tabs

from gconflict.models.file_progress import FileProgress

PENDING = "*"
RESOLVED = "+"
UNTOUCHED = "o"
UNSUPPORTED = "!"


@dataclass(frozen=True)
class TabEntry:
    """A file's tab: its basename, its remaining conflicts, and its state."""

    name: str
    remaining: int
    glyph: str


def tab_entries(
    progress: Sequence[FileProgress], resolved_paths: Container[Path]
) -> list[TabEntry]:
    """Turn per-file progress into tab entries, in the order Git reported them."""
    entries: list[TabEntry] = []
    for item in progress:
        if not item.supported:
            entries.append(TabEntry(item.file.path.name, 0, UNSUPPORTED))
        elif item.file.path in resolved_paths:
            entries.append(TabEntry(item.file.path.name, 0, RESOLVED))
        else:
            entries.append(TabEntry(item.file.path.name, item.total, PENDING))
    return entries


class FileTabs(Tabs):
    """Show the conflicted files as tabs."""

    DEFAULT_CSS = """
    FileTabs {
        background: $surface-2;
        border-bottom: solid $line;
    }
    """

    _STYLES = {
        PENDING: "#e8a44c",
        RESOLVED: "#6fbf73",
        UNTOUCHED: "#4d5462",
        UNSUPPORTED: "#d9645f",
    }

    def __init__(self) -> None:
        super().__init__()
        self._entries: dict[str, TabEntry] = {}
        self._generation = 0

    @property
    def labels(self) -> list[str]:
        """Return the plain label of every tab, in order."""
        return [tab.label.plain for tab in self.query(Tab)]

    @property
    def tab_ids(self) -> list[str]:
        """Return the id of every tab, in order."""
        return [str(tab.id) for tab in self.query(Tab)]

    def set_files(self, entries: Sequence[TabEntry]) -> None:
        """Replace every tab with one per given entry."""
        # Tabs.clear() removes deferred, so ids must not collide across calls.
        self.clear()
        self._generation += 1
        self._entries = {}
        for position, entry in enumerate(entries):
            tab_id = f"file-{self._generation}-{position}"
            self._entries[tab_id] = entry
            self.add_tab(Tab(self._label(entry), id=tab_id))

    def entry_for(self, tab_id: str) -> TabEntry:
        """Return the entry behind an activated tab."""
        return self._entries[tab_id]

    def _label(self, entry: TabEntry) -> Text:
        """Render one tab label: glyph, name, and remaining count."""
        style = self._STYLES.get(entry.glyph, "#4d5462")
        label = Text()
        label.append(entry.glyph, style=style)
        label.append(f" {entry.name}", style="#d6dae3")
        if entry.remaining:
            label.append(f" {entry.remaining}", style=style)
        return label
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_file_tabs.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gconflict/ui/widgets/file_tabs.py tests/ui/widgets/test_file_tabs.py
git commit -m "feat: add the FileTabs widget"
```

---

### Task 11: `FileSidebar`

La columna izquierda del artboard principal: lista de archivos con directorio, glifo y estado, más el bloque de progreso (`3 / 8`, `archivos 1 / 4`).

**Files:**
- Create: `src/gconflict/ui/widgets/file_sidebar.py`
- Create: `tests/ui/widgets/test_file_sidebar.py`

**Interfaces:**
- Consumes: `FileProgress` (Tarea 6), los glifos de la Tarea 10.
- Produces:
  - `SidebarEntry(path: Path, glyph: str, note: str)` — dataclass congelada.
  - `FileSidebar(Vertical)` con:
    - `set_entries(entries: Sequence[SidebarEntry], selected: int | None) -> None`
    - `set_progress(conflicts_resolved: int, conflicts_total: int, files_resolved: int, files_total: int) -> None`
    - propiedades `rows: list[str]` y `progress_text: str`.
  La Tarea 14 la consume.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/ui/widgets/test_file_sidebar.py`:

```python
from pathlib import Path

from textual.app import ComposeResult

from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.file_sidebar import FileSidebar, SidebarEntry


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield FileSidebar()


async def test_sidebar_lists_directory_name_and_note() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries(
            [
                SidebarEntry(Path("lib/lynxweb/accounts/user.ex"), "*", "2 sin resolver"),
                SidebarEntry(Path("config/runtime.exs"), "o", "1 sin resolver"),
            ],
            selected=0,
        )
        await pilot.pause()
        assert sidebar.rows == [
            "* user.ex\n  lib/lynxweb/accounts/\n  2 sin resolver",
            "o runtime.exs\n  config/\n  1 sin resolver",
        ]


async def test_sidebar_marks_a_file_at_the_repository_root() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries([SidebarEntry(Path("README.md"), "*", "1 sin resolver")], selected=0)
        await pilot.pause()
        assert sidebar.rows == ["* README.md\n  ./\n  1 sin resolver"]


async def test_sidebar_renders_the_progress_block() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_progress(
            conflicts_resolved=3, conflicts_total=8, files_resolved=1, files_total=4
        )
        await pilot.pause()
        assert sidebar.progress_text == "PROGRESO 3 / 8\narchivos 1 / 4"


async def test_sidebar_survives_an_empty_file_list() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries([], selected=None)
        await pilot.pause()
        assert sidebar.rows == []
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_file_sidebar.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui.widgets.file_sidebar'`

- [ ] **Step 3: Implementar el widget**

Crear `src/gconflict/ui/widgets/file_sidebar.py`:

```python
"""The conflicted-file list and the global progress block."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView, Static

_GLYPH_STYLES = {"*": "#e8a44c", "+": "#6fbf73", "o": "#4d5462", "!": "#d9645f"}


@dataclass(frozen=True)
class SidebarEntry:
    """One row of the file list."""

    path: Path
    glyph: str
    note: str


class FileSidebar(Vertical):
    """List the conflicted files and summarise overall progress."""

    DEFAULT_CSS = """
    FileSidebar {
        width: 32;
        background: $surface-1;
        border-right: solid $line;
    }
    FileSidebar > ListView {
        height: 1fr;
        background: $surface-1;
    }
    FileSidebar > #sidebar-progress {
        height: auto;
        padding: 1;
        border-top: solid $line;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[str] = []
        self._progress_text = ""

    def compose(self) -> ComposeResult:
        yield ListView()
        yield Static("", id="sidebar-progress")

    @property
    def rows(self) -> list[str]:
        """Return the plain text of every file row, in order."""
        return list(self._rows)

    @property
    def progress_text(self) -> str:
        """Return the plain text of the progress block."""
        return self._progress_text

    def set_entries(
        self, entries: Sequence[SidebarEntry], selected: int | None
    ) -> None:
        """Replace the file list and move the highlight."""
        listing = self.query_one(ListView)
        listing.clear()
        self._rows = []
        for entry in entries:
            text = self._row(entry)
            self._rows.append(text.plain)
            listing.append(ListItem(Label(text)))
        listing.index = selected

    def set_progress(
        self,
        conflicts_resolved: int,
        conflicts_total: int,
        files_resolved: int,
        files_total: int,
    ) -> None:
        """Replace the progress block."""
        text = Text()
        text.append("PROGRESO ", style="#4d5462")
        text.append(f"{conflicts_resolved} / {conflicts_total}", style="#a4abba")
        text.append("\narchivos ", style="#4d5462")
        text.append(f"{files_resolved} / {files_total}", style="#a4abba")
        self._progress_text = text.plain
        self.query_one("#sidebar-progress", Static).update(text)

    @staticmethod
    def _row(entry: SidebarEntry) -> Text:
        """Render one file row: glyph, basename, directory, note."""
        directory = entry.path.parent
        shown = "./" if directory == Path(".") else f"{directory}/"
        style = _GLYPH_STYLES.get(entry.glyph, "#4d5462")

        text = Text()
        text.append(entry.glyph, style=style)
        text.append(f" {entry.path.name}", style="#d6dae3")
        text.append(f"\n  {shown}", style="#4d5462")
        text.append(f"\n  {entry.note}", style=style)
        return text
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_file_sidebar.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gconflict/ui/widgets/file_sidebar.py tests/ui/widgets/test_file_sidebar.py
git commit -m "feat: add the FileSidebar widget"
```

---

## Fase 3 — El editor

### Task 12: `ConflictPanes`

El corazón del artboard principal: dos paneles con número de línea, barra de canal a la izquierda y fondo tenue. El panel elegido lleva borde de acento y la etiqueta `SELECTED`. Las etiquetas de cada lado vienen de `RepositoryContext` (Tarea 4), nunca se codifican como `HEAD`/`main`.

**Files:**
- Create: `src/gconflict/ui/widgets/conflict_panes.py`
- Create: `tests/ui/widgets/test_conflict_panes.py`

**Interfaces:**
- Consumes: `Conflict` (`models/conflict.py`), `Resolution`, `RepositoryContext` (Tarea 4).
- Produces:
  - `ConflictPanes(Horizontal)` con:
    - `show(conflict: Conflict, resolution: Resolution | None, current_label: str, incoming_label: str) -> None`
    - `clear() -> None`
    - propiedades `current_text: str`, `incoming_text: str`, `current_header: str`, `incoming_header: str`.
  La Tarea 14 la consume.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/ui/widgets/test_conflict_panes.py`:

```python
from textual.app import App, ComposeResult

from gconflict.models.conflict import Conflict
from gconflict.models.resolution import Resolution
from gconflict.ui.widgets.conflict_panes import ConflictPanes


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield ConflictPanes()


def make_conflict() -> Conflict:
    return Conflict(
        index=0,
        current=["    user.status\n", "    |> normalize()\n"],
        incoming=["    user.account.status\n"],
        base=None,
        start_line=111,
        end_line=116,
    )


async def test_panes_number_lines_from_the_conflict_start() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), None, "ours - feature/x", "theirs - main")
        await pilot.pause()
        assert panes.current_text == (
            "112     user.status\n113     |> normalize()"
        )
        assert panes.incoming_text == "112     user.account.status"


async def test_panes_headers_carry_the_operation_labels() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), None, "rebased base", "commit being applied")
        await pilot.pause()
        assert panes.current_header == "* CURRENT  rebased base"
        assert panes.incoming_header == "o INCOMING  commit being applied"


async def test_choosing_current_marks_only_that_pane() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), Resolution.CURRENT, "ours", "theirs")
        await pilot.pause()
        assert panes.current_header == "* CURRENT  ours  SELECTED"
        assert panes.incoming_header == "o INCOMING  theirs"


async def test_choosing_both_marks_the_two_panes() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), Resolution.BOTH_INCOMING_FIRST, "ours", "theirs")
        await pilot.pause()
        assert panes.current_header == "* CURRENT  ours  SELECTED"
        assert panes.incoming_header == "o INCOMING  theirs  SELECTED"


async def test_clear_empties_both_panes() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), None, "ours", "theirs")
        panes.clear()
        await pilot.pause()
        assert panes.current_text == ""
        assert panes.incoming_text == ""
        assert panes.current_header == ""
        assert panes.incoming_header == ""
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_conflict_panes.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui.widgets.conflict_panes'`

- [ ] **Step 3: Implementar el widget**

Crear `src/gconflict/ui/widgets/conflict_panes.py`:

```python
"""The two sides of one conflict, shown next to each other."""

from collections.abc import Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gconflict.models.conflict import Conflict
from gconflict.models.resolution import Resolution

_INCLUDES_CURRENT = {
    Resolution.CURRENT,
    Resolution.BOTH_CURRENT_FIRST,
    Resolution.BOTH_INCOMING_FIRST,
}
_INCLUDES_INCOMING = {
    Resolution.INCOMING,
    Resolution.BOTH_CURRENT_FIRST,
    Resolution.BOTH_INCOMING_FIRST,
}


class ConflictPanes(Horizontal):
    """Render CURRENT and INCOMING side by side, marking what is chosen."""

    DEFAULT_CSS = """
    ConflictPanes {
        height: 1fr;
    }
    ConflictPanes > Vertical {
        width: 1fr;
        background: $surface-2;
        border: solid $line;
    }
    ConflictPanes > #pane-current.-selected { border: solid $current; }
    ConflictPanes > #pane-incoming.-selected { border: solid $incoming; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._headers = {"current": "", "incoming": ""}
        self._bodies = {"current": "", "incoming": ""}

    def compose(self) -> ComposeResult:
        with Vertical(id="pane-current"):
            yield Static("", id="header-current")
            yield Static("", id="body-current")
        with Vertical(id="pane-incoming"):
            yield Static("", id="header-incoming")
            yield Static("", id="body-incoming")

    @property
    def current_header(self) -> str:
        """Return the plain text of the CURRENT header."""
        return self._headers["current"]

    @property
    def incoming_header(self) -> str:
        """Return the plain text of the INCOMING header."""
        return self._headers["incoming"]

    @property
    def current_text(self) -> str:
        """Return the plain text of the CURRENT body."""
        return self._bodies["current"]

    @property
    def incoming_text(self) -> str:
        """Return the plain text of the INCOMING body."""
        return self._bodies["incoming"]

    def show(
        self,
        conflict: Conflict,
        resolution: Resolution | None,
        current_label: str,
        incoming_label: str,
    ) -> None:
        """Render one conflict and mark the sides the resolution keeps."""
        # The marker line itself is start_line, so content starts one line later.
        first_line = conflict.start_line + 1
        self._render(
            "current",
            glyph="*",
            title="CURRENT",
            label=current_label,
            selected=resolution in _INCLUDES_CURRENT,
            lines=conflict.current,
            first_line=first_line,
            accent="#e8a44c",
            gutter="#8a6b34",
            body="#f0d3a4",
        )
        self._render(
            "incoming",
            glyph="o",
            title="INCOMING",
            label=incoming_label,
            selected=resolution in _INCLUDES_INCOMING,
            lines=conflict.incoming,
            first_line=first_line,
            accent="#4ca8e8",
            gutter="#35708f",
            body="#a8d6f5",
        )

    def clear(self) -> None:
        """Empty both panes and drop their selection marks."""
        for side in ("current", "incoming"):
            self._headers[side] = ""
            self._bodies[side] = ""
            self.query_one(f"#header-{side}", Static).update("")
            self.query_one(f"#body-{side}", Static).update("")
            self.query_one(f"#pane-{side}").remove_class("-selected")

    def _render(
        self,
        side: str,
        *,
        glyph: str,
        title: str,
        label: str,
        selected: bool,
        lines: Sequence[str],
        first_line: int,
        accent: str,
        gutter: str,
        body: str,
    ) -> None:
        """Render one pane's header and body."""
        header = Text()
        header.append(glyph, style=accent)
        header.append(f" {title}", style=accent)
        header.append(f"  {label}", style="#79808f")
        if selected:
            header.append("  SELECTED", style=accent)

        content = Text()
        for offset, line in enumerate(lines):
            if offset:
                content.append("\n")
            content.append(str(first_line + offset).rjust(3), style=gutter)
            content.append(" ", style=gutter)
            content.append(line.rstrip("\r\n"), style=body)

        self._headers[side] = header.plain
        self._bodies[side] = content.plain
        self.query_one(f"#header-{side}", Static).update(header)
        self.query_one(f"#body-{side}", Static).update(content)
        pane = self.query_one(f"#pane-{side}")
        pane.set_class(selected, "-selected")
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_conflict_panes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/gconflict/ui/widgets/conflict_panes.py tests/ui/widgets/test_conflict_panes.py
git commit -m "feat: add the ConflictPanes widget"
```

---

### Task 13: `ResultPane`

El panel `RESULT` del artboard principal: lo que se va a escribir, y si ya está guardado o no. Consume `ConflictService.preview_resolution` (Tarea 5).

El panel muestra a lo sumo `max_lines` líneas para no dominar la pantalla; cuando recorta lo dice, nunca finge que ese es el archivo completo.

**Files:**
- Create: `src/gconflict/ui/widgets/result_pane.py`
- Create: `tests/ui/widgets/test_result_pane.py`

**Interfaces:**
- Consumes: los tokens de la Tarea 7.
- Produces:
  - `ResultPane(Vertical)` con:
    - `show(text: str, *, saved: bool, first_line: int = 1, max_lines: int = 8) -> None`
    - `clear() -> None`
    - propiedades `header_text: str`, `body_text: str`.
  La Tarea 14 la consume.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/ui/widgets/test_result_pane.py`:

```python
from textual.app import ComposeResult

from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.result_pane import ResultPane


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield ResultPane()


async def test_result_pane_numbers_lines_and_warns_it_is_unsaved() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("def status do\n  user.status\nend\n", saved=False, first_line=111)
        await pilot.pause()
        assert pane.header_text == "RESULT  lo que se escribira en el archivo  sin guardar"
        assert pane.body_text == "111 def status do\n112   user.status\n113 end"


async def test_result_pane_reports_a_saved_file() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("a\n", saved=True)
        await pilot.pause()
        assert pane.header_text == "RESULT  lo que se escribira en el archivo  guardado"


async def test_result_pane_says_when_it_truncates() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("".join(f"line {n}\n" for n in range(1, 11)), saved=False, max_lines=3)
        await pilot.pause()
        assert pane.body_text == "1 line 1\n2 line 2\n3 line 3\n... 7 lineas mas"


async def test_result_pane_handles_an_empty_result() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("", saved=False)
        await pilot.pause()
        assert pane.body_text == "(archivo vacio)"


async def test_clear_empties_the_pane() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("a\n", saved=False)
        pane.clear()
        await pilot.pause()
        assert pane.header_text == ""
        assert pane.body_text == ""
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_result_pane.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui.widgets.result_pane'`

- [ ] **Step 3: Implementar el widget**

Crear `src/gconflict/ui/widgets/result_pane.py`:

```python
"""Preview of the text that Save would write to the file."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

_TITLE = "RESULT  lo que se escribira en el archivo"


class ResultPane(Vertical):
    """Show the reconstructed file before anything touches disk."""

    DEFAULT_CSS = """
    ResultPane {
        height: auto;
        max-height: 12;
        background: $surface-0;
        border: solid $line;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._header_text = ""
        self._body_text = ""

    def compose(self) -> ComposeResult:
        yield Static("", id="result-header")
        yield Static("", id="result-body")

    @property
    def header_text(self) -> str:
        """Return the plain text of the header."""
        return self._header_text

    @property
    def body_text(self) -> str:
        """Return the plain text of the preview body."""
        return self._body_text

    def show(
        self, text: str, *, saved: bool, first_line: int = 1, max_lines: int = 8
    ) -> None:
        """Render the preview, saying whether it has been written yet."""
        header = Text()
        header.append(_TITLE, style="#6fbf73")
        header.append("  ")
        header.append(
            "guardado" if saved else "sin guardar",
            style="#6fbf73" if saved else "#d9645f",
        )

        lines = text.splitlines()
        body = Text()
        if not lines:
            body.append("(archivo vacio)", style="#4d5462")
        else:
            for offset, line in enumerate(lines[:max_lines]):
                if offset:
                    body.append("\n")
                body.append(str(first_line + offset), style="#4d5462")
                body.append(f" {line}", style="#d6dae3")
            hidden = len(lines) - max_lines
            if hidden > 0:
                body.append(f"\n... {hidden} lineas mas", style="#4d5462")

        self._header_text = header.plain
        self._body_text = body.plain
        self.query_one("#result-header", Static).update(header)
        self.query_one("#result-body", Static).update(body)

    def clear(self) -> None:
        """Empty the pane."""
        self._header_text = ""
        self._body_text = ""
        self.query_one("#result-header", Static).update("")
        self.query_one("#result-body", Static).update("")
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_result_pane.py -q`
Expected: PASS

- [ ] **Step 5: Verificar la suite completa**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: PASS, sin fallos

- [ ] **Step 6: Commit**

```bash
git add src/gconflict/ui/widgets/result_pane.py tests/ui/widgets/test_result_pane.py
git commit -m "feat: add the ResultPane widget"
```

---

## Fase 4 — Integración

### Task 14: `RepositoryHeader` y la nueva composición

Aquí se junta todo. `GConflictApp.compose` deja de rendir `ListView` + tres `Label` y pasa a rendir header, tabs, sidebar, paneles, resultado, status y barra de acciones.

Reglas que **no** cambian y que los tests existentes ya protegen: `main()` conserva su firma, sus códigos de salida y su reconstrucción de rutas con espacios; `Save` sigue bloqueado hasta que todos los conflictos tengan elección; `Mark resolved` sigue bloqueado hasta que un `Save` haya tenido éxito; ningún atajo muta el repositorio por su cuenta.

**Files:**
- Create: `src/gconflict/ui/widgets/repository_header.py`
- Create: `tests/ui/widgets/test_repository_header.py`
- Modify: `src/gconflict/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: todo lo de las Tareas 4–13.
- Produces:
  - `RepositoryHeader(Static)` con `set_context(context: RepositoryContext) -> None` y la propiedad `rendered_text: str`.
  - `GConflictApp` con `CSS_PATH = "ui/app.tcss"` y los mismos `BINDINGS` de hoy.
  La Tarea 15 y la 16 consumen el nuevo `_refresh_view`.

- [ ] **Step 1: Escribir el test del header**

Crear `tests/ui/widgets/test_repository_header.py`:

```python
from pathlib import Path

from textual.app import App, ComposeResult

from gconflict.git.operation import GitOperation
from gconflict.models.repository_context import RepositoryContext
from gconflict.ui.widgets.repository_header import RepositoryHeader


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield RepositoryHeader()


def context(operation: GitOperation, branch: str | None) -> RepositoryContext:
    return RepositoryContext(
        root=Path("/work/lynxweb"),
        name="lynxweb",
        branch=branch,
        operation=operation,
        current_label="ours",
        incoming_label="theirs",
    )


async def test_header_shows_repository_operation_and_branch() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.MERGE, "feature/user-status"))
        await pilot.pause()
        assert header.rendered_text == "gconflict / lynxweb   MERGE   feature/user-status"


async def test_header_names_a_detached_head() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.REBASE, None))
        await pilot.pause()
        assert header.rendered_text == "gconflict / lynxweb   REBASE   detached HEAD"
```

- [ ] **Step 2: Ejecutarlo y verificar que falla**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_repository_header.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'gconflict.ui.widgets.repository_header'`

- [ ] **Step 3: Implementar el header**

Crear `src/gconflict/ui/widgets/repository_header.py`:

```python
"""Repository name, operation in progress, and checked-out branch."""

from rich.text import Text
from textual.widgets import Static

from gconflict.models.repository_context import RepositoryContext


class RepositoryHeader(Static):
    """Name where the user is and what Git is in the middle of."""

    DEFAULT_CSS = """
    RepositoryHeader {
        height: 1;
        padding: 0 1;
        background: $surface-2;
        border-bottom: solid $line;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._rendered_text = ""

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed."""
        return self._rendered_text

    def set_context(self, context: RepositoryContext) -> None:
        """Replace the header with the given repository state."""
        text = Text()
        text.append("gconflict", style="bold #e8e9ee")
        text.append(" / ", style="#4d5462")
        text.append(context.name, style="#a4abba")
        text.append("   ")
        text.append(context.operation.value.upper(), style="#e8a44c")
        text.append("   ")
        text.append(context.branch or "detached HEAD", style="#79808f")

        self._rendered_text = text.plain
        self.update(text)
```

- [ ] **Step 4: Verificar que el header pasa**

Run: `.venv/bin/python -m pytest tests/ui/widgets/test_repository_header.py -q`
Expected: PASS

- [ ] **Step 5: Escribir el test de la nueva composición**

Primero extender `FakeConflictService` con los tres métodos nuevos (`context`, `file_progress`, `preview_resolution`). Añadir a `FakeConflictService.__init__`:

```python
        self.context_result = RepositoryContext(
            root=Path("/validated/repository"),
            name="repository",
            branch="feature/x",
            operation=GitOperation.MERGE,
            current_label="ours - feature/x",
            incoming_label="theirs - main",
        )
        self.progress_result: list[FileProgress] | None = None
        self.preview_result = "preview text\n"
```

`progress_result` usa `None` como «sin override», no una lista vacía: la Tarea 16 necesita poder forzar **cero** archivos restantes.

y estos métodos a la clase:

```python
    def context(self, cwd: str | Path | None = None) -> RepositoryContext:
        self.calls.append(("context", Path(cwd) if cwd is not None else None))
        return self.context_result

    def file_progress(self, cwd: str | Path | None = None) -> list[FileProgress]:
        self.calls.append(("file_progress", Path(cwd) if cwd is not None else None))
        if self.progress_result is not None:
            return self.progress_result
        return [FileProgress(conflict, 1) for conflict in self.conflicts]

    def preview_resolution(self, snapshot, conflicts, resolutions, manual=None) -> str:
        return self.preview_result
```

y los imports al principio del archivo:

```python
from gconflict.git.operation import GitOperation
from gconflict.models.file_progress import FileProgress
from gconflict.models.repository_context import RepositoryContext
from gconflict.ui.widgets.action_bar import ActionBar
from gconflict.ui.widgets.conflict_panes import ConflictPanes
from gconflict.ui.widgets.file_sidebar import FileSidebar
from gconflict.ui.widgets.file_tabs import FileTabs
from gconflict.ui.widgets.repository_header import RepositoryHeader
from gconflict.ui.widgets.result_pane import ResultPane
from gconflict.ui.widgets.status_line import StatusLine
```

Y añadir estos tests:

```python
async def test_compose_mounts_every_redesigned_widget() -> None:
    service = FakeConflictService([Path("lib/user.ex"), Path("config/runtime.exs")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test():
        assert app.screen.query_one(RepositoryHeader).rendered_text == (
            "gconflict / repository   MERGE   feature/x"
        )
        assert app.screen.query_one(FileTabs).labels == ["* user.ex 1", "* runtime.exs 1"]
        assert app.screen.query_one(FileSidebar).rows == [
            "* user.ex\n  lib/\n  1 sin resolver",
            "* runtime.exs\n  config/\n  1 sin resolver",
        ]
        assert app.screen.query_one(ActionBar).rendered_text.startswith("CONFLICT")
        assert app.screen.query_one(StatusLine).rendered_text == ""
        assert service.mutation_calls == []


async def test_choosing_current_marks_the_pane_and_previews_the_result() -> None:
    service = FakeConflictService([Path("lib/user.ex")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        panes = app.screen.query_one(ConflictPanes)
        assert panes.current_header.endswith("SELECTED")
        assert not panes.incoming_header.endswith("SELECTED")
        assert app.screen.query_one(ResultPane).body_text == "1 preview text"
        assert service.mutation_calls == []


async def test_save_blocked_explains_itself_in_the_status_line() -> None:
    service = FakeConflictService([Path("lib/user.ex")])
    service.loaded = (
        "snapshot",
        [
            SimpleNamespace(current=["a\n"], incoming=["b\n"], index=0, start_line=1, end_line=5),
            SimpleNamespace(current=["c\n"], incoming=["d\n"], index=1, start_line=6, end_line=10),
        ],
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("s")
        assert app.screen.query_one(StatusLine).rendered_text == (
            "! No puedes guardar todavia\n  falta 1 de 2 conflictos sin eleccion"
        )
        assert service.mutation_calls == []
```

**Nota para quien implemente:** los `SimpleNamespace` que usa `FakeConflictService.loaded` ahora necesitan también `index`, `start_line` y `end_line`, porque `ConflictPanes.show` los lee. Actualizar el `loaded` por defecto de `FakeConflictService.__init__` a:

```python
        self.loaded = (
            "snapshot",
            [
                SimpleNamespace(
                    current=["ours\n"],
                    incoming=["theirs\n"],
                    index=0,
                    start_line=1,
                    end_line=5,
                )
            ],
        )
```

- [ ] **Step 6: Ejecutarlos y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_app.py -q -k redesigned`
Expected: FAIL con `NoMatches: No nodes match 'RepositoryHeader'`

- [ ] **Step 7: Reescribir la composición de la app**

En `src/gconflict/app.py`, sustituir los imports de widgets y `compose` por:

```python
from textual.app import App, ComposeResult
from textual import on
from textual.containers import Horizontal, Vertical
from textual.worker import Worker, WorkerState

from gconflict.ui.widgets.action_bar import Action, ActionBar
from gconflict.ui.widgets.conflict_panes import ConflictPanes
from gconflict.ui.widgets.file_sidebar import FileSidebar, SidebarEntry
from gconflict.ui.widgets.file_tabs import FileTabs, tab_entries
from gconflict.ui.widgets.repository_header import RepositoryHeader
from gconflict.ui.widgets.result_pane import ResultPane
from gconflict.ui.widgets.status_line import StatusKind, StatusLine
from gconflict.models.file_progress import FileProgress
from gconflict.models.repository_context import RepositoryContext
from textual.widgets import ListView
```

Añadir a la clase, junto a `TITLE` y `BINDINGS`:

```python
    CSS_PATH = "ui/app.tcss"
```

Añadir al `__init__`, después de `self._editor_worker`:

```python
        self._context: RepositoryContext | None = None
        self._progress: list[FileProgress] = []
        self._resolved_paths: set[Path] = set()
```

Sustituir `compose` entero por:

```python
    def compose(self) -> ComposeResult:
        yield RepositoryHeader()
        yield FileTabs()
        with Horizontal(id="body"):
            yield FileSidebar()
            with Vertical(id="editor"):
                yield ConflictPanes()
                yield ResultPane()
        yield StatusLine()
        yield ActionBar()

    def on_mount(self) -> None:
        """Load repository state once the widgets exist."""
        self._context = self.service.context(self.cwd)
        self._progress = self.service.file_progress(self.cwd)
        self._conflicted_files = [item.file for item in self._progress]
        self.query_one(RepositoryHeader).set_context(self._context)
        self._refresh_view()
        # Tabs would otherwise take the initial focus and swallow enter/arrows.
        self.query_one(FileSidebar).query_one(ListView).focus()
```

`ListView` sigue importándose desde `textual.widgets`; el resto de imports de widgets de `app.py` (`Footer`, `Header`, `Label`, `ListItem`) ya no se usan y se eliminan.

Añadir los métodos de refresco:

```python
    def _refresh_view(self) -> None:
        """Rebuild every widget from the current in-memory state."""
        self.query_one(FileTabs).set_files(
            tab_entries(self._progress, self._resolved_paths)
        )
        self.query_one(FileSidebar).set_entries(
            [self._sidebar_entry(item) for item in self._progress],
            selected=self._selected_index(),
        )
        self.query_one(FileSidebar).set_progress(
            conflicts_resolved=sum(1 for item in self.resolutions if item is not None),
            conflicts_total=sum(item.total for item in self._progress),
            files_resolved=len(self._resolved_paths),
            files_total=len(self._progress),
        )
        self._render_active_conflict()
        self._refresh_actions()

    def _sidebar_entry(self, item: FileProgress) -> SidebarEntry:
        """Describe one file for the sidebar."""
        if not item.supported:
            return SidebarEntry(item.file.path, "!", "no soportado")
        if item.file.path in self._resolved_paths:
            return SidebarEntry(item.file.path, "+", "guardado - staged")
        return SidebarEntry(item.file.path, "*", f"{item.total} sin resolver")

    def _selected_index(self) -> int | None:
        """Return the position of the selected file, if any."""
        if self.selected_file is None:
            return None
        for position, item in enumerate(self._progress):
            if item.file.path == self.selected_file.path:
                return position
        return None

    def _refresh_actions(self) -> None:
        """Rebuild the action bar from what is currently allowed."""
        supported = (
            self.selected_file is not None
            and self.selected_file.conflict_type is ConflictType.CONTENT
        )
        active = self.resolutions[self.active_conflict_index] if self.resolutions else None
        pending = sum(1 for item in self.resolutions if item is None)

        conflict_actions = [
            Action("c", "Current", "CONFLICT", supported, active=active is Resolution.CURRENT),
            Action("i", "Incoming", "CONFLICT", supported, active=active is Resolution.INCOMING),
            Action(
                "b", "Both C-I", "CONFLICT", supported,
                active=active is Resolution.BOTH_CURRENT_FIRST,
            ),
            Action(
                "B", "Both I-C", "CONFLICT", supported,
                active=active is Resolution.BOTH_INCOMING_FIRST,
            ),
            Action("u", "Undo", "CONFLICT", supported),
            Action("e", "Editor externo", "CONFLICT", self.selected_file is not None),
        ]

        file_actions = [
            Action(
                "s", "Save", "FILE", supported and not pending,
                reason=self._save_reason(),
            ),
            Action(
                "r", "Mark resolved", "FILE", self._save_succeeded,
                reason="" if self._save_succeeded else "guarda primero con s",
            ),
        ]
        repo_actions = [
            Action("tab", "Siguiente archivo", "REPO"),
            Action("q", "Salir", "REPO"),
        ]
        self.query_one(ActionBar).set_actions(
            [*conflict_actions, *file_actions, *repo_actions]
        )

    def _save_reason(self) -> str:
        """Explain in one clause why Save is unavailable, or return an empty string."""
        if self.selected_file is None:
            return "selecciona un archivo"
        if self.selected_file.conflict_type is not ConflictType.CONTENT:
            return "tipo de conflicto no soportado"
        if self.snapshot is None:
            return "no hay archivo cargado"
        if not self.loaded_conflicts:
            return "el archivo no tiene conflictos cargados"
        pending = sum(1 for item in self.resolutions if item is None)
        if not pending:
            return ""
        return (
            f"falta{'n' if pending != 1 else ''} {pending} "
            f"de {len(self.resolutions)} conflictos sin eleccion"
        )
```

`_save_reason` es **la única** fuente de esa frase: la barra de acciones y la línea de estado la comparten, así que nunca se pueden contradecir.

Sustituir `_render_active_conflict` entero por:

```python
    def _render_active_conflict(self) -> None:
        """Render the active conflict into the panes and the result preview."""
        panes = self.query_one(ConflictPanes)
        result = self.query_one(ResultPane)
        if not self.loaded_conflicts or self._context is None:
            panes.clear()
            result.clear()
            return

        conflict = self.loaded_conflicts[self.active_conflict_index]
        panes.show(
            conflict,
            self.resolutions[self.active_conflict_index],
            self._context.current_label,
            self._context.incoming_label,
        )

        if any(resolution is None for resolution in self.resolutions):
            result.clear()
            return
        text = self.service.preview_resolution(
            self.snapshot, self.loaded_conflicts, self.resolutions
        )
        result.show(text, saved=self._save_succeeded)
```

Sustituir `action_save` y `action_mark_resolved` enteros por:

```python
    def action_save(self) -> None:
        if self._unsupported_selected():
            return
        reason = self._save_reason()
        if reason:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "No puedes guardar todavia", reason
            )
            return

        try:
            snapshot = self.service.resolve_file(
                self.snapshot, self.loaded_conflicts, self.resolutions  # type: ignore[arg-type]
            )
        except Exception as error:
            self.query_one(StatusLine).show(StatusKind.BLOCKED, "Save fallo", str(error))
            return

        resolved = len(self.loaded_conflicts)
        self.snapshot = snapshot
        self.loaded_conflicts = []
        self.resolutions = []
        self._resolution_history = []
        self.active_conflict_index = 0
        self._save_succeeded = True
        assert self.selected_file is not None
        self.query_one(StatusLine).show(
            StatusKind.SUCCESS,
            f"Guardado - {self.selected_file.path.name}",
            f"{resolved} conflictos resueltos - r para hacer git add",
        )
        self._refresh_view()

    def action_mark_resolved(self) -> None:
        if self._unsupported_selected():
            return
        if not self._save_succeeded or self.selected_file is None:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "Marcar resuelto bloqueado", "guarda primero con s"
            )
            return

        try:
            self.service.mark_resolved(self.selected_file.path, cwd=self.cwd)
        except Exception as error:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "Marcar resuelto fallo", str(error)
            )
            return

        self._resolved_paths.add(self.selected_file.path)
        self._progress = self.service.file_progress(self.cwd)
        self._conflicted_files = [item.file for item in self._progress]
        if not self._progress:
            self._report_all_resolved(len(self._resolved_paths))
            return
        self.query_one(StatusLine).show(
            StatusKind.SUCCESS,
            "Marcado como resuelto",
            f"{self.selected_file.path.name} ya no aparece como conflictivo",
        )
        self._refresh_view()
```

`_report_all_resolved` llega en la Tarea 16; hasta entonces esa rama solo se alcanza cuando `file_progress` devuelve vacío, cosa que ningún test de esta tarea provoca. Para que la Tarea 14 corra sola, añadir el stub mínimo y sustituirlo en la 16:

```python
    def _report_all_resolved(self, staged: int) -> None:
        """Announce that nothing is left. Completed in Task 16."""
        self.query_one(ActionBar).set_actions([])
```

En `_editor_worker_state_changed`, sustituir las dos actualizaciones de `#conflict-count` por:

```python
        if event.state is WorkerState.ERROR:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "El editor fallo", str(event.worker.error)
            )
            return
```

y

```python
        if not opened:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED,
                "No encontre un editor",
                "define GIT_EDITOR, VISUAL o EDITOR",
            )
            return
```

En `action_edit`, justo antes de lanzar el worker, informar de que la interfaz sigue viva (artboard «Estados», recuadro C):

```python
        self.query_one(StatusLine).show(
            StatusKind.INFO,
            "Editor externo abierto",
            "al cerrarlo se relee el archivo desde disco",
        )
```

Todo método que hoy termina llamando a `_render_active_conflict()` pasa a llamar `_refresh_view()`.

- [ ] **Step 8: Adaptar los tests existentes de `tests/test_app.py`**

Los tests que consultan `#conflict-count`, `#current` y `#incoming` ya no aplican: esos ids desaparecieron. Reescribir cada uno para consultar el widget equivalente:

| Consulta vieja | Consulta nueva |
|---|---|
| `query_one("#current", Label).render().plain` | `query_one(ConflictPanes).current_text` |
| `query_one("#incoming", Label).render().plain` | `query_one(ConflictPanes).incoming_text` |
| `query_one("#conflict-count", Label).render().plain` | `query_one(StatusLine).rendered_text` |
| `query_one(ListView)` | `query_one(FileSidebar).rows` |

Los tests de `main()` (`test_main_*`) **no** se tocan: `main()` no cambia.

- [ ] **Step 9: Verificar la suite completa**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -5`
Expected: PASS, sin fallos

- [ ] **Step 10: Ver la app de verdad**

En un repositorio con un conflicto real:

```bash
.venv/bin/gconflict /ruta/al/repo/en/conflicto
```

Expected: header con operación y rama, tabs con contadores, sidebar con progreso, dos paneles y el panel RESULT vacío hasta que todos los conflictos tengan elección.

- [ ] **Step 11: Commit**

```bash
git add src/gconflict/app.py src/gconflict/ui/widgets/repository_header.py tests/test_app.py tests/ui/widgets/test_repository_header.py
git commit -m "feat: rebuild the interface around tabs, sidebar, panes and result preview"
```

---

### Task 15: Pantalla de tipo no soportado

El artboard «Estados», recuadro A. Hoy `_unsupported_message` produce dos líneas de texto plano. El diseño da tres pasos accionables y deja `e` (editor externo) habilitado mientras bloquea todo lo demás.

**Files:**
- Modify: `src/gconflict/app.py` (`_unsupported_message`, `_unsupported_selected`)
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `StatusLine`, `ActionBar`, `ConflictType`.
- Produces: `GConflictApp._unsupported_message(conflict_type: ConflictType) -> tuple[str, str]` — título y detalle para `StatusLine`.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_app.py`:

```python
async def test_unsupported_file_explains_itself_and_keeps_only_the_editor() -> None:
    service = FakeConflictService(
        [ConflictedFile(Path("priv/logo.png"), ConflictType.ADD_ADD)]
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert app.screen.query_one(StatusLine).rendered_text == (
            "! Conflicto add_add - no soportado\n"
            "  1 compara las dos versiones fuera - "
            "2 deja la que quieras - 3 vuelve y marca resuelto"
        )
        bar = app.screen.query_one(ActionBar).rendered_text
        assert "[e] Editor externo" in bar
        assert "[c] Current" in bar
        assert app.screen.query_one(ConflictPanes).current_text == ""
        assert service.mutation_calls == []


async def test_unsupported_file_blocks_every_resolution_key() -> None:
    service = FakeConflictService(
        [ConflictedFile(Path("priv/logo.png"), ConflictType.MODIFY_DELETE)]
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        for key in ("c", "i", "b", "B", "s", "r"):
            await pilot.press(key)
        assert app.resolutions == []
        assert service.mutation_calls == []
```

- [ ] **Step 2: Ejecutarlos y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_app.py -q -k unsupported`
Expected: FAIL — el texto del `StatusLine` no coincide

- [ ] **Step 3: Reescribir el mensaje**

En `src/gconflict/app.py`, sustituir `_unsupported_message` por:

```python
    @staticmethod
    def _unsupported_message(conflict_type: ConflictType) -> tuple[str, str]:
        """Explain an unsupported conflict and the way out of it."""
        steps = {
            ConflictType.ADD_ADD: (
                "1 compara las dos versiones fuera - "
                "2 deja la que quieras - 3 vuelve y marca resuelto"
            ),
            ConflictType.MODIFY_DELETE: (
                "1 decide fuera entre borrado y version modificada - "
                "2 deja el resultado - 3 vuelve y marca resuelto"
            ),
            ConflictType.OTHER: (
                "1 resuelvelo con herramientas de Git - "
                "2 deja el resultado - 3 vuelve y marca resuelto"
            ),
        }[conflict_type]
        return f"Conflicto {conflict_type.value} - no soportado", steps
```

Y sustituir `_unsupported_selected` por:

```python
    def _unsupported_selected(self) -> bool:
        """Report an unsupported selection, and say what to do instead."""
        if (
            self.selected_file is not None
            and self.selected_file.conflict_type is not ConflictType.CONTENT
        ):
            title, detail = self._unsupported_message(self.selected_file.conflict_type)
            self.query_one(StatusLine).show(StatusKind.BLOCKED, title, detail)
            return True
        return False
```

En `_reload_selected_file`, sustituir la rama de tipo no soportado por:

```python
        if self.selected_file.conflict_type is not ConflictType.CONTENT:
            title, detail = self._unsupported_message(self.selected_file.conflict_type)
            self.query_one(StatusLine).show(StatusKind.BLOCKED, title, detail)
            self.query_one(ConflictPanes).clear()
            self.query_one(ResultPane).clear()
            self._refresh_actions()
            return
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_app.py -q -k unsupported`
Expected: PASS

- [ ] **Step 5: Verificar la suite completa**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: PASS, sin fallos

- [ ] **Step 6: Commit**

```bash
git add src/gconflict/app.py tests/test_app.py
git commit -m "feat: explain unsupported conflicts with actionable steps"
```

---

### Task 16: Pantalla de todo resuelto

El artboard «Estados», recuadro B. Cuando el último archivo queda staged, la app dice qué se resolvió y **cuál es el siguiente paso del usuario** — sin ejecutarlo (RN-004, RN-005, RN-025).

El recuadro D del mismo artboard («nada que resolver») **no necesita trabajo**: `main()` ya imprime `No unresolved Git conflicts found.` y sale con `0` sin construir la interfaz, y `tests/test_app.py::test_main_returns_zero_without_running_when_no_conflicts` ya lo protege. El artboard lo dibuja para dejar claro que es una línea de terminal, no una pantalla.

**Files:**
- Modify: `src/gconflict/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `ConflictService.file_progress`, `StatusLine`, `ActionBar`, `GitOperation`.
- Produces: `GConflictApp._continue_hint() -> str` — el comando que el usuario debe correr, según la operación.

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/test_app.py`:

```python
async def test_last_resolved_file_reports_the_users_next_step() -> None:
    service = FakeConflictService([Path("lib/user.ex")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("s")
        service.progress_result = []
        await pilot.press("r")
        assert app.screen.query_one(StatusLine).rendered_text == (
            "+ Todo resuelto - 1 archivo en el index\n"
            "  gconflict no hace commit: te toca git merge --continue"
        )
        assert service.mark_resolved_calls == [(Path("lib/user.ex"), "/workspace/subdirectory")]


async def test_continue_hint_follows_the_operation() -> None:
    service = FakeConflictService([Path("lib/user.ex")])
    service.context_result = RepositoryContext(
        root=Path("/validated/repository"),
        name="repository",
        branch="feature/x",
        operation=GitOperation.REBASE,
        current_label="rebased base",
        incoming_label="commit being applied",
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test():
        assert app._continue_hint() == "git rebase --continue"
```

- [ ] **Step 2: Ejecutarlos y verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_app.py -q -k "next_step or continue_hint"`
Expected: FAIL con `AttributeError: 'GConflictApp' object has no attribute '_continue_hint'`

- [ ] **Step 3: Implementar el estado final**

Sustituir el stub de `_report_all_resolved` que dejó la Tarea 14 por la versión completa, y añadir el mapa de comandos. En `src/gconflict/app.py`:

```python
    _CONTINUE_COMMANDS = {
        GitOperation.MERGE: "git merge --continue",
        GitOperation.REBASE: "git rebase --continue",
        GitOperation.CHERRY_PICK: "git cherry-pick --continue",
        GitOperation.REVERT: "git revert --continue",
        GitOperation.NONE: "git commit",
    }

    def _continue_hint(self) -> str:
        """Name the command the user must run; gconflict never runs it."""
        operation = self._context.operation if self._context else GitOperation.NONE
        return self._CONTINUE_COMMANDS[operation]

    def _report_all_resolved(self, staged: int) -> None:
        """Announce that nothing is left and hand Git back to the user."""
        files = "archivo" if staged == 1 else "archivos"
        self.query_one(StatusLine).show(
            StatusKind.SUCCESS,
            f"Todo resuelto - {staged} {files} en el index",
            f"gconflict no hace commit: te toca {self._continue_hint()}",
        )
        self.query_one(ActionBar).set_actions([])
```

`action_mark_resolved` ya llama a `_report_all_resolved` desde la Tarea 14; aquí solo se completa el cuerpo.

Añadir el import que falta al principio del archivo:

```python
from gconflict.git.operation import GitOperation
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_app.py -q -k "next_step or continue_hint"`
Expected: PASS

- [ ] **Step 5: Verificar la suite completa**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: PASS, sin fallos

- [ ] **Step 6: Verificar cobertura de la capa nueva**

Run: `.venv/bin/python -m pytest --cov=gconflict.ui --cov=gconflict.models --cov-report=term-missing -q 2>&1 | tail -15`
Expected: cada módulo de `gconflict/ui/widgets/` por encima del 90%

- [ ] **Step 7: Commit**

```bash
git add src/gconflict/app.py tests/test_app.py
git commit -m "feat: report the all-resolved state and the user's next Git step"
```

---

## Verificación final

Después de la Tarea 16, con evidencia, no de memoria:

- [ ] `.venv/bin/python -m pytest -q` — suite completa en verde, sin flags.
- [ ] `.venv/bin/python -m pip install -e ".[dev]"` — reinstalación limpia.
- [ ] `.venv/bin/gconflict` desde un directorio que no es repo → imprime `Not a Git repository.` y sale con `2`. Comprobar con `echo $?`.
- [ ] `.venv/bin/gconflict` desde un repo sin conflictos → imprime `No unresolved Git conflicts found.` y sale con `0`.
- [ ] `.venv/bin/gconflict --version` → `gconflict 0.1.0`, sale con `0`.
- [ ] `.venv/bin/gconflict --invalid` → sale con `4`.
- [ ] En un repo con un conflicto real: resolver, `s`, `r`, y comprobar con `git status` que el archivo quedó staged y que **no** se creó ningún commit.
- [ ] `git log --oneline` no muestra commits creados por gconflict.

## Deuda conocida que este plan no toca

Anotado para que nadie lo descubra por sorpresa:

- **`README.md` está desincronizado con `app.py`.** Documenta los bindings `e`/`s`/`m`/`q`, pero `app.py:22` liga «mark resolved» a `r`, añade `n p u c i b B` y no declara `q`. La tabla de códigos de salida del README también intercambia el significado de `2` y `4` respecto a `main()`. Corregirlo es una tarea aparte, de documentación.
- **`plan.md` §12** propone `ui/screens/` además de `ui/widgets/`. Este plan solo crea `widgets/`: con una sola pantalla, `screens/` sería un directorio con un archivo. Cuando aparezca la segunda pantalla, se crea.
- El resaltado a nivel de carácter de la variante C descartada sigue siendo buena idea dentro de la variante A. No está en este plan.
