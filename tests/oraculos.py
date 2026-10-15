"""
oraculos independientes para las pruebas.

la idea es tener formas de saber la respuesta correcta SIN usar el codigo
que estamos probando (ni cnf.py ni cyk.py), para comparar contra eso.
"""


def lenguaje_acotado(g, n):
    """
    todas las cadenas de terminales de largo <= n que genera la gramatica g.

    funciona con cualquier cfg (con ε, unitarias, ciclos, etc) porque no deriva
    paso a paso, sino que calcula para cada variable A el conjunto L[A] de
    cadenas cortas que genera, y lo va agrandando hasta que ya no cambia
    (punto fijo). como solo hay finitas cadenas de largo <= n, termina seguro.
    """
    variables = g.no_terminales()
    # al inicio ninguna variable genera nada
    lenguaje = {a: set() for a in variables}
    cambio = True
    while cambio:
        cambio = False
        for a, lados in g.producciones.items():
            for rhs in lados:
                # empezamos con la cadena vacia y vamos concatenando simbolo por simbolo
                parciales = {()}
                for s in rhs:
                    if s in variables:
                        # pegamos cada cadena que ya sabemos que genera s
                        parciales = {
                            p + w for p in parciales for w in lenguaje[s] if len(p) + len(w) <= n
                        }
                    else:
                        # terminal: se pega tal cual si no nos pasamos de n
                        parciales = {p + (s,) for p in parciales if len(p) < n}
                # lo nuevo que encontramos para A
                nuevas = parciales - lenguaje[a]
                if nuevas:
                    lenguaje[a] |= nuevas
                    cambio = True
    return lenguaje[g.inicial]


class ReconocedorExpresiones:
    """
    reconocedor descendente recursivo escrito a mano para la gramatica 1.txt:
        E -> T X        X -> + T X | ε
        T -> F Y        Y -> * F Y | ε
        F -> ( E ) | id
    esa gramatica es ll(1), asi que se puede reconocer mirando solo el
    siguiente token. no usa cnf ni cyk, por eso sirve como referencia.
    """

    def __init__(self, tokens):
        self.tokens = list(tokens)
        # posicion del siguiente token por leer
        self.pos = 0

    def actual(self):
        # el token que toca, o None si ya se acabaron
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consumir(self, esperado):
        # avanza solo si el token es el que esperamos
        if self.actual() != esperado:
            raise ValueError(f"se esperaba {esperado}")
        self.pos += 1

    def e(self):
        # E -> T X
        self.t()
        self.x()

    def x(self):
        # X -> + T X   si viene +,   si no X -> ε (no consume nada)
        if self.actual() == "+":
            self.consumir("+")
            self.t()
            self.x()

    def t(self):
        # T -> F Y
        self.f()
        self.y()

    def y(self):
        # Y -> * F Y   si viene *,   si no Y -> ε
        if self.actual() == "*":
            self.consumir("*")
            self.f()
            self.y()

    def f(self):
        # F -> ( E )  o  F -> id
        if self.actual() == "(":
            self.consumir("(")
            self.e()
            self.consumir(")")
        else:
            self.consumir("id")


def es_expresion_valida(tokens):
    # acepta si E consume todos los tokens sin error
    reconocedor = ReconocedorExpresiones(tokens)
    try:
        reconocedor.e()
    except ValueError:
        return False
    return reconocedor.pos == len(reconocedor.tokens)
