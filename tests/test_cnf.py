# pruebas de la simplificacion y conversion a cnf (cnf.py)
# las respuestas esperadas se sacaron a mano de la teoria, no del codigo

import itertools
import os
import unittest

from parser_cyk.cnf import (
    anulables,
    convertir_a_cnf,
    formatear_etapas,
    paso_epsilon,
    paso_inicio,
    paso_inutiles,
    paso_terminales,
    paso_unitarias,
)
from parser_cyk.gramatica import EPSILON, leer_gramatica, leer_gramatica_texto
from tests.oraculos import es_expresion_valida, lenguaje_acotado

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cargar(nombre):
    # lee un archivo de la carpeta gramaticas/
    return leer_gramatica(os.path.join(RAIZ, "gramaticas", nombre))


def g_(texto):
    # atajo para escribir gramaticas pequenas dentro de las pruebas
    return leer_gramatica_texto(texto)


# gramaticas de prueba que juntan todos los casos dificiles,
# se usan para comparar lenguaje original vs cnf
CASOS_EQUIVALENCIA = {
    "anulables repetidos": "S -> A a A\nA -> b | e",
    "epsilon en el lenguaje": "S -> a S b | e",
    "unitarias en cadena": "S -> A\nA -> B\nB -> C\nC -> c | c C",
    "unitarias en ciclo": "S -> A | s\nA -> B | a\nB -> A | S | b B",
    "inutiles": "S -> A B | a | S C\nA -> a A\nB -> b\nC -> c\nD -> d",
    "terminales mezclados": "S -> a B | B a\nB -> b",
    "producciones largas": "S -> A B C D | A B C\nA -> a\nB -> b\nC -> c\nD -> d",
    "todo junto": "S -> A S B | x A y\nA -> a A | e\nB -> S | b | e",
    "inicial solo ε": "S -> e",
    "parentesis balanceados": "S -> ( S ) S | e",
}


class PruebasPasosSueltos(unittest.TestCase):
    def test_inicio_solo_si_hace_falta(self):
        # S no sale a la derecha: no se agrega nada
        g, _ = paso_inicio(g_("S -> A B\nA -> a\nB -> b"))
        self.assertEqual(g.inicial, "S")
        # S sale a la derecha: se crea S0 -> S y S0 queda como auxiliar
        g, _ = paso_inicio(g_("S -> a S | b"))
        self.assertEqual(g.inicial, "S0")
        self.assertEqual(g.producciones["S0"], {("S",)})
        self.assertTrue(g.es_auxiliar("S0"))

    def test_anulables(self):
        # A tiene ε, B -> A A tambien es anulable, C no, S necesita C asi que no
        g = g_("S -> A B C | a\nA -> a | e\nB -> A A\nC -> c")
        self.assertEqual(anulables(g), {"A", "B"})

    def test_combinaciones_de_anulables_repetidos(self):
        # cada A se puede quitar por separado: A a A, a A, A a, a
        g, _ = paso_epsilon(g_("S -> A a A\nA -> b | e"))
        self.assertEqual(g.producciones["S"], {("A", "a", "A"), ("a", "A"), ("A", "a"), ("a",)})
        # A pierde su ε y S no la recibe porque S no es anulable
        self.assertEqual(g.producciones["A"], {("b",)})

    def test_epsilon_se_queda_solo_en_el_inicial(self):
        g, _ = paso_epsilon(g_("S -> A B\nA -> a | e\nB -> b | e"))
        self.assertIn(EPSILON, g.producciones["S"])
        self.assertNotIn(EPSILON, g.producciones["A"])
        self.assertNotIn(EPSILON, g.producciones["B"])

    def test_unitarias_encadenadas(self):
        # S -> A -> B -> C -> c, entonces todos terminan con C -> c
        g, _ = paso_unitarias(g_("S -> A\nA -> B\nB -> C\nC -> c"))
        for variable in "SABC":
            self.assertEqual(g.producciones[variable], {("c",)})

    def test_unitarias_ciclicas(self):
        # S -> A -> B -> S es un ciclo, los tres se alcanzan entre si
        g, _ = paso_unitarias(g_("S -> A | s\nA -> B | a\nB -> A | S | b"))
        for variable in "SAB":
            self.assertEqual(g.producciones[variable], {("s",), ("a",), ("b",)})

    def test_terminal_no_es_unitaria(self):
        # S -> word es terminal y se queda; S -> A si es unitaria
        g, _ = paso_unitarias(g_("S -> A | word\nA -> otra"))
        self.assertEqual(g.producciones["S"], {("word",), ("otra",)})

    def test_inutiles(self):
        # A -> a A nunca termina (no generador), entonces se va S -> A B,
        # y despues B, C y D quedan inalcanzables
        g, _ = paso_inutiles(g_("S -> A B | a\nA -> a A\nB -> b\nC -> c\nD -> d"))
        self.assertEqual(g.producciones, {"S": {("a",)}})

    def test_orden_no_generador_antes_que_inalcanzable(self):
        # B solo es alcanzable a traves de S -> A B, que se borra porque A no genera
        g, _ = paso_inutiles(g_("S -> A B | c\nA -> a A\nB -> b"))
        self.assertNotIn("B", g.producciones)

    def test_terminales_mezclados(self):
        g, _ = paso_terminales(g_("S -> a B | b\nB -> b"))
        self.assertEqual(g.producciones["S"], {("T_a", "B"), ("b",)})
        self.assertEqual(g.producciones["T_a"], {("a",)})
        # B -> b tiene largo 1 y no se toca
        self.assertEqual(g.producciones["B"], {("b",)})


class PruebasConversionCompleta(unittest.TestCase):
    def test_producciones_largas(self):
        g, _ = convertir_a_cnf(g_("S -> A B C D\nA -> a\nB -> b\nC -> c\nD -> d"))
        # S -> A S_1, S_1 -> B S_2, S_2 -> C D
        self.assertEqual(g.producciones["S"], {("A", "S_1")})
        self.assertEqual(g.producciones["S_1"], {("B", "S_2")})
        self.assertEqual(g.producciones["S_2"], {("C", "D")})
        self.assertTrue(g.es_cnf())

    def test_sufijos_iguales_comparten_auxiliar(self):
        # A B C y D B C terminan igual (B C), asi que se usa una sola auxiliar
        g, _ = convertir_a_cnf(g_("S -> A B C | D B C\nA -> a\nB -> b\nC -> c\nD -> d"))
        self.assertEqual(g.producciones["S"], {("A", "S_1"), ("D", "S_1")})
        self.assertEqual(g.producciones["S_1"], {("B", "C")})

    def test_epsilon_en_el_lenguaje(self):
        # S -> a S b | e genera ε, y S sale a la derecha, entonces S0 -> ε
        g, _ = convertir_a_cnf(g_("S -> a S b | e"))
        self.assertEqual(g.inicial, "S0")
        self.assertIn(EPSILON, g.producciones["S0"])
        self.assertTrue(g.es_cnf())

    def test_lenguaje_vacio(self):
        # A nunca termina, el lenguaje es vacio y la cnf queda sin producciones
        g, _ = convertir_a_cnf(g_("S -> A\nA -> a A"))
        self.assertEqual(g.producciones, {"S": set()})
        self.assertTrue(g.es_cnf())
        self.assertEqual(lenguaje_acotado(g, 5), set())

    def test_nombres_sin_colision(self):
        # ya existe una variable S0 y otra T_a, los nombres nuevos no las pisan
        g, _ = convertir_a_cnf(g_("S -> a S T_a | e\nT_a -> t\nS0 -> s"))
        self.assertEqual(g.inicial, "S0_1")
        self.assertEqual(g.producciones["T_a"], {("t",)})
        self.assertEqual(g.producciones["T_a_1"], {("a",)})
        self.assertTrue(g.es_cnf())

    def test_variables_originales_y_auxiliares(self):
        g, _ = convertir_a_cnf(cargar("expresiones.txt"))
        # las originales siguen marcadas como originales
        for variable in "ETFXY":
            self.assertFalse(g.es_auxiliar(variable))
        # E0 y las T_... son auxiliares
        self.assertTrue(g.es_auxiliar("E0"))
        self.assertTrue(g.es_auxiliar("T_MAS"))

    def test_ingles_no_cambia(self):
        # la gramatica del enunciado ya esta en cnf y S no sale a la derecha,
        # entonces la conversion la debe dejar exactamente igual
        original = cargar("ingles.txt")
        g, _ = convertir_a_cnf(original)
        self.assertEqual(g.inicial, "S")
        self.assertEqual(g.producciones, original.producciones)
        self.assertFalse(any(g.es_auxiliar(v) for v in g.no_terminales()))

    def test_expresiones_estructura(self):
        g, _ = convertir_a_cnf(cargar("expresiones.txt"))
        self.assertTrue(g.es_cnf())
        # convencion estricta: E sale en F -> ( E ), por eso hay inicial nuevo
        self.assertEqual(g.inicial, "E0")
        # ε no esta en el lenguaje de expresiones
        self.assertNotIn(EPSILON, g.producciones["E0"])

    def test_es_determinista(self):
        # convertir dos veces debe dar exactamente el mismo texto
        a, _ = convertir_a_cnf(cargar("expresiones.txt"))
        b, _ = convertir_a_cnf(cargar("expresiones.txt"))
        self.assertEqual(str(a), str(b))

    def test_etapas(self):
        _, etapas = convertir_a_cnf(cargar("expresiones.txt"))
        # original + 6 pasos + validacion
        self.assertEqual(len(etapas), 8)
        texto = formatear_etapas(etapas)
        self.assertIn("anulables: X, Y", texto)
        self.assertIn("nuevo inicial E0 -> E", texto)


class PruebasEquivalencia(unittest.TestCase):
    """
    comparamos el lenguaje de la gramatica original contra el de la cnf hasta
    cierto largo usando el oraculo lenguaje_acotado. esto es evidencia fuerte,
    pero no es una demostracion para cadenas de cualquier largo.
    """

    def test_casos_varios(self):
        for nombre, texto in CASOS_EQUIVALENCIA.items():
            with self.subTest(caso=nombre):
                original = g_(texto)
                cnf, _ = convertir_a_cnf(original)
                self.assertTrue(cnf.es_cnf())
                self.assertEqual(lenguaje_acotado(original, 7), lenguaje_acotado(cnf, 7))

    def test_expresiones_contra_original_y_referencia(self):
        original = cargar("expresiones.txt")
        referencia = cargar("expresiones_cnf_referencia.txt")
        cnf, _ = convertir_a_cnf(original)
        n = 7
        lenguaje = lenguaje_acotado(cnf, n)
        # mismo lenguaje que 1.txt y que 1-cnf.txt hasta largo 7
        self.assertEqual(lenguaje, lenguaje_acotado(original, n))
        self.assertEqual(lenguaje, lenguaje_acotado(referencia, n))
        # y tambien coincide con el reconocedor hecho a mano, cadena por cadena,
        # para todas las combinaciones de los 5 terminales de largo 1 a 7
        terminales = ["id", "+", "*", "(", ")"]
        for largo in range(1, n + 1):
            for cadena in itertools.product(terminales, repeat=largo):
                self.assertEqual(cadena in lenguaje, es_expresion_valida(cadena), cadena)

    def test_ejemplos_de_expresiones(self):
        cnf, _ = convertir_a_cnf(cargar("expresiones.txt"))
        lenguaje = lenguaje_acotado(cnf, 7)
        # validas: se derivan a mano de E -> T X, T -> F Y, F -> ( E ) | id
        for valida in ["id", "id + id * id", "( id + id ) * id"]:
            self.assertIn(tuple(valida.split()), lenguaje)
        # invalidas: operador sin operando, parentesis sin cerrar, dos id seguidos
        for invalida in ["id +", "( id", "id id", ") id (", "+"]:
            self.assertNotIn(tuple(invalida.split()), lenguaje)

    def test_ingles_frases(self):
        cnf, _ = convertir_a_cnf(cargar("ingles.txt"))
        lenguaje = lenguaje_acotado(cnf, 5)
        self.assertIn(("he", "cooks"), lenguaje)
        self.assertIn(("the", "cat", "drinks", "the", "beer"), lenguaje)
        self.assertNotIn(("cooks", "he"), lenguaje)


if __name__ == "__main__":
    unittest.main()
