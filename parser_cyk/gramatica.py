"""
representacion de gramaticas libres de contexto (cfg).

aqui solo se guarda la gramatica y se lee desde un archivo de texto,
la conversion a cnf esta en cnf.py y el algoritmo cyk en cyk.py.

formato del archivo de gramatica:
  - una regla por linea:  A -> X Y | Z   (tambien vale la flecha unicode)
  - los simbolos van separados por espacios, asi 'NP', 'Det' o 'id' son
    UN solo simbolo y no una secuencia de letras
  - los no terminales son los simbolos que aparecen a la izquierda de alguna
    regla, todo lo demas se considera terminal
  - el simbolo inicial es el lado izquierdo de la primera regla
  - si una alternativa es solo 'e' (o 'ε') significa la cadena vacia,
    la letra e dentro de una palabra como 'beer' no se toca
  - '#' empieza un comentario hasta el final de la linea

cada lado derecho se guarda como una tupla de simbolos, por ejemplo
('NP', 'VP'), y la cadena vacia es la tupla vacia ().
"""

# la cadena vacia la representamos como una tupla sin simbolos
EPSILON = ()

# formas de escribir epsilon en el archivo (solo cuando van solas)
MARCAS_EPSILON = {"e", "ε"}


class ErrorGramatica(ValueError):
    """error que se lanza cuando el archivo de gramatica esta mal escrito."""


class Gramatica:
    """
    una gramatica = simbolo inicial + producciones.

    producciones es un diccionario que va de no terminal a un set de tuplas,
    ej: {"S": {("NP", "VP")}, "NP": {("Det", "N"), ("he",), ("she",)}}
    usamos set para que no se repitan producciones automaticamente.
    """

    def __init__(self, inicial, producciones, originales=None):
        # guardamos el simbolo inicial tal cual
        self.inicial = inicial
        # copiamos cada set para no modificar el diccionario que nos pasaron
        self.producciones = {a: set(rhs) for a, rhs in producciones.items()}
        # si el inicial no tiene producciones igual debe existir como variable
        self.producciones.setdefault(inicial, set())
        # originales = variables que venian en la gramatica de entrada,
        # las que no esten aqui son auxiliares que creo la conversion a cnf
        if originales is None:
            originales = set(self.producciones)
        # frozenset porque esto no deberia cambiar despues
        self.originales = frozenset(originales)

    # ------------------------------------------------------------ consultas

    def no_terminales(self):
        # las variables son justamente las llaves del diccionario
        return set(self.producciones)

    def terminales(self):
        # un terminal es cualquier simbolo de un lado derecho que no sea variable
        variables = self.no_terminales()
        return {
            simbolo
            for lados in self.producciones.values()  # cada set de alternativas
            for rhs in lados                          # cada alternativa (tupla)
            for simbolo in rhs                        # cada simbolo de la tupla
            if simbolo not in variables
        }

    def es_auxiliar(self, simbolo):
        # auxiliar = es variable pero no venia en la gramatica original
        return simbolo in self.producciones and simbolo not in self.originales

    def orden_variables(self):
        """orden fijo para imprimir: inicial, luego originales y al final auxiliares."""
        # todas menos el inicial, ordenadas alfabeticamente para que sea determinista
        resto = sorted(v for v in self.producciones if v != self.inicial)
        # separamos las originales de las auxiliares manteniendo el orden alfabetico
        originales = [v for v in resto if v in self.originales]
        auxiliares = [v for v in resto if v not in self.originales]
        return [self.inicial] + originales + auxiliares

    def copia(self):
        # el constructor ya copia los sets, entonces esto es una copia independiente
        return Gramatica(self.inicial, self.producciones, self.originales)

    def numero_producciones(self):
        # suma cuantas alternativas tiene cada variable
        return sum(len(lados) for lados in self.producciones.values())

    # ---------------------------------------------------- validacion de cnf

    def errores_cnf(self):
        """
        devuelve una lista con las razones por las que NO esta en cnf
        (lista vacia = si esta en cnf).

        lo que se acepta como cnf:
          - A -> B C   con B y C no terminales
          - A -> a     con a terminal
          - S -> ε     solo si S es el inicial y S no sale en ningun lado derecho
        """
        errores = []
        variables = self.no_terminales()
        # revisamos si el inicial aparece a la derecha de alguna produccion,
        # porque en ese caso no se le permite tener epsilon
        inicial_en_rhs = any(
            self.inicial in rhs for lados in self.producciones.values() for rhs in lados
        )
        # recorremos todas las producciones en orden fijo
        for a in self.orden_variables():
            for rhs in sorted(self.producciones[a]):
                # texto para que el mensaje de error diga que produccion falla
                texto = f"{a} -> {formatear_rhs(rhs)}"
                if len(rhs) == 0:
                    # caso epsilon: solo vale en el inicial y si no sale a la derecha
                    if a != self.inicial:
                        errores.append(f"ε fuera del símbolo inicial: {texto}")
                    elif inicial_en_rhs:
                        errores.append(f"{texto} pero el inicial aparece en un lado derecho")
                elif len(rhs) == 1:
                    # largo 1: debe ser terminal, si es variable es una unitaria
                    if rhs[0] in variables:
                        errores.append(f"producción unitaria: {texto}")
                elif len(rhs) == 2:
                    # largo 2: los dos tienen que ser variables
                    if not all(s in variables for s in rhs):
                        errores.append(f"terminal en producción binaria: {texto}")
                else:
                    # largo 3 o mas nunca es cnf
                    errores.append(f"lado derecho de longitud {len(rhs)}: {texto}")
        return errores

    def es_cnf(self):
        # esta en cnf si no encontramos ningun error
        return not self.errores_cnf()

    # -------------------------------------------------------------- formato

    def __str__(self):
        # una linea por variable con sus alternativas separadas por |
        lineas = []
        for a in self.orden_variables():
            alternativas = " | ".join(formatear_rhs(r) for r in sorted(self.producciones[a]))
            # si quedo sin producciones (lenguaje vacio) lo decimos explicitamente
            lineas.append(f"{a} -> {alternativas}" if alternativas else f"{a} -> (sin producciones)")
        return "\n".join(lineas)


def formatear_rhs(rhs):
    # une los simbolos con espacios, y si la tupla esta vacia pone ε
    return " ".join(rhs) if rhs else "ε"


def leer_gramatica_texto(texto):
    """arma una Gramatica a partir de un texto con el formato de arriba."""
    # lista de (lado izquierdo, alternativas) en el orden en que aparecen
    reglas = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        # quitamos el comentario y los espacios de los extremos
        linea = linea.split("#", 1)[0].strip()
        # las lineas vacias se ignoran
        if not linea:
            continue
        # partimos la linea en lado izquierdo y derecho segun la flecha
        if "->" in linea:
            izquierda, derecha = linea.split("->", 1)
        elif "→" in linea:
            izquierda, derecha = linea.split("→", 1)
        else:
            raise ErrorGramatica(f"línea {numero}: falta la flecha '->'")
        # a la izquierda tiene que haber exactamente un simbolo
        izquierda = izquierda.split()
        if len(izquierda) != 1:
            raise ErrorGramatica(f"línea {numero}: el lado izquierdo debe ser un solo símbolo")
        # cada alternativa separada por | se vuelve una tupla de simbolos
        alternativas = []
        for alternativa in derecha.split("|"):
            simbolos = alternativa.split()
            if not simbolos:
                # algo como "A -> a | | b", pedimos usar e para epsilon
                raise ErrorGramatica(f"línea {numero}: alternativa vacía (use 'e' para ε)")
            if len(simbolos) == 1 and simbolos[0] in MARCAS_EPSILON:
                # la 'e' sola es epsilon
                alternativas.append(EPSILON)
            elif any(s in MARCAS_EPSILON for s in simbolos):
                # 'a e' seria ambiguo, asi que no lo permitimos
                raise ErrorGramatica(f"línea {numero}: 'e' solo puede ir sola en una alternativa")
            else:
                alternativas.append(tuple(simbolos))
        reglas.append((izquierda[0], alternativas))

    # un archivo sin reglas no es una gramatica
    if not reglas:
        raise ErrorGramatica("la gramática no tiene reglas")

    # juntamos las reglas con el mismo lado izquierdo (pueden venir en varias lineas)
    producciones = {}
    for izquierda, alternativas in reglas:
        producciones.setdefault(izquierda, set()).update(alternativas)
    # el inicial es el lado izquierdo de la primera regla
    return Gramatica(reglas[0][0], producciones)


def leer_gramatica(ruta):
    # abre el archivo en utf-8 (por la flecha y la ε) y lo procesa
    with open(ruta, encoding="utf-8") as archivo:
        return leer_gramatica_texto(archivo.read())
