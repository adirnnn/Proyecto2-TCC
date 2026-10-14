import os
import unittest

from parser_cyk.gramatica import (
    EPSILON,
    ErrorGramatica,
    Gramatica,
    leer_gramatica,
    leer_gramatica_texto,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta_gramatica(nombre):
    return os.path.join(RAIZ, "gramaticas", nombre)


class PruebasLectura(unittest.TestCase):
    def test_gramatica_ingles(self):
        g = leer_gramatica(ruta_gramatica("ingles.txt"))
        self.assertEqual(g.inicial, "S")
        self.assertEqual(g.no_terminales(), {"S", "VP", "PP", "NP", "V", "P", "N", "Det"})
        # Los nombres de varias letras son un solo símbolo.
        self.assertEqual(g.producciones["S"], {("NP", "VP")})
        self.assertIn(("Det", "N"), g.producciones["NP"])
        self.assertEqual(len(g.producciones["N"]), 11)
        self.assertEqual(
            g.producciones["VP"],
            {("VP", "PP"), ("V", "NP"), ("cooks",), ("drinks",), ("eats",), ("cuts",)},
        )
        self.assertIn("beer", g.terminales())
        self.assertEqual(g.numero_producciones(), 1 + 6 + 1 + 3 + 4 + 2 + 11 + 2)

    def test_gramatica_expresiones_e_es_epsilon(self):
        g = leer_gramatica(ruta_gramatica("expresiones.txt"))
        self.assertEqual(g.inicial, "E")
        self.assertEqual(g.producciones["X"], {("+", "T", "X"), EPSILON})
        self.assertEqual(g.producciones["Y"], {("*", "F", "Y"), EPSILON})
        self.assertEqual(g.producciones["F"], {("(", "E", ")"), ("id",)})
        self.assertEqual(g.terminales(), {"+", "*", "(", ")", "id"})
        self.assertNotIn("e", g.terminales())

    def test_e_dentro_de_palabra_no_es_epsilon(self):
        g = leer_gramatica_texto("N -> beer | e | ε\n")
        self.assertEqual(g.producciones["N"], {("beer",), EPSILON})

    def test_flecha_unicode_y_reglas_repetidas(self):
        g = leer_gramatica_texto("A → a\nA -> b B # comentario\nB -> b\n")
        self.assertEqual(g.inicial, "A")
        self.assertEqual(g.producciones["A"], {("a",), ("b", "B")})

    def test_errores_de_formato(self):
        for texto in ["", "A a", "A B -> a", "A -> a | | b", "A -> a e"]:
            with self.subTest(texto=texto):
                with self.assertRaises(ErrorGramatica):
                    leer_gramatica_texto(texto)


class PruebasValidacionCNF(unittest.TestCase):
    def test_ingles_ya_esta_en_cnf(self):
        self.assertTrue(leer_gramatica(ruta_gramatica("ingles.txt")).es_cnf())

    def test_referencia_expresiones_esta_en_cnf(self):
        self.assertTrue(leer_gramatica(ruta_gramatica("expresiones_cnf_referencia.txt")).es_cnf())

    def test_expresiones_original_no_esta_en_cnf(self):
        errores = leer_gramatica(ruta_gramatica("expresiones.txt")).errores_cnf()
        self.assertTrue(any("ε" in e for e in errores))
        self.assertTrue(any("longitud 3" in e for e in errores))

    def test_casos_que_violan_cnf(self):
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
        g = Gramatica("S0", {"S0": {EPSILON, ("A", "A")}, "A": {("a",)}})
        self.assertTrue(g.es_cnf())

    def test_auxiliares_y_formato(self):
        g = Gramatica("S", {"S": {("A", "T_b")}, "A": {("a",)}, "T_b": {("b",)}},
                      originales={"S", "A"})
        self.assertTrue(g.es_auxiliar("T_b"))
        self.assertFalse(g.es_auxiliar("A"))
        self.assertEqual(str(g).splitlines(), ["S -> A T_b", "A -> a", "T_b -> b"])


if __name__ == "__main__":
    unittest.main()
