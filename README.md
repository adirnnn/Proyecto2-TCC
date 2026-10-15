# Proyecto 2 — Simplificación de gramáticas y parsing con CYK

Teoría de la Computación. El programa convierte una gramática libre de contexto a
**Forma Normal de Chomsky (CNF)** y usa el algoritmo **CYK** (programación dinámica)
para decidir si una frase en inglés pertenece al lenguaje. Responde **SÍ** o **NO**,
muestra el **tiempo** que tardó CYK y, si la frase se acepta, su **árbol de análisis**.

La documentación completa (diseño, programación dinámica, conversión, complejidad,
obstáculos, pruebas) está en [docs/DOCUMENTACION.md](docs/DOCUMENTACION.md).

## Requisitos e instalación

- Python 3 (desarrollado y probado solo con Python 3.11.9 en Windows 11; no usa nada
  posterior a Python 3.7, pero versiones anteriores a la 3.11 no se probaron).
- No usa bibliotecas externas: solo la biblioteca estándar. No hay que instalar nada.

```bash
git clone https://github.com/adirnnn/Proyecto2-TCC.git
cd Proyecto2-TCC
```

## Ejecución

Uso normal (solo pide la frase):

```bash
python main.py
```

```
Ingrese la frase: She eats a cake with a fork
Frase normalizada: she eats a cake with a fork
Tokens (7): she | eats | a | cake | with | a | fork
Resultado: SÍ
Tiempo de validación CYK: 0.0595 ms (59500 ns)

Árbol de análisis (gramática en CNF):
S
|-- NP
|   `-- "she"
`-- VP
    |-- VP
    |   |-- V
    |   |   `-- "eats"
    |   `-- NP
    |       |-- Det
    |       |   `-- "a"
    |       `-- N
    |           `-- "cake"
    `-- PP
        |-- P
        |   `-- "with"
        `-- NP
            |-- Det
            |   `-- "a"
            `-- N
                `-- "fork"

Notación parentizada: (S (NP she) (VP (VP (V eats) (NP (Det a) (N cake))) (PP (P with) (NP (Det a) (N fork)))))
Nota: la CNF es idéntica a la gramática original, así que este árbol también es un árbol de la gramática original.
```

El tiempo varía en cada ejecución y entre computadoras.

Opciones:

| Opción | Qué hace |
| --- | --- |
| `--frase "..."` | Pasa la frase directamente, sin preguntarla. |
| `--gramatica RUTA` | Usa otra gramática (por defecto `gramaticas/ingles.txt`). |
| `--etapas` | Diagnóstico: muestra la gramática después de cada paso de la conversión a CNF y el tiempo de conversión. |
| `--tabla` | Muestra las celdas de la tabla de CYK. |

Ejemplos:

```bash
python main.py --frase "The cat drinks the beer"
```

```bash
python main.py --frase "she eats a pizza"
```

```bash
python main.py --gramatica gramaticas/expresiones.txt --etapas --frase "( id + id ) * id"
```

```bash
python main.py --frase "he cooks" --tabla
```

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Son 65 pruebas automatizadas (lectura de gramáticas, cada paso de la conversión, CYK,
árboles y la interfaz). Todas pasan; el detalle está en la documentación.

## Normalización de la entrada

- Se convierte todo a **minúsculas** (`She` → `she`), porque los terminales de la
  gramática están en minúsculas.
- Se separa por **espacios**; los espacios repetidos o al inicio/final se ignoran.
- La **puntuación no se elimina**: `cake.` queda como un token distinto de `cake`, no
  pertenece a la gramática y la frase se rechaza, avisando qué tokens son desconocidos.
- La **entrada vacía** se acepta solo si la gramática genera ε (la de inglés no la genera,
  así que responde NO).
- El prefijo `w =` del enunciado es notación: no se escribe.
- Para la gramática de expresiones los tokens también van separados por espacios:
  `( id + id ) * id`, no `(id+id)*id`.

## Formato de los archivos de gramática

```
# comentario
S -> NP VP
NP -> Det N | he | she
X -> + T X | e
```

- Una regla por línea; `->` o `→`; alternativas separadas por `|`.
- Los símbolos se separan con espacios: `NP`, `Det` o `id` son **un** símbolo.
- No terminales = los símbolos que aparecen a la izquierda de alguna regla; el resto son terminales.
- El símbolo inicial es el lado izquierdo de la primera regla.
- Una alternativa formada solo por `e` (o `ε`) es la cadena vacía. La letra `e` dentro de
  una palabra (`beer`) no se toca. Por esta convención, no se puede usar `e` sola como terminal.
- Una variable puede tener reglas en varias líneas (se juntan).

## Estructura

```
main.py                 interfaz de línea de comandos y medición del tiempo
parser_cyk/
  gramatica.py          representación, lectura de archivos y validación de CNF
  cnf.py                simplificación y conversión a CNF por etapas
  cyk.py                algoritmo CYK, punteros de reconstrucción y árbol
gramaticas/
  ingles.txt            gramática del enunciado
  expresiones.txt       gramática de expresiones (1.txt)
  expresiones_cnf_referencia.txt   conversión de referencia (1-cnf.txt)
tests/                  pruebas (unittest) y oráculos independientes
docs/DOCUMENTACION.md   documentación del proyecto
```
