<img src="assets/gconflict-logo.svg" alt="Logo app">

![Python](https://img.shields.io/badge/python-3.14-blue)
![](https://img.shields.io/github/stars/mane087/gconflict.svg) ![](https://img.shields.io/github/forks/mane087/gconflict.svg) ![](https://img.shields.io/github/release/mane087/gconflict.svg) ![](https://img.shields.io/github/issues/mane087/gconflict.svg)

# gconflict

gconflict es una interfaz de terminal Textual para resolver conflictos de Git.
La arquitectura sigue el flujo `Textual TUI → services → Git/conflicts/filesystem → models`.
Git es la fuente de verdad del estado del repositorio. La aplicación también
integra editores externos para editar el archivo seleccionado.

## Prerrequisitos

- Python 3.13 o superior
- Git disponible en el sistema

## Instalación

Desde una copia local del repositorio:

```bash
python -m pip install .
```

Para desarrollo, usa una instalación editable con las dependencias opcionales:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

El proyecto usa el empaquetado de setuptools y no requiere un paso de
compilación personalizado.

## Ejecución

```bash
gconflict [directory]
```

`directory` es opcional y permite indicar el directorio del repositorio. Usa
`--help` para consultar las opciones disponibles y `--version` para mostrar la
versión instalada. En un entorno de desarrollo con instalación editable,
también puedes ejecutar `.venv/bin/gconflict [directory]`.

## Arquitectura y seguridad

- La TUI consulta los servicios; estos coordinan Git, el motor de conflictos y
  el sistema de archivos, usando los modelos de la aplicación.
- Solo los conflictos `CONTENT` se pueden resolver. Los demás tipos muestran
  instrucciones y bloquean las acciones de modificación.
- La vista previa aparece únicamente cuando todos los conflictos resolubles
  tienen una selección.
- El sistema de archivos conserva los metadatos relevantes y detecta cambios
  concurrentes antes de guardar, aunque esa comprobación mantiene una ventana
  residual de TOCTOU. Rechaza enlaces simbólicos y archivos no regulares.
- Guardar y ejecutar `git add` son acciones independientes. No se ejecutan
  automáticamente `commit`, `--continue` ni `--abort`.

## Uso

- `↑`/`↓` y `Enter`: seleccionar un archivo.
- `→`/`n`: ir al siguiente conflicto.
- `←`/`p`: ir al conflicto anterior.
- `c`: elegir Current.
- `i`: elegir Incoming.
- `b`: elegir Both C-I.
- `B`: elegir Both I-C.
- `u`: quitar la resolución activa.
- `e`: abrir el archivo seleccionado en un editor externo.
- `s`: guardar la resolución. Requiere un archivo `CONTENT` cargado y todos sus
  conflictos resueltos; ejecuta el guardado.
- `r`: marcar el archivo como resuelto.
- `Ctrl+Q`: salir.

Las acciones `c`, `i`, `b` y `B` requieren un conflicto `CONTENT`. `u` elimina
la selección activa. `e` requiere un archivo seleccionado y vuelve a cargar su
estado. `s` requiere resoluciones completas para todos los conflictos
`CONTENT` y todos sus conflictos resueltos. `r` requiere un guardado exitoso
previo y validación de Git.

### ActionBar

El ActionBar agrupa las acciones en `CONFLICT`, `FILE` y `REPO`. Se inicia
cerrado cuando `collapsible_actions = true` y solo se puede alternar haciendo
clic en la barra. Con `false`, permanece expandido y los clics no tienen
efecto. Los chips son informativos; no son controles de acción.

Las acciones mostradas son:

- `CONFLICT`: `c`, `i`, `b`, `B`, `e`, `u`.
- `FILE`: `s`, `r`.
- `REPO`: `up`/`down`, `Enter`, `q`.

`Next` y `Previous` son combinaciones de teclado, no entradas del ActionBar.

## Configuración

La configuración opcional se lee únicamente desde
`~/.config/gconflict/config.toml`. Si el archivo no existe se usan los valores
predeterminados; las claves desconocidas se ignoran.

```toml
# Omite editor o theme para conservar None y la selección automática.
editor = "code --wait"
collapsible_actions = true
show_status_line = true
show_command_palette = true
theme = "textual-dark"
```

El esquema admite estas claves:

- `editor`: string mediante omisión. TOML no tiene un literal `null`: omite esta
  clave para conservar `None`. Un valor configurado no vacío tiene prioridad
  sobre `GIT_EDITOR`, `VISUAL` y `EDITOR`; si la clave se omite o está vacía,
  se aplica la prioridad de las variables de entorno.
- `collapsible_actions`: booleano, `true` por defecto. Con `false`, las acciones
  permanecen expandidas y no muestran control para plegarlas.
- `show_status_line`: booleano, `true` por defecto.
- `show_command_palette`: booleano, `true` por defecto.
- `theme`: string mediante omisión. TOML no tiene un literal `null`: omite esta
  clave para conservar `None`. Debe nombrar un tema registrado en Textual.

Los valores predeterminados son `editor = None`,
`collapsible_actions = true`, `show_status_line = true`,
`show_command_palette = true` y `theme = None`. Las claves desconocidas se
ignoran. Cuando están presentes, `editor` y `theme` deben ser strings; las
demás opciones son booleanas.

Otro ejemplo mínimo para ocultar elementos de la interfaz es:

```toml
collapsible_actions = false
show_status_line = false
show_command_palette = false
```

Un TOML mal formado, un tipo inválido, un tema no registrado o un error de
lectura produce `Configuration error` y el código de salida `4`. Un `editor`
configurado no vacío tiene prioridad sobre `GIT_EDITOR`, `VISUAL` y `EDITOR`; si
la clave se omite o está vacía, se aplica la prioridad de esas variables de
entorno. La orden se divide con `shlex`, sin `shell`, y el archivo objetivo debe
permanecer dentro del repositorio.

Cuando `show_command_palette = true`, `Ctrl+P` abre la paleta y oculta
`Keys`, `Maximize` y `Minimize`, pero conserva `Theme`, `Quit` y `Screenshot`.
Cuando es `false`, `Ctrl+P` no hace nada.

## Pruebas

Comando estándar:

```bash
.venv/bin/python -m pytest -q --asyncio-mode=auto
```

Ejemplos de pruebas enfocadas:

```bash
.venv/bin/python -m pytest tests/git/test_repository.py -q --asyncio-mode=auto
.venv/bin/python -m pytest -q --asyncio-mode=auto -k test_save_calls_resolve_file
```

La aplicación emite estos códigos de salida:

- `0`: ejecución completada sin conflictos, `--help`, `--version` o salida
  normal.
- `2`: el directorio no es un repositorio Git.
- `4`: argumentos inválidos o configuración inválida.

## Alcance

Actualmente solo se pueden resolver conflictos `CONTENT`; otros tipos se
identifican como no soportados. No se afirma que exista una publicación en
PyPI ni que el paquete esté disponible allí.
