# pruebas de la lectura de gramaticas y de la validacion de cnf (gramatica.py)

import os
import unittest

from parser_cyk.gramatica import (
    EPSILON,
    ErrorGramatica,
    Gramatica,
    leer_gramatica,
    leer_gramatica_texto,
)

# carpeta raiz del proyecto (la de arriba de tests/)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta_gramatica(nombre):
    # arma la ruta a un archivo dentro de gramaticas/
    return os.path.join(RAIZ, "gramaticas", nombre)


class PruebasLectura(unittest.TestCase):
    def test_gramatica_ingles(self):
        g = leer_gramatica(ruta_gramatica("ingles.txt"))
        # el inicial es el de la primera regla
        self.assertEqual(g.inicial, "S")
        # las 8 variables del enunciado, cada una como un solo simbolo
        self.assertEqual(g.no_terminales(), {"S", "VP", "PP", "NP", "V", "P", "N", "Det"})
        # NP y VP no se parten en letras sueltas
        self.assertEqual(g.producciones["S"], {("NP", "VP")})
        self.assertIn(("Det", "N"), g.producciones["NP"])
        # N tiene los 11 sustantivos del enunciado
        self.assertEqual(len(g.producciones["N"]), 11)
        self.assertEqual(
            g.producciones["VP"],
            {("VP", "PP"), ("V", "NP"), ("cooks",), ("drinks",), ("eats",), ("cuts",)},
        )
        # beer es terminal y su letra e no se convirtio en epsilon
        self.assertIn("beer", g.terminales())
        # conteo a mano: S1 + VP6 + PP1 + NP3 + V4 + P2 + N11 + Det2
        self.assertEqual(g.numero_producciones(), 1 + 6 + 1 + 3 + 4 + 2 + 11 + 2)

    def test_gramatica_expresiones_e_es_epsilon(self):
        g = leer_gramatica(ruta_gramatica("expresiones.txt"))
        self.assertEqual(g.inicial, "E")
        # en 1.txt la 'e' sola de X y Y es epsilon
        self.assertEqual(g.producciones["X"], {("+", "T", "X"), EPSILON})
        self.assertEqual(g.producciones["Y"], {("*", "F", "Y"), EPSILON})
        self.assertEqual(g.producciones["F"], {("(", "E", ")"), ("id",)})
        # 'id' es un solo terminal y 'e' no quedo como terminal
        self.assertEqual(g.terminales(), {"+", "*", "(", ")", "id"})
        self.assertNotIn("e", g.terminales())

    def test_e_dentro_de_palabra_no_es_epsilon(self):
        # beer se queda igual, e y ε solas son la misma cadena vacia
        g = leer_gramatica_texto("N -> beer | e | ε\n")
        self.assertEqual(g.producciones["N"], {("beer",), EPSILON})

    def test_flecha_unicode_y_reglas_repetidas(self):
        # se aceptan las dos flechas, comentarios y reglas de A en varias lineas
        g = leer_gramatica_texto("A → a\nA -> b B # comentario\nB -> b\n")
        self.assertEqual(g.inicial, "A")
        self.assertEqual(g.producciones["A"], {("a",), ("b", "B")})

    def test_errores_de_formato(self):
        # vacio, sin flecha, dos simbolos a la izquierda, alternativa vacia, e mezclada
        for texto in ["", "A a", "A B -> a", "A -> a | | b", "A -> a e"]:
            with self.subTest(texto=texto):
                with self.assertRaises(ErrorGramatica):
                    leer_gramatica_texto(texto)


class PruebasValidacionCNF(unittest.TestCase):
    def test_ingles_ya_esta_en_cnf(self):
        # todas sus reglas son A -> B C o A -> palabra
        self.assertTrue(leer_gramatica(ruta_gramatica("ingles.txt")).es_cnf())

    def test_referencia_expresiones_esta_en_cnf(self):
        # 1-cnf.txt debe pasar la validacion (el inicial E sale a la derecha pero no tiene ε)
        self.assertTrue(leer_gramatica(ruta_gramatica("expresiones_cnf_referencia.txt")).es_cnf())

    def test_expresiones_original_no_esta_en_cnf(self):
        errores = leer_gramatica(ruta_gramatica("expresiones.txt")).errores_cnf()
        # tiene epsilon en X y Y, y producciones de largo 3
        self.assertTrue(any("ε" in e for e in errores))
        self.assertTrue(any("longitud 3" in e for e in errores))

    def test_casos_que_violan_cnf(self):
        # un caso por cada tipo de violacion
        casos = {
            "unitaria": "S -> A\nA -> a",
            "terminal en binaria": "S -> a A\nA -> a",
            "larga": "S -> A A A\nA -> a",
            "ε fuera del inicial": "S -> A A\nA -> a | e",
            "ε con inicial en rhs": "S -> S S | a | e",
        }
        for nombre, texto in casos.items():
            with self.subTest(caso=nombre):
                self.assertFalse(leer_gramatica_texto(texto).es_cnf())

    def test_epsilon_permitido_en_inicial_nuevo(self):
        # S0 -> ε esta bien porque S0 no sale en ningun lado derecho
        g = Gramatica("S0", {"S0": {EPSILON, ("A", "A")}, "A": {("a",)}})
        self.assertTrue(g.es_cnf())

    def test_auxiliares_y_formato(self):
        # T_b no esta en originales, entonces cuenta como auxiliar
        g = Gramatica("S", {"S": {("A", "T_b")}, "A": {("a",)}, "T_b": {("b",)}},
                      originales={"S", "A"})
        self.assertTrue(g.es_auxiliar("T_b"))
        self.assertFalse(g.es_auxiliar("A"))
        # se imprime inicial, originales y luego auxiliares
        self.assertEqual(str(g).splitlines(), ["S -> A T_b", "A -> a", "T_b -> b"])


if __name__ == "__main__":
    unittest.main()
