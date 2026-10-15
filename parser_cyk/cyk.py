"""
algoritmo cyk (cocke-younger-kasami) con programacion dinamica.

necesita la gramatica en cnf, porque asi cada variable produce o un solo
terminal (A -> a) o exactamente dos variables (A -> B C). eso permite partir
cualquier pedazo de la frase en dos mitades y resolver cada mitad por separado.

la tabla:
  tabla[i][l] es la celda del pedazo que empieza en la palabra i y tiene
  l palabras (o sea tokens[i : i + l]). cada celda es un diccionario:
      variable -> puntero de reconstruccion
  las llaves del diccionario son el conjunto de variables que pueden generar
  ese pedazo (no se repiten), y el valor dice COMO se genero:
      ("hoja", palabra)  si viene de A -> palabra
      (k, B, C)          si viene de A -> B C, donde B genera las primeras
                         k palabras del pedazo y C genera el resto
  con esos punteros se arma el arbol al final sin volver a buscar nada.

la frase se acepta si el simbolo inicial esta en tabla[0][n] (la frase completa).
"""

from parser_cyk.gramatica import EPSILON

# simbolo que usamos como hoja cuando el arbol deriva la cadena vacia
HOJA_EPSILON = "ε"


def normalizar(frase):
    """
    pasa la frase a la lista de tokens que entiende cyk:
      - todo a minusculas (por eso 'She' se vuelve 'she')
      - se separa por espacios, y split() sin argumentos ignora espacios repetidos
      - NO se quita la puntuacion: 'fork.' queda como token y despues se
        rechaza por ser desconocido, en vez de esconder el error
    """
    return frase.lower().split()


class Nodo:
    """nodo del arbol de analisis: una variable con hijos, o una hoja terminal."""

    def __init__(self, simbolo, hijos=None, terminal=False):
        self.simbolo = simbolo
        # lista de nodos hijos (vacia para las hojas)
        self.hijos = hijos or []
        # True si es una palabra de la frase (o la hoja ε)
        self.terminal = terminal

    def hojas(self):
        # palabras del arbol leidas de izquierda a derecha (sin contar la ε)
        if self.terminal:
            return [] if self.simbolo == HOJA_EPSILON else [self.simbolo]
        return [palabra for hijo in self.hijos for palabra in hijo.hojas()]

    def parentizado(self):
        # notacion tipo (S (NP she) (VP eats))
        if self.terminal:
            return self.simbolo
        return "(" + self.simbolo + " " + " ".join(h.parentizado() for h in self.hijos) + ")"


class ResultadoCYK:
    """todo lo que devuelve cyk: decision, tabla, arbol y tokens desconocidos."""

    def __init__(self, aceptada, tokens, tabla, arbol, desconocidos):
        self.aceptada = aceptada
        self.tokens = tokens
        self.tabla = tabla
        # None si la frase no se acepto
        self.arbol = arbol
        # tokens que no son terminales de la gramatica (en orden, sin repetir)
        self.desconocidos = desconocidos


def construir_indices(g):
    """
    indices para no recorrer toda la gramatica en cada celda:
      por_terminal[a]     = variables A con A -> a
      por_par[(B, C)]     = variables A con A -> B C
    los valores se guardan ordenados para que el arbol elegido sea siempre
    el mismo (los sets de python no tienen orden fijo entre ejecuciones).
    """
    por_terminal = {}
    por_par = {}
    for a in g.orden_variables():
        for rhs in g.producciones[a]:
            if len(rhs) == 1:
                por_terminal.setdefault(rhs[0], []).append(a)
            elif len(rhs) == 2:
                por_par.setdefault(rhs, []).append(a)
    # ordenamos cada lista alfabeticamente
    por_terminal = {t: sorted(vs) for t, vs in por_terminal.items()}
    por_par = {par: sorted(vs) for par, vs in por_par.items()}
    return por_terminal, por_par


def cyk(g, tokens):
    """
    ejecuta cyk sobre la gramatica g (debe estar en cnf) y la lista de tokens.
    devuelve un ResultadoCYK con la decision y el arbol si se acepta.
    """
    n = len(tokens)
    # tokens que la gramatica no conoce, solo para avisarle al usuario
    terminales = g.terminales()
    desconocidos = list(dict.fromkeys(t for t in tokens if t not in terminales))

    # caso especial: frase vacia, se acepta solo si el inicial tiene S -> ε
    if n == 0:
        aceptada = EPSILON in g.producciones[g.inicial]
        arbol = Nodo(g.inicial, [Nodo(HOJA_EPSILON, terminal=True)]) if aceptada else None
        return ResultadoCYK(aceptada, tokens, [], arbol, desconocidos)

    por_terminal, por_par = construir_indices(g)

    # tabla[i][l]: n filas (inicio) y n + 1 columnas (largo, la 0 no se usa)
    tabla = [[{} for _ in range(n + 1)] for _ in range(n)]

    # paso 1, largo 1: cada palabra con las variables A -> palabra
    for i, palabra in enumerate(tokens):
        for a in por_terminal.get(palabra, []):
            tabla[i][1][a] = ("hoja", palabra)

    # paso 2, largos de 2 a n: primero los pedazos cortos y luego los largos,
    # asi cuando llenamos una celda sus dos mitades ya estan calculadas
    for largo in range(2, n + 1):
        # todas las posiciones donde cabe un pedazo de ese largo
        for i in range(0, n - largo + 1):
            celda = tabla[i][largo]
            # probamos todos los puntos de division: k palabras a la izquierda
            for k in range(1, largo):
                izquierda = tabla[i][k]                # tokens[i : i+k]
                derecha = tabla[i + k][largo - k]      # tokens[i+k : i+largo]
                # si alguna mitad no la genera nadie, esta division no sirve
                if not izquierda or not derecha:
                    continue
                # combinamos cada B de la izquierda con cada C de la derecha
                for b in izquierda:
                    for c in derecha:
                        # buscamos las A con A -> B C
                        for a in por_par.get((b, c), []):
                            # nos quedamos con el PRIMER puntero que encontramos,
                            # asi el arbol es determinista (si hay ambiguedad
                            # se elige uno y no se enumeran todos)
                            if a not in celda:
                                celda[a] = (k, b, c)

    # se acepta si el inicial genera la frase completa
    aceptada = g.inicial in tabla[0][n]
    # el arbol se arma con los punteros guardados durante el calculo
    arbol = reconstruir(tabla, 0, n, g.inicial) if aceptada else None
    return ResultadoCYK(aceptada, tokens, tabla, arbol, desconocidos)


def reconstruir(tabla, i, largo, variable):
    """arma el subarbol de 'variable' para el pedazo tabla[i][largo] siguiendo punteros."""
    puntero = tabla[i][largo][variable]
    if puntero[0] == "hoja":
        # A -> palabra: el nodo A tiene una sola hoja con la palabra
        return Nodo(variable, [Nodo(puntero[1], terminal=True)])
    # A -> B C: B cubre las primeras k palabras y C el resto
    k, b, c = puntero
    return Nodo(variable, [
        reconstruir(tabla, i, k, b),
        reconstruir(tabla, i + k, largo - k, c),
    ])


# ------------------------------------------------------------- impresion

def dibujar_arbol(nodo, g):
    """
    arbol con sangria usando solo caracteres ascii (para que no falle en
    consolas de windows). las variables auxiliares de la cnf llevan '*'.
    """
    lineas = []

    def etiqueta(n):
        # las hojas van entre comillas para distinguir palabras de variables
        if n.terminal:
            return n.simbolo if n.simbolo == HOJA_EPSILON else f'"{n.simbolo}"'
        return n.simbolo + ("*" if g.es_auxiliar(n.simbolo) else "")

    def visitar(n, prefijo, es_ultimo, es_raiz):
        if es_raiz:
            lineas.append(etiqueta(n))
            prefijo_hijos = ""
        else:
            # `-- para el ultimo hijo y |-- para los demas
            lineas.append(prefijo + ("`-- " if es_ultimo else "|-- ") + etiqueta(n))
            # si no es el ultimo hay que seguir dibujando la linea vertical
            prefijo_hijos = prefijo + ("    " if es_ultimo else "|   ")
        for indice, hijo in enumerate(n.hijos):
            visitar(hijo, prefijo_hijos, indice == len(n.hijos) - 1, False)

    visitar(nodo, "", True, True)
    return "\n".join(lineas)


def formatear_tabla(resultado):
    """muestra las celdas no vacias de la tabla, de los pedazos cortos a los largos."""
    tokens = resultado.tokens
    lineas = []
    for largo in range(1, len(tokens) + 1):
        for i in range(0, len(tokens) - largo + 1):
            celda = resultado.tabla[i][largo]
            # la celda vacia se muestra como {} para ver donde no hubo nada
            variables = ", ".join(sorted(celda)) if celda else ""
            pedazo = " ".join(tokens[i:i + largo])
            lineas.append(f"[{i},{largo}] {pedazo!r}: {{{variables}}}")
    return "\n".join(lineas)
