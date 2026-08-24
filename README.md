<img src="assets/gconflict-logo.svg" alt="Logo app">

# gconflict

gconflict es una interfaz de terminal para resolver conflictos de Git.
Permite inspeccionar conflictos de tipo `CONTENT`, editar su contenido y
guardar la resolución desde una interfaz Textual. Los tipos de conflicto que
no son compatibles se muestran como no soportados.

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
python -m pip install -e ".[dev]"
```

## Ejecución

```bash
gconflict [directory]
```

`directory` es opcional y permite indicar el directorio del repositorio. Usa
`--help` para consultar las opciones disponibles y `--version` para mostrar la
versión instalada.

## Uso

- `↑`/`↓`: seleccionar un conflicto.
- `e`: abrir el conflicto seleccionado en un editor externo.
- `s`: guardar el contenido editado.
- `r`: marcar el conflicto como resuelto.
- `q`: salir.

Guardar (`s`) y marcar como resuelto (`r`) son acciones explícitas e
independientes. Para el editor externo se da prioridad a la configuración y
después a `GIT_EDITOR`, `VISUAL` y `EDITOR`, en ese orden.

## Configuración

La configuración opcional se lee únicamente desde
`~/.config/gconflict/config.toml`. Si el archivo no existe se usan los valores
predeterminados; las claves desconocidas se ignoran.

```toml
# Omite editor o theme para usar null y conservar la selección automática.
editor = "code --wait"
collapsible_actions = true
show_status_line = true
show_command_palette = true
theme = "textual-dark"
```

El esquema admite estas claves:

- `editor`: string o `null` mediante omisión. Tiene prioridad sobre
  `GIT_EDITOR`, `VISUAL` y `EDITOR`, en ese orden.
- `collapsible_actions`: booleano, `true` por defecto. Con `false`, las acciones
  permanecen expandidas y no muestran control para plegarlas.
- `show_status_line`: booleano, `true` por defecto.
- `show_command_palette`: booleano, `true` por defecto.
- `theme`: string o `null` mediante omisión. Debe nombrar un tema registrado en
  Textual.

Otro ejemplo mínimo para ocultar elementos de la interfaz es:

```toml
collapsible_actions = false
show_status_line = false
show_command_palette = false
```

Un TOML mal formado, un tipo inválido o un tema no registrado produce un error
de configuración y el código de salida `4`. Cuando la paleta está habilitada,
gconflict oculta solo los comandos del sistema `Keys`, `Maximize` y `Minimize`;
mantiene disponibles `Theme`, `Quit` y `Screenshot`.

La aplicación emite estos códigos de salida:

- `0`: ejecución completada o salida normal.
- `2`: el directorio no es un repositorio Git.
- `4`: argumentos inválidos o configuración inválida.

## Alcance

Actualmente solo se pueden resolver conflictos `CONTENT`; otros tipos se
identifican como no soportados. El proyecto se instala desde el checkout y
ofrece instalación editable para desarrollo. No se afirma que exista una
publicación en PyPI ni que el paquete esté disponible allí.
