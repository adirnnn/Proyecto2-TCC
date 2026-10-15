"""
simplificacion de gramaticas y conversion a forma normal de chomsky (cnf).

cada paso es una funcion que recibe una Gramatica y devuelve una nueva
(no modifica la de entrada), asi se puede guardar como quedo la gramatica
despues de cada etapa y mostrarla con la opcion --etapas.

orden que usamos (y por que):
  1. inicio:     si el inicial sale en algun lado derecho creamos S0 -> S,
                 asi el inicial nuevo nunca sale a la derecha y puede tener ε
                 sin romper la cnf
  2. epsilon:    calculamos los anulables y quitamos las producciones ε
                 (solo el inicial se queda con ε si el lenguaje la tiene)
  3. unitarias:  quitamos A -> B usando el cierre transitivo (sirve con ciclos)
  4. inutiles:   quitamos no generadores y despues inalcanzables, va despues de
                 unitarias porque ese paso puede dejar variables sin usar
  5. terminales: en lados derechos de largo >= 2 cambiamos cada terminal a por
                 una variable T_a con T_a -> a
  6. binarizar:  A -> X1 X2 ... Xn se parte en una cadena de producciones de 2
  7. validacion: los sets ya quitan duplicados, y revisamos que quedo en cnf

los pasos 5 y 6 no crean ε, unitarias ni simbolos inutiles, por eso no hace
falta repetir los pasos 2 a 4 al final.
"""

from itertools import product

from parser_cyk.gramatica import EPSILON, ErrorGramatica, Gramatica

# nombres legibles para terminales que no son identificadores validos
NOMBRES_SIMBOLOS = {
    "+": "MAS",
    "-": "MENOS",
    "*": "POR",
    "/": "DIV",
    "(": "PAR_IZQ",
    ")": "PAR_DER",
}


# ------------------------------------------------------------------ nombres

def simbolos_usados(g):
    # todos los nombres ocupados, variables y terminales, para no repetir ninguno
    return g.no_terminales() | g.terminales()


def nombre_fresco(base, usados):
    """devuelve base si esta libre, si no base_1, base_2, ... el primero libre."""
    if base not in usados:
        return base
    i = 1
    while f"{base}_{i}" in usados:
        i += 1
    return f"{base}_{i}"


def nombre_numerado(base, usados):
    """como nombre_fresco pero siempre con numero: base_1, base_2, ..."""
    i = 1
    while f"{base}_{i}" in usados:
        i += 1
    return f"{base}_{i}"


def nombre_para_terminal(terminal):
    # si el terminal ya es un nombre valido (cake, id) lo usamos tal cual
    if terminal.isidentifier():
        return f"T_{terminal}"
    # si es un simbolo conocido usamos su nombre en espanol
    if terminal in NOMBRES_SIMBOLOS:
        return f"T_{NOMBRES_SIMBOLOS[terminal]}"
    # si no, usamos el codigo unicode de cada caracter (ej: '%' -> T_U25)
    return "T_U" + "_".join(f"{ord(c):X}" for c in terminal)


# ------------------------------------------------------- paso 1: inicio

def paso_inicio(g):
    """crea un inicial nuevo S0 -> S si el inicial sale en algun lado derecho."""
    # buscamos si el inicial aparece a la derecha de alguna produccion
    aparece = any(g.inicial in rhs for lados in g.producciones.values() for rhs in lados)
    if not aparece:
        # no hace falta nada, devolvemos una copia igual
        return g.copia(), "el inicial no aparece en lados derechos, no se agrega uno nuevo"
    # nombre nuevo tipo S0 (o S0_1 si S0 ya existiera)
    nuevo = nombre_fresco(g.inicial + "0", simbolos_usados(g))
    producciones = dict(g.producciones)
    # la unica produccion del inicial nuevo es ir al inicial viejo
    producciones[nuevo] = {(g.inicial,)}
    # originales no cambia, asi S0 queda marcado como auxiliar
    return Gramatica(nuevo, producciones, g.originales), f"nuevo inicial {nuevo} -> {g.inicial}"


# ------------------------------------------------------- paso 2: epsilon

def anulables(g):
    """conjunto de variables que pueden derivar la cadena vacia (punto fijo)."""
    nulos = set()
    cambio = True
    # repetimos hasta que una vuelta completa no agregue nada nuevo
    while cambio:
        cambio = False
        for a, lados in g.producciones.items():
            if a in nulos:
                continue
            # A es anulable si alguna alternativa tiene solo simbolos anulables,
            # la alternativa vacia () cuenta porque all() de nada es True
            if any(all(s in nulos for s in rhs) for rhs in lados):
                nulos.add(a)
                cambio = True
    return nulos


def paso_epsilon(g):
    """quita las producciones ε agregando las versiones sin los anulables."""
    nulos = anulables(g)
    producciones = {}
    for a, lados in g.producciones.items():
        nuevas = set()
        for rhs in lados:
            # por cada simbolo decidimos si se queda o se puede quitar:
            # un anulable tiene dos opciones (quedarse o desaparecer),
            # cualquier otro simbolo solo puede quedarse
            opciones = [[(s,), ()] if s in nulos else [(s,)] for s in rhs]
            # product hace todas las combinaciones, cada ocurrencia por separado
            # (asi A a A da A a A, a A, A a y a)
            for eleccion in product(*opciones):
                nuevo_rhs = tuple(s for parte in eleccion for s in parte)
                # las alternativas vacias se descartan
                if nuevo_rhs:
                    nuevas.add(nuevo_rhs)
        producciones[a] = nuevas
    # si el inicial podia dar ε, el lenguaje tiene ε y se la devolvemos solo a el
    if g.inicial in nulos:
        producciones[g.inicial].add(EPSILON)
    detalle = "anulables: " + (", ".join(sorted(nulos)) if nulos else "ninguno")
    return Gramatica(g.inicial, producciones, g.originales), detalle


# ----------------------------------------------------- paso 3: unitarias

def es_unitaria(rhs, variables):
    # A -> B es unitaria solo si B es variable; A -> palabra es terminal y se queda
    return len(rhs) == 1 and rhs[0] in variables


def pares_unitarios(g):
    """para cada A, las variables B a las que llega solo con unitarias (incluye A)."""
    variables = g.no_terminales()
    pares = {}
    for a in g.producciones:
        # recorrido en anchura empezando por A
        alcanzadas = {a}
        pendientes = [a]
        while pendientes:
            actual = pendientes.pop()
            for rhs in g.producciones[actual]:
                if es_unitaria(rhs, variables) and rhs[0] not in alcanzadas:
                    # si ya la habiamos visto no se agrega, por eso los ciclos terminan
                    alcanzadas.add(rhs[0])
                    pendientes.append(rhs[0])
        pares[a] = alcanzadas
    return pares


def paso_unitarias(g):
    """cambia cada A -> B por las producciones no unitarias de B (y de lo que B alcanza)."""
    variables = g.no_terminales()
    pares = pares_unitarios(g)
    producciones = {}
    for a, alcanzadas in pares.items():
        # A se queda con todas las producciones no unitarias de lo que alcanza
        producciones[a] = {
            rhs
            for b in alcanzadas
            for rhs in g.producciones[b]
            if not es_unitaria(rhs, variables)
        }
    # para el detalle solo mostramos los pares A => B con A distinto de B
    lista = [f"{a}=>{b}" for a in g.orden_variables() for b in sorted(pares[a]) if b != a]
    detalle = "pares unitarios: " + (", ".join(lista) if lista else "ninguno")
    return Gramatica(g.inicial, producciones, g.originales), detalle


# ------------------------------------------------------- paso 4: inutiles

def generadores(g):
    """variables que derivan al menos una cadena de terminales (punto fijo)."""
    variables = g.no_terminales()
    gen = set()
    cambio = True
    while cambio:
        cambio = False
        for a, lados in g.producciones.items():
            if a in gen:
                continue
            # A genera si alguna alternativa tiene solo terminales o variables generadoras
            if any(all(s not in variables or s in gen for s in rhs) for rhs in lados):
                gen.add(a)
                cambio = True
    return gen


def alcanzables(g):
    """variables a las que se llega desde el inicial."""
    variables = g.no_terminales()
    vistos = {g.inicial}
    pendientes = [g.inicial]
    while pendientes:
        actual = pendientes.pop()
        for rhs in g.producciones[actual]:
            for s in rhs:
                # solo seguimos variables que no hayamos visitado
                if s in variables and s not in vistos:
                    vistos.add(s)
                    pendientes.append(s)
    return vistos


def paso_inutiles(g):
    """quita no generadores y despues inalcanzables (en ese orden importa)."""
    variables = g.no_terminales()
    gen = generadores(g)
    no_gen = variables - gen
    # si el inicial no genera nada el lenguaje es vacio
    if g.inicial not in gen:
        vacia = Gramatica(g.inicial, {g.inicial: set()}, g.originales)
        return vacia, "el inicial no es generador: el lenguaje es vacío"
    # quitamos las variables no generadoras y toda produccion que las use
    producciones = {
        a: {rhs for rhs in lados if not any(s in no_gen for s in rhs)}
        for a, lados in g.producciones.items()
        if a in gen
    }
    intermedia = Gramatica(g.inicial, producciones, g.originales)
    # recien ahora calculamos alcanzables, porque quitar no generadores
    # puede dejar mas variables sueltas
    alcanza = alcanzables(intermedia)
    no_alc = set(producciones) - alcanza
    producciones = {a: lados for a, lados in producciones.items() if a in alcanza}
    detalle = (
        "no generadores: " + (", ".join(sorted(no_gen)) or "ninguno")
        + "; inalcanzables: " + (", ".join(sorted(no_alc)) or "ninguno")
    )
    return Gramatica(g.inicial, producciones, g.originales), detalle


# ----------------------------------------------------- paso 5: terminales

def paso_terminales(g):
    """en lados derechos de largo >= 2 cambia cada terminal a por T_a (con T_a -> a)."""
    variables = g.no_terminales()
    usados = simbolos_usados(g)
    # terminal -> variable que lo reemplaza (una sola variable por terminal)
    reemplazo = {}
    producciones = {a: set() for a in g.producciones}
    # recorremos en orden fijo para que los nombres salgan siempre iguales
    for a in g.orden_variables():
        for rhs in sorted(g.producciones[a]):
            if len(rhs) < 2:
                # A -> a y A -> ε se quedan como estan
                producciones[a].add(rhs)
                continue
            nuevo_rhs = []
            for s in rhs:
                if s in variables:
                    nuevo_rhs.append(s)
                    continue
                # es terminal: buscamos (o creamos) su variable
                if s not in reemplazo:
                    nueva = nombre_fresco(nombre_para_terminal(s), usados)
                    usados.add(nueva)
                    reemplazo[s] = nueva
                nuevo_rhs.append(reemplazo[s])
            producciones[a].add(tuple(nuevo_rhs))
    # agregamos las producciones T_a -> a
    for terminal, variable in reemplazo.items():
        producciones[variable] = {(terminal,)}
    lista = [f"{v} -> {t}" for t, v in sorted(reemplazo.items(), key=lambda par: par[1])]
    detalle = "variables de terminal: " + (", ".join(lista) if lista else "ninguna")
    return Gramatica(g.inicial, producciones, g.originales), detalle


# ------------------------------------------------------ paso 6: binarizar

def paso_binarizar(g):
    """parte A -> X1 X2 ... Xn (n > 2) en A -> X1 A_1, A_1 -> X2 A_2, ..."""
    usados = simbolos_usados(g)
    # sufijo (tupla de simbolos) -> variable que lo produce, asi si dos reglas
    # terminan igual comparten la misma auxiliar
    memo = {}
    producciones = {a: set() for a in g.producciones}

    def variable_para(sufijo, duenio):
        # devuelve una variable V con V -> sufijo (ya binarizado)
        if sufijo in memo:
            return memo[sufijo]
        # nombre tipo A_1, A_2 segun la variable que la necesito primero
        nueva = nombre_numerado(duenio, usados)
        usados.add(nueva)
        memo[sufijo] = nueva
        if len(sufijo) == 2:
            # dos simbolos ya es cnf
            producciones[nueva] = {sufijo}
        else:
            # primer simbolo + variable para el resto (recursivo)
            producciones[nueva] = {(sufijo[0], variable_para(sufijo[1:], duenio))}
        return nueva

    # orden fijo para que los nombres no dependan del orden de los sets
    for a in g.orden_variables():
        for rhs in sorted(g.producciones[a]):
            if len(rhs) <= 2:
                producciones[a].add(rhs)
            else:
                producciones[a].add((rhs[0], variable_para(rhs[1:], a)))
    lista = [f"{v} -> {' '.join(s)}" for s, v in sorted(memo.items(), key=lambda par: par[1])]
    detalle = "auxiliares de binarización: " + (", ".join(lista) if lista else "ninguna")
    return Gramatica(g.inicial, producciones, g.originales), detalle


# ------------------------------------------------------- conversion total

# lista de pasos en orden: (titulo, funcion)
PASOS = [
    ("1. símbolo inicial nuevo", paso_inicio),
    ("2. eliminación de producciones ε", paso_epsilon),
    ("3. eliminación de producciones unitarias", paso_unitarias),
    ("4. eliminación de símbolos inútiles", paso_inutiles),
    ("5. sustitución de terminales", paso_terminales),
    ("6. binarización", paso_binarizar),
]


def convertir_a_cnf(g):
    """
    convierte g a cnf. devuelve (gramatica_cnf, etapas) donde etapas es una
    lista de (titulo, detalle, gramatica) con el resultado de cada paso.
    """
    etapas = [("0. gramática original", "", g.copia())]
    actual = g
    # aplicamos cada paso sobre el resultado del anterior
    for titulo, paso in PASOS:
        actual, detalle = paso(actual)
        etapas.append((titulo, detalle, actual.copia()))
    # validacion final: si algo fallo preferimos un error claro a un cyk incorrecto
    errores = actual.errores_cnf()
    if errores:
        raise ErrorGramatica("la conversión no quedó en CNF: " + "; ".join(errores))
    etapas.append(("7. validación final", "la gramática está en CNF", actual.copia()))
    return actual, etapas


def formatear_etapas(etapas):
    """texto legible de todas las etapas (para la opcion --etapas)."""
    bloques = []
    for titulo, detalle, gramatica in etapas:
        bloque = [f"== {titulo} =="]
        if detalle:
            bloque.append(f"({detalle})")
        bloque.append(str(gramatica))
        bloques.append("\n".join(bloque))
    return "\n\n".join(bloques)
