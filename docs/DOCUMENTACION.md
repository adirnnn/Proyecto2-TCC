# Documentación — Proyecto 2: simplificación de gramáticas y CYK

Curso: Teoría de la Computación. Lenguaje: Python 3 (solo biblioteca estándar).
La conversión a CNF y el algoritmo CYK están implementados a mano; no se usan bibliotecas de parsing.

Contenido:

1. [Objetivo y alcance](#1-objetivo-y-alcance)
2. [Diseño de la aplicación](#2-diseño-de-la-aplicación)
3. [Simplificación y conversión a CNF](#3-simplificación-y-conversión-a-cnf)
4. [Algoritmo CYK y programación dinámica](#4-algoritmo-cyk-y-programación-dinámica)
5. [Reconstrucción del árbol de análisis](#5-reconstrucción-del-árbol-de-análisis)
6. [Complejidad](#6-complejidad)
7. [Entrada, normalización y medición del tiempo](#7-entrada-normalización-y-medición-del-tiempo)
8. [Ejemplos de frases dentro y fuera del lenguaje](#8-ejemplos-de-frases-dentro-y-fuera-del-lenguaje)
9. [Pruebas realizadas y resultados](#9-pruebas-realizadas-y-resultados)
10. [Discusión: obstáculos y recomendaciones](#10-discusión-obstáculos-y-recomendaciones)
11. [Guía breve para defender el proyecto](#11-guía-breve-para-defender-el-proyecto)
12. [Requisitos y evidencia](#12-requisitos-y-evidencia)

---

## 1. Objetivo y alcance

El enunciado pide:

- Implementar la **simplificación de gramáticas** y la conversión a **Forma Normal de Chomsky**.
- Implementar **CYK** con **programación dinámica**.
- Recibir una frase en inglés `w` y responder **SÍ** o **NO**.
- Indicar el **tiempo** que tarda el algoritmo en validarla.
- Construir el **parse tree** de `w`, guardando nodos en la tabla dinámica.

La gramática principal es la del enunciado ([gramaticas/ingles.txt](../gramaticas/ingles.txt)):

```
S   -> NP VP
VP  -> VP PP | V NP | cooks | drinks | eats | cuts
PP  -> P NP
NP  -> Det N | he | she
V   -> cooks | drinks | eats | cuts
P   -> in | with
N   -> cat | dog | beer | cake | juice | meat | soup | fork | knife | oven | spoon
Det -> a | the
```

Esta gramática **ya está en CNF**: todas sus reglas son `A → B C` o `A → palabra`, y `S`
no aparece en ningún lado derecho. Aun así, el conversor es **general**. Para demostrar
cada transformación se usa la gramática de expresiones `1.txt`
([gramaticas/expresiones.txt](../gramaticas/expresiones.txt)) y varias gramáticas
pequeñas escritas para las pruebas.

## 2. Diseño de la aplicación

Se modeló el problema con módulos separados por responsabilidad, sin clases innecesarias:

```
main.py                 interfaz: argumentos, lectura de la frase, medición, impresión
parser_cyk/gramatica.py representación de la gramática + lectura de archivo + validación CNF
parser_cyk/cnf.py       los 7 pasos de la conversión, cada uno como función pura
parser_cyk/cyk.py       normalización, tabla CYK, punteros, árbol e impresión
tests/                  pruebas unittest + oráculos independientes (tests/oraculos.py)
```

Flujo de una ejecución:

```
archivo .txt --leer_gramatica--> Gramatica --convertir_a_cnf--> Gramatica CNF
frase --normalizar--> tokens --cyk--> ResultadoCYK (decisión, tabla, árbol)
                                       |
                           main.py imprime SÍ/NO, tiempo y árbol
```

### Representación de la gramática

- `Gramatica.inicial`: símbolo inicial (el de la primera regla del archivo).
- `Gramatica.producciones`: diccionario `no terminal → set de tuplas`. Por ejemplo,
  `{"NP": {("Det", "N"), ("he",), ("she",)}}`. Cada lado derecho es una **tupla de
  símbolos completos**, así `NP` nunca se confunde con `N` seguido de `P`. La cadena
  vacía es la tupla vacía `()`. Al usar `set`, las producciones duplicadas desaparecen solas.
- `Gramatica.originales`: variables que venían en la gramática de entrada. Cualquier
  variable que no esté ahí es **auxiliar** (creada por la conversión), y así se puede
  marcar en el árbol.
- Terminal = símbolo que aparece en algún lado derecho y nunca a la izquierda.

Convención de ε: en el archivo, una alternativa formada solo por `e` (o `ε`) es la
cadena vacía. En `1.txt`, `X -> + T X | e` significa `X → +TX | ε`. La `e` dentro de
palabras como `beer` no se toca, porque se comparan símbolos completos y no caracteres.

Determinismo: los `set` de Python no tienen un orden fijo de recorrido entre ejecuciones
(por la aleatorización de hash de cadenas). Por eso, todo recorrido que crea nombres o
elige árboles usa listas ordenadas (`orden_variables()`, `sorted(...)`, índices ordenados
en CYK). Así, la misma entrada da siempre la misma CNF y el mismo árbol.

## 3. Simplificación y conversión a CNF

`convertir_a_cnf(g)` aplica estos pasos en orden y guarda una copia de la gramática
después de cada uno. Esas copias se ven con `python main.py --etapas`.

| Paso | Qué hace | Por qué conserva el lenguaje |
| --- | --- | --- |
| 1. Inicio | Si el inicial `S` aparece en algún lado derecho, crea `S0 → S` y `S0` pasa a ser el inicial. | `S0` solo deriva `S`, así que genera lo mismo. Garantiza que el inicial nunca aparece a la derecha, condición para que pueda tener `S0 → ε`. |
| 2. ε | Calcula los **anulables** por punto fijo. Por cada producción, genera todas las combinaciones de quitar o dejar **cada ocurrencia** anulable (`itertools.product`), descarta las vacías y quita las `A → ε`. Si el inicial era anulable, agrega `inicial → ε`. | Toda derivación que usaba un `A ⇒* ε` se reemplaza por la versión de la producción sin esa `A`. La única cadena que se perdería es ε, y se recupera en el inicial. |
| 3. Unitarias | Calcula los pares unitarios `(A, B)` con `A ⇒* B` usando solo reglas `A → B`, mediante un recorrido en anchura (**cierre transitivo**; un conjunto de visitados hace que los **ciclos** terminen). `A` recibe todas las producciones **no unitarias** de cada `B` alcanzado. | Una cadena de unitarias `A ⇒ B ⇒ … ⇒ C ⇒ α` se reemplaza por el atajo `A → α`. |
| 4. Inútiles | Primero quita los **no generadores** (variables que no derivan ninguna cadena de terminales, por punto fijo) y las producciones que los usan. Después quita los **inalcanzables** desde el inicial. Si el inicial no es generador, el lenguaje es vacío y queda una gramática sin producciones. | Un símbolo inútil no aparece en ninguna derivación completa, así que quitarlo no cambia ninguna cadena del lenguaje. El orden importa: quitar no generadores puede volver inalcanzables a otras variables. |
| 5. Terminales | En lados derechos de largo ≥ 2, cambia cada terminal `a` por una variable `T_a` y agrega `T_a → a`. Los símbolos que no son identificadores reciben nombres legibles (`+` → `T_MAS`, `(` → `T_PAR_IZQ`). | `T_a` solo deriva `a`. |
| 6. Binarización | `A → X1 X2 … Xn` (n > 2) pasa a `A → X1 A_1`, `A_1 → X2 A_2`, …, hasta `A_k → X(n-1) Xn`. Si dos reglas terminan con el mismo sufijo, **comparten** la variable auxiliar. | Cada auxiliar tiene una sola producción, así que `A ⇒* X1…Xn` exactamente como antes. |
| 7. Validación | Los `set` ya eliminaron los duplicados; `errores_cnf()` revisa cada producción y lanza error si alguna no es CNF. | — |

Detalles cuidados:

- **ε en el lenguaje**: solo el inicial puede quedarse con ε, y por el paso 1 no aparece
  a la derecha. Ejemplo: `S → a S b | e` produce `S0 → ε | …`.
- **Unitaria vs terminal**: `A → B` es unitaria solo si `B` es variable. `VP → cooks` es
  una producción terminal y se queda.
- **Anulables repetidos**: `S → A a A` con `A` anulable produce `A a A`, `a A`, `A a` y `a`.
- **Nombres sin colisión**: `nombre_fresco` revisa variables **y** terminales existentes
  y agrega un sufijo `_1`, `_2`, … si el nombre ya está ocupado. Si ya existe `S0`, el
  nuevo inicial es `S0_1`; si ya existe `T_a`, el nuevo es `T_a_1`.
- Los pasos 5 y 6 no crean ε, unitarias ni símbolos inútiles, por eso no se repiten los pasos 2 a 4.

### Resultado con la gramática de inglés

La conversión deja la gramática **exactamente igual**. Esto se verifica en la prueba
`test_ingles_no_cambia`: no se crea un inicial nuevo porque `S` no aparece a la derecha,
no hay ε, ni unitarias, ni inútiles, y no hay reglas largas ni terminales mezclados.

### Resultado con `1.txt` (expresiones)

Etapas reales (salida de `--etapas`, resumida):

```
== 1. símbolo inicial nuevo ==        (nuevo inicial E0 -> E)
== 2. eliminación de producciones ε == (anulables: X, Y)
E -> T | T X        T -> F | F Y        X -> + T | + T X        Y -> * F | * F Y
== 3. eliminación de producciones unitarias ==
(pares unitarios: E0=>E, E0=>F, E0=>T, E=>F, E=>T, T=>F)
== 4. eliminación de símbolos inútiles == (no generadores: ninguno; inalcanzables: ninguno)
```

CNF final:

```
E0 -> F Y | T X | T_PAR_IZQ E0_1 | id
E -> F Y | T X | T_PAR_IZQ E0_1 | id
F -> T_PAR_IZQ E0_1 | id
T -> F Y | T_PAR_IZQ E0_1 | id
X -> T_MAS T | T_MAS X_1
Y -> T_POR F | T_POR Y_1
E0_1 -> E T_PAR_DER
T_MAS -> +
T_PAR_DER -> )
T_PAR_IZQ -> (
T_POR -> *
X_1 -> T X
Y_1 -> F Y
```

La auxiliar `E0_1` se nombra según la primera variable que la necesitó (`E0`). Luego la
reutilizan `E`, `T` y `F`, porque las cuatro tienen el mismo sufijo `E )`.

### Comparación con `1-cnf.txt`

La referencia ([gramaticas/expresiones_cnf_referencia.txt](../gramaticas/expresiones_cnf_referencia.txt))
usa otros nombres, pero la estructura coincide casi uno a uno:

| Nuestra CNF | Referencia `1-cnf.txt` |
| --- | --- |
| `E → F Y \| T X \| T_PAR_IZQ E0_1 \| id` | `E → T X \| F Y \| L Z \| id` |
| `X → T_MAS T \| T_MAS X_1`, `X_1 → T X` | `X → P T \| P W`, `W → T X` |
| `Y → T_POR F \| T_POR Y_1`, `Y_1 → F Y` | `Y → M F \| M V`, `V → F Y` |
| `E0_1 → E T_PAR_DER` | `Z → E R` |
| `T_PAR_IZQ → (`, `T_PAR_DER → )`, `T_MAS → +`, `T_POR → *` | `L → (`, `R → )`, `P → +`, `M → *` |
| `E0 → …` (copia de las producciones de `E`) | — (no existe) |

La diferencia está en la **convención del símbolo inicial**. Usamos la convención
estricta: como `E` aparece en `F → ( E )`, se crea `E0`. La referencia deja `E` como
inicial aunque aparezca a la derecha (en `Z → E R`). Las dos son CNF válidas y generan
el mismo lenguaje, porque ε no pertenece al lenguaje de expresiones. La convención
estricta solo es necesaria cuando el lenguaje contiene ε, pero la aplicamos siempre para
que el algoritmo sea uniforme.

La equivalencia se comprobó sobre un conjunto acotado de cadenas (sección 9): las tres
gramáticas (`1.txt`, nuestra CNF y `1-cnf.txt`) generan exactamente las mismas cadenas
de largo ≤ 7. Esto es **evidencia** fuerte, no una demostración para cualquier largo; el
argumento general es el de la tabla de pasos.

## 4. Algoritmo CYK y programación dinámica

**Programación dinámica**: se resuelve un problema grande combinando las soluciones de
subproblemas más pequeños, que se calculan una sola vez y se guardan en una tabla. En
CYK, el subproblema es: *¿qué variables pueden generar el pedazo `tokens[i : i+l]`?*

**La tabla**: `tabla[i][l]` es la celda del pedazo que empieza en la palabra `i` y tiene
`l` palabras. Cada celda es un diccionario `variable → puntero`:

- las **llaves** son el conjunto de variables que generan ese pedazo (sin repetidos);
- el **valor** dice cómo se generó: `("hoja", palabra)` si viene de `A → palabra`, o
  `(k, B, C)` si viene de `A → B C`, donde `B` genera las primeras `k` palabras y `C` el resto.

**Por qué necesita CNF**: en CNF, todo pedazo de largo ≥ 2 generado por `A` se obtiene
con una regla `A → B C`, donde `B` genera un prefijo no vacío y `C` el resto. Así basta
probar todos los puntos de división y consultar celdas más cortas, que ya están calculadas.
Sin CNF habría reglas de largo 3 o más (muchas formas de partir), unitarias (`A → B`
sobre el mismo pedazo, posiblemente en ciclo) y ε (pedazos vacíos), y la recurrencia
simple dejaría de ser válida.

**Pasos** (`parser_cyk/cyk.py`, función `cyk`):

1. Índices: `por_terminal[a] = [A con A → a]` y `por_par[(B, C)] = [A con A → B C]`,
   ordenados, para no recorrer toda la gramática en cada celda.
2. **Inicialización** (largo 1): `tabla[i][1]` recibe cada `A` con `A → tokens[i]`.
3. **Recorrido**: para cada `largo` de 2 a n, para cada inicio `i`, para cada división
   `k` de 1 a `largo-1`: se combina cada `B ∈ tabla[i][k]` con cada
   `C ∈ tabla[i+k][largo-k]`, y se agrega cada `A` de `por_par[(B, C)]`. Recorrer de los
   largos cortos a los largos garantiza que las dos mitades ya estén calculadas.
4. **Aceptación**: SÍ si el inicial está en `tabla[0][n]`. Si `n = 0`, SÍ solo si el
   inicial tiene `→ ε`.

Tabla real de `the cat drinks the beer` (`python main.py --tabla --frase "The cat drinks the beer"`):

```
[0,1] 'the': {Det}        [1,1] 'cat': {N}        [2,1] 'drinks': {V, VP}
[3,1] 'the': {Det}        [4,1] 'beer': {N}
[0,2] 'the cat': {NP}     [1,2] 'cat drinks': {}  [2,2] 'drinks the': {}   [3,2] 'the beer': {NP}
[0,3] 'the cat drinks': {S}   [1,3] 'cat drinks the': {}   [2,3] 'drinks the beer': {VP}
[0,4] 'the cat drinks the': {}   [1,4] 'cat drinks the beer': {}
[0,5] 'the cat drinks the beer': {S}      <- contiene S: SÍ
```

`[0,3]` contiene `S` porque `the cat` (NP) + `drinks` (VP → drinks) es una frase válida.
La celda de la frase completa `[0,5]` también contiene `S`, por la división
`k = 2`: NP (`the cat`) + VP (`drinks the beer`).

## 5. Reconstrucción del árbol de análisis

El árbol no se inventa después de decidir: se arma con los punteros que se guardaron
**durante** el cálculo de la tabla. `reconstruir(tabla, i, largo, A)`:

- si el puntero de `A` en `tabla[i][largo]` es `("hoja", palabra)`, devuelve el nodo `A`
  con la hoja `palabra`;
- si es `(k, B, C)`, devuelve el nodo `A` con dos hijos: `reconstruir(i, k, B)` y
  `reconstruir(i+k, largo-k, C)`.

Se empieza con `reconstruir(0, n, inicial)`. El árbol se muestra con sangría (caracteres
ASCII) y en notación parentizada.

**Ambigüedad**: si una variable se puede obtener de varias formas en la misma celda,
solo se guarda el **primer** puntero encontrado (divisiones `k` de menor a mayor,
variables en orden). El árbol es determinista, pero **no se enumeran todos** los árboles
posibles y no hay detector de ambigüedad. Ejemplo probado: `S → S S | a` con `a a a`
tiene dos árboles, y siempre sale `(S0 (S a) (S (S a) (S a)))`.

**¿Árbol de qué gramática?** El árbol es de la **gramática CNF**. Las variables
auxiliares creadas por la conversión se marcan con `*` (por ejemplo `T_PAR_IZQ*`,
`E0_1*`), y el programa avisa que el árbol no es de la gramática original. Con la
gramática de inglés la CNF es idéntica a la original, así que el programa lo indica y
ese árbol también es un árbol de la gramática original. No se implementó la
reconstrucción del árbol de la gramática original a partir del de la CNF.

## 6. Complejidad

Sea `n` el número de tokens, `|V|` el número de variables de la CNF y `|P|` el número de producciones.

- **Conversión a CNF**: se hace una sola vez, antes de leer la frase. La eliminación de ε
  puede crear hasta `2^m` versiones de una regla con `m` anulables (exponencial en el
  largo de las reglas, no en la frase). Para estas gramáticas tarda menos de 1 ms
  (0.45 ms medidos con `1.txt` en esta máquina).
- **Índices**: `O(|P|)`.
- **Tiempo de CYK**: hay `O(n²)` celdas y cada una prueba `O(n)` divisiones. En cada
  división se combinan como mucho `|V| · |V|` pares `(B, C)`, cada uno con una búsqueda
  en diccionario de costo promedio constante. En el peor caso es `O(n³ · |V|²)`, es decir,
  cúbico en el largo de la frase y dependiente del tamaño de la gramática. En la práctica
  muchas celdas están vacías y se saltan.
- **Espacio de CYK**: `O(n² · |V|)`: `n(n+1)/2` celdas útiles con como mucho `|V|`
  entradas cada una, y cada puntero ocupa espacio constante.
- **Reconstrucción**: `O(n)`. Un árbol binario con `n` hojas tiene `2n - 1` nodos internos.

Medición pequeña (Python 3.11.9, Windows 11, gramática de inglés, mediana de 30
ejecuciones de `cyk()` por frase, frases `he cooks` + `with a fork` repetido):

| Tokens | Mediana CYK |
| --- | --- |
| 2 | 0.016 ms |
| 5 | 0.024 ms |
| 8 | 0.037 ms |
| 14 | 0.079 ms |
| 26 | 0.291 ms |
| 50 | 1.417 ms |

El tiempo crece claramente más rápido que lineal. Pasar de 26 a 50 tokens (×1.9)
multiplica el tiempo por ×4.9, por debajo del ×7 de un cubo exacto porque muchas celdas
quedan vacías. Son mediciones de una sola máquina y no demuestran un rendimiento general.

## 7. Entrada, normalización y medición del tiempo

Normalización (`normalizar` en `cyk.py`):

1. Todo a **minúsculas**, para aceptar `She` y `The` de los ejemplos oficiales.
2. Se separa por espacios con `split()`, que ignora los espacios repetidos y los de los extremos.
3. **No** se elimina la puntuación ni las palabras desconocidas. `beer.` es un token que
   no es terminal, la frase se rechaza y el programa lista los tokens desconocidos.
4. La entrada vacía produce cero tokens y se acepta solo si la CNF tiene `inicial → ε`.
5. El prefijo `w =` del enunciado no se escribe.
6. En expresiones, los tokens se separan con espacios (`( id + id ) * id`). Se eligió
   esto en lugar de un tokenizador para mantener una sola regla de normalización para
   todas las gramáticas.

Medición: en `main.py` se toma `time.perf_counter_ns()` (reloj de alta resolución)
justo antes y justo después de `cyk(gramatica, tokens)`. Esto incluye la construcción de
los índices, la tabla y los punteros del árbol. **No** incluye la espera de la entrada,
la normalización, la impresión, ni la conversión a CNF (que, con `--etapas`, se mide y
se muestra por separado). En Windows este reloj avanza en pasos de 100 ns (sección 10).

## 8. Ejemplos de frases dentro y fuera del lenguaje

Salidas reales de `python main.py --frase "..."`. Los tiempos son de una sola ejecución.

| Frase | Resultado | Tiempo CYK | Por qué |
| --- | --- | --- | --- |
| `She eats a cake with a fork` | SÍ | 0.0595 ms | NP(she) + VP(VP(eats a cake) + PP(with a fork)) |
| `The cat drinks the beer` | SÍ | 0.0514 ms | NP(the cat) + VP(V drinks + NP(the beer)) |
| `he cooks` | SÍ | 0.0354 ms | NP → he, VP → cooks |
| `the fork drinks the oven` | SÍ | 0.0977 ms | Sintácticamente es NP V NP; semánticamente no tiene sentido |
| `he cuts the meat with a knife in the oven` | SÍ | 0.0811 ms | VP → VP PP aplicado dos veces |
| `eats she a cake` | NO | 0.0370 ms | Ninguna división da NP seguido de VP |
| `the cat` | NO | 0.0315 ms | Solo es un NP; falta el VP |
| `she eats a pizza` | NO | 0.0419 ms | `pizza` no es terminal (se reporta como desconocido) |
| `She eats a cake.` | NO | 0.0369 ms | `cake.` no es terminal: la puntuación no se borra |
| *(vacía)* | NO | — | La gramática de inglés no genera ε |

Más frases del lenguaje: `she drinks the juice`, `the dog eats the meat in the oven`,
`he cooks the soup with a spoon`. Más frases fuera del lenguaje: `the a cat cooks` (dos
determinantes), `she eats with` (PP sin NP), `cat the eats` (orden inválido).

Expresiones (`--gramatica gramaticas/expresiones.txt`): se aceptan `id`, `id + id * id` y
`( id + id ) * id`. Se rechazan `id +`, `( id`, `id id`, `) id (`, `* id` y `( )`.

## 9. Pruebas realizadas y resultados

Comando:

```bash
python -m unittest discover -s tests -v
```

Resultado real: **65 pruebas, todas OK** (`Ran 65 tests in 1.794s — OK`, Python 3.11.9, Windows 11).

| Archivo | Pruebas | Qué cubre |
| --- | --- | --- |
| `tests/test_gramatica.py` | 11 | Lectura de la gramática de inglés y de `1.txt`; `e` aislada como ε pero no dentro de `beer`; flecha `→`; reglas en varias líneas; errores de formato; validación CNF (unitaria, terminal en binaria, regla larga, ε fuera del inicial, ε con el inicial a la derecha). |
| `tests/test_cnf.py` | 24 | Cada paso por separado: inicio nuevo solo si hace falta; anulables; combinaciones con anulables repetidos; ε solo en el inicial; unitarias encadenadas y cíclicas; terminal ≠ unitaria; no generadores e inalcanzables (y su orden); terminales mezclados; producciones largas; sufijos compartidos; ε en el lenguaje; lenguaje vacío; colisión de nombres; inglés sin cambios; determinismo; etapas. Equivalencia original vs CNF en 10 gramáticas de prueba. |
| `tests/test_cyk.py` | 21 | Normalización; ejemplos oficiales; `he cooks`; `the fork drinks the oven`; varios PP; orden inválido, incompleta, PP incompleto, palabra desconocida, doble determinante; mayúsculas y espacios; puntuación; vacía; tabla; dibujo del árbol; expresiones válidas e inválidas; auxiliares marcados; gramática ambigua; ε aceptada; lenguaje vacío. |
| `tests/test_main.py` | 9 | Ejecuta `main.py` como proceso real: frase por teclado y por `--frase`; rechazo con puntuación; vacía; BOM de PowerShell; `--etapas` y `--tabla`; ejecución desde otra carpeta; gramática inexistente; entrada cerrada. |

### Cómo se verifican los árboles

Para cada frase aceptada, `verificar_arbol` comprueba que:

1. la raíz es el símbolo inicial;
2. las hojas, leídas de izquierda a derecha, son **exactamente** los tokens;
3. cada nodo interno `A` con hijos `X Y` (o con una hoja `a`) corresponde a una
   producción `A → X Y` (o `A → a`) de la gramática CNF.

### Oráculos independientes

Para no probar el código contra sí mismo, `tests/oraculos.py` tiene dos referencias que
no usan `cnf.py` ni `cyk.py`:

- `lenguaje_acotado(g, n)`: calcula, por punto fijo, todas las cadenas de largo ≤ n que
  genera **cualquier** CFG (con ε, unitarias o ciclos). Sirve para comparar el lenguaje de
  la gramática original con el de su CNF.
- `es_expresion_valida(tokens)`: reconocedor descendente recursivo escrito a mano para
  `1.txt`. Se puede escribir así porque esa gramática es LL(1).

Comparaciones realizadas:

- 10 gramáticas de prueba con casos difíciles: el lenguaje original y el de la CNF
  coinciden para largo ≤ 7.
- `1.txt`, nuestra CNF y `1-cnf.txt`: mismo lenguaje para largo ≤ 7. Además, las
  97 655 cadenas posibles de largo 1 a 7 sobre `{id, +, *, (, )}` se clasificaron igual
  con el oráculo de punto fijo y con el reconocedor a mano.
- CYK con nuestra CNF, CYK con `1-cnf.txt` y el reconocedor a mano coinciden en las
  19 530 cadenas posibles de largo 1 a 6.

Estas comparaciones son evidencia sobre un conjunto acotado y reproducible, no una
demostración de equivalencia para todas las longitudes.

### Justificación de los resultados esperados

Los valores esperados se derivaron a mano con la gramática, no copiando la salida del programa. Por ejemplo:

- `he cooks`: `S ⇒ NP VP ⇒ he VP ⇒ he cooks`, así que el árbol esperado es `(S (NP he) (VP cooks))`.
- `the cat`: solo `NP → Det N` cubre las dos palabras y no hay `S → NP`, así que NO.
- `S → A a A`, `A → b | e`: al quitar ε deben aparecer exactamente `A a A`, `a A`, `A a` y `a`.
- `S → A | s`, `A → B | a`, `B → A | S | b`: el ciclo S → A → B → S hace que las tres
  variables alcancen a las otras dos, así que todas terminan con `{s, a, b}`.

Como control adicional, se rompieron a propósito tres partes de la conversión (cierre
unitario sin transitividad, ε sin todas las combinaciones, sin inicial nuevo), y las
pruebas de `test_cnf.py` fallaron en los tres casos (6, 4 y 7 pruebas fallidas). Así se confirmó que las
pruebas detectan esos fallos.

## 10. Discusión: obstáculos y recomendaciones

### Obstáculos encontrados

1. **Codificación en la consola de Windows**: al redirigir la salida (pipe o archivo),
   Python usaba cp1252 y fallaba con `UnicodeEncodeError` al imprimir `ε`. Pasó durante
   el desarrollo, al revisar las etapas de `1.txt`. Solución: `main.py` reconfigura
   stdout y stderr a UTF-8, y el árbol se dibuja con caracteres ASCII (`|--`, `` `-- ``).
2. **BOM de PowerShell**: con `"eats she" | python main.py`, PowerShell envía una marca
   invisible `﻿` al inicio. Se pegaba a la primera palabra (`﻿eats`), que
   quedaba como token desconocido. Se detectó al probar a mano en PowerShell. Solución:
   leer stdin con `utf-8-sig`, que descarta el BOM; lo cubre la prueba `test_entrada_con_bom`.
3. **Resolución del reloj**: en esta máquina, `perf_counter_ns` avanza en pasos de 100 ns
   (todos los tiempos terminan en `00`). Para frases de este tamaño (decenas de µs) es
   suficiente, pero una sola medición tiene mucho ruido. Por eso la tabla de crecimiento
   usa la mediana de 30 ejecuciones.
4. **Prueba de ambigüedad mal planteada**: la primera versión de la prueba suponía que
   `she eats a cake with a fork in the oven` era ambigua. No lo es con esta gramática:
   no hay `NP → NP PP` y los PP solo se pueden colgar como `(VP PP) PP`. La prueba se
   rehízo con una gramática realmente ambigua (`S → S S | a`).
5. **Diferencia con la referencia**: la conversión de `1.txt` no coincide textualmente
   con `1-cnf.txt` por la convención del inicial y por los nombres. En vez de comparar
   texto, se comparó el lenguaje generado (sección 9).

### Decisiones y limitaciones

- Solo se muestra **un** árbol por frase (determinista); no se enumeran todos.
- El árbol es de la gramática CNF; no se reconstruye el árbol de la gramática original
  (con inglés coinciden).
- Con la convención de ε del archivo, no se puede usar `e` sola como terminal.
- La entrada se pasa a minúsculas, así que una gramática con terminales en mayúsculas
  no reconocería esas palabras.
- La eliminación de ε es exponencial en el número de anulables de una misma regla.
  Para gramáticas grandes conviene binarizar antes de quitar ε, como proponen algunos
  textos (orden START, TERM, BIN, DEL, UNIT), para que cada regla tenga como mucho 2 anulables.
- Los tokens de expresiones deben ir separados por espacios.

### Recomendaciones

- Guardar en cada celda **todos** los punteros (no solo el primero) si se quiere contar
  o enumerar los árboles de frases ambiguas.
- Para frases largas o gramáticas grandes, recorrer las producciones binarias en lugar
  de todos los pares `(B, C)` cuando las celdas tengan muchas variables.
- Para medir rendimiento en serio: repetir muchas veces, reportar mediana y dispersión,
  y separar la primera ejecución (calentamiento).
- Validar siempre la CNF obtenida (como hace el paso 7) antes de usarla en CYK, porque
  un error en la conversión haría que CYK diera respuestas incorrectas sin avisar.

## 11. Guía breve para defender el proyecto

- **¿Qué guarda cada celda?** `tabla[i][l]` guarda el conjunto de variables que pueden
  generar las `l` palabras que empiezan en la posición `i`. Además, para cada variable
  guarda un puntero de cómo la obtuvo: la palabra, o `(k, B, C)`, que significa "B generó
  las primeras k palabras y C el resto".
- **¿Por qué CYK necesita CNF?** Porque en CNF cada paso de una derivación produce una
  palabra o parte un pedazo exactamente en dos mitades no vacías. Así, la respuesta para
  un pedazo depende solo de pedazos más cortos ya calculados, que es la base de la
  programación dinámica. Con reglas largas, unitarias o ε esa recurrencia no funciona.
- **¿Cómo conserva el lenguaje la conversión?** Cada paso reemplaza una forma de derivar
  por otra equivalente: el inicial nuevo solo deriva el viejo; quitar ε agrega las
  versiones "sin el anulable"; quitar unitarias agrega los atajos; los símbolos inútiles
  nunca aparecen en una derivación completa; `T_a` y las auxiliares de binarización
  tienen una única producción. Además se comprobó con pruebas sobre cadenas acotadas.
- **¿Cómo se reconstruye el árbol?** Desde `tabla[0][n]` con el inicial se sigue el
  puntero: si es una hoja se pone la palabra, y si es `(k, B, C)` se reconstruye `B` en
  las primeras `k` palabras y `C` en el resto, recursivamente. Los punteros se guardaron
  mientras se llenaba la tabla, así que el árbol corresponde exactamente al cálculo de CYK.
- **¿Qué pasa con frases ambiguas?** Se guarda el primer puntero encontrado, así que
  siempre sale el mismo árbol. No se enumeran todos.
- **¿Qué mide el tiempo?** Solo la ejecución de `cyk()` (tabla, punteros e índices), con
  `perf_counter_ns`. No incluye la entrada, la impresión ni la conversión a CNF.

## 12. Requisitos y evidencia

| Requisito | Implementación | Evidencia |
| --- | --- | --- |
| Simplificación y CNF general | `parser_cyk/cnf.py` (7 pasos) | `tests/test_cnf.py` (24 pruebas), `--etapas` con `1.txt` |
| ε, anulables repetidos, unitarias con ciclos, inútiles, nombres sin colisión | `paso_epsilon`, `paso_unitarias`, `paso_inutiles`, `nombre_fresco` | Pruebas específicas en `test_cnf.py` |
| Conversión de `1.txt` y comparación con `1-cnf.txt` | `convertir_a_cnf` + `gramaticas/` | `test_expresiones_contra_original_y_referencia`, `test_contra_referencia_y_reconocedor`, sección 3 |
| CYK con programación dinámica | `parser_cyk/cyk.py`, función `cyk` | `tests/test_cyk.py` (21 pruebas), `--tabla` |
| Respuesta SÍ / NO | `main.py` | `tests/test_main.py`, sección 8 |
| Tiempo de validación | `perf_counter_ns` alrededor de `cyk()` en `main.py` | Salida `Tiempo de validación CYK`, sección 6 |
| Árbol de análisis desde la tabla | Punteros en la tabla + `reconstruir` | `verificar_arbol` (hojas = tokens, cada nodo es una producción) |
| Normalización de la entrada | `normalizar` + `configurar_utf8` | Pruebas de mayúsculas, espacios, puntuación, vacía y BOM |
| Ejemplos dentro y fuera del lenguaje | — | Sección 8 |
| Documentación (diseño, discusión, pruebas) | `README.md`, este documento | Secciones 2–12 |
