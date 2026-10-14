"""Representación de gramáticas libres de contexto (CFG).

Convenciones del formato de archivo:
  * Una regla por línea:  A -> X Y | Z   (también se acepta la flecha '→').
  * Los símbolos se separan con espacios: 'NP', 'Det' o 'id' son UN símbolo.
  * Los no terminales son los símbolos que aparecen a la izquierda de alguna
    regla; cualquier otro símbolo es terminal.
  * El símbolo inicial es el lado izquierdo de la primera regla.
  * Una alternativa formada únicamente por 'e' o 'ε' representa la cadena
    vacía. La letra 'e' dentro de una palabra (p. ej. 'beer') no se toca.
  * '#' inicia un comentario hasta el final de la línea.

Cada lado derecho se guarda como una tupla de símbolos; la cadena vacía es
la tupla vacía ().
"""

EPSILON = ()
MARCAS_EPSILON = {"e", "ε"}


class ErrorGramatica(ValueError):
    """Error de formato o de estructura de una gramática."""


class Gramatica:
    def __init__(self, inicial, producciones, originales=None):
        self.inicial = inicial
        # dict: no terminal -> set de tuplas (lados derechos)
        self.producciones = {a: set(rhs) for a, rhs in producciones.items()}
        self.producciones.setdefault(inicial, set())
        # Variables de la gramática original; las demás son auxiliares
        # introducidas por la conversión.
        if originales is None:
            originales = set(self.producciones)
        self.originales = frozenset(originales)

    # ------------------------------------------------------------ consultas
    def no_terminales(self):
        return set(self.producciones)

    def terminales(self):
        variables = self.no_terminales()
        return {
            simbolo
            for lados in self.producciones.values()
            for rhs in lados
            for simbolo in rhs
            if simbolo not in variables
        }

    def es_auxiliar(self, simbolo):
        return simbolo in self.producciones and simbolo not in self.originales

    def orden_variables(self):
        """Inicial primero, luego originales y auxiliares en orden alfabético."""
        resto = sorted(v for v in self.producciones if v != self.inicial)
        originales = [v for v in resto if v in self.originales]
        auxiliares = [v for v in resto if v not in self.originales]
        return [self.inicial] + originales + auxiliares

    def copia(self):
        return Gramatica(self.inicial, self.producciones, self.originales)

    def numero_producciones(self):
        return sum(len(lados) for lados in self.producciones.values())

    # ---------------------------------------------------- validación de CNF
    def errores_cnf(self):
        """Lista de motivos por los que la gramática NO está en CNF.

        CNF aceptada: A -> B C (B, C no terminales), A -> a (terminal), y
        opcionalmente S -> ε solo si S es el inicial y no aparece en ningún
        lado derecho.
        """
        errores = []
        variables = self.no_terminales()
        inicial_en_rhs = any(
            self.inicial in rhs for lados in self.producciones.values() for rhs in lados
        )
        for a in self.orden_variables():
            for rhs in sorted(self.producciones[a]):
                texto = f"{a} -> {formatear_rhs(rhs)}"
                if len(rhs) == 0:
                    if a != self.inicial:
                        errores.append(f"ε fuera del símbolo inicial: {texto}")
                    elif inicial_en_rhs:
                        errores.append(f"{texto} pero el inicial aparece en un lado derecho")
                elif len(rhs) == 1:
                    if rhs[0] in variables:
                        errores.append(f"producción unitaria: {texto}")
                elif len(rhs) == 2:
                    if not all(s in variables for s in rhs):
                        errores.append(f"terminal en producción binaria: {texto}")
                else:
                    errores.append(f"lado derecho de longitud {len(rhs)}: {texto}")
        return errores

    def es_cnf(self):
        return not self.errores_cnf()

    # -------------------------------------------------------------- formato
    def __str__(self):
        lineas = []
        for a in self.orden_variables():
            alternativas = " | ".join(formatear_rhs(r) for r in sorted(self.producciones[a]))
            lineas.append(f"{a} -> {alternativas}" if alternativas else f"{a} -> (sin producciones)")
        return "\n".join(lineas)


def formatear_rhs(rhs):
    return " ".join(rhs) if rhs else "ε"


def leer_gramatica_texto(texto):
    """Construye una Gramatica a partir del texto con el formato descrito arriba."""
    reglas = []  # (lado izquierdo, lista de alternativas), en orden de aparición
    for numero, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        if "->" in linea:
            izquierda, derecha = linea.split("->", 1)
        elif "→" in linea:
            izquierda, derecha = linea.split("→", 1)
        else:
            raise ErrorGramatica(f"línea {numero}: falta la flecha '->'")
        izquierda = izquierda.split()
        if len(izquierda) != 1:
            raise ErrorGramatica(f"línea {numero}: el lado izquierdo debe ser un solo símbolo")
        alternativas = []
        for alternativa in derecha.split("|"):
            simbolos = alternativa.split()
            if not simbolos:
                raise ErrorGramatica(f"línea {numero}: alternativa vacía (use 'e' para ε)")
            if len(simbolos) == 1 and simbolos[0] in MARCAS_EPSILON:
                alternativas.append(EPSILON)
            elif any(s in MARCAS_EPSILON for s in simbolos):
                raise ErrorGramatica(f"línea {numero}: 'e' solo puede ir sola en una alternativa")
            else:
                alternativas.append(tuple(simbolos))
        reglas.append((izquierda[0], alternativas))

    if not reglas:
        raise ErrorGramatica("la gramática no tiene reglas")

    producciones = {}
    for izquierda, alternativas in reglas:
        producciones.setdefault(izquierda, set()).update(alternativas)
    return Gramatica(reglas[0][0], producciones)


def leer_gramatica(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return leer_gramatica_texto(archivo.read())
