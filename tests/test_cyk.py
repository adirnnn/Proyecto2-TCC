# pruebas del algoritmo cyk y del arbol de analisis (cyk.py)
# lo esperado se justifica a mano con la gramatica del enunciado, no con el codigo

import itertools
import os
import unittest

from parser_cyk.cnf import convertir_a_cnf
from parser_cyk.cyk import cyk, dibujar_arbol, formatear_tabla, normalizar
from parser_cyk.gramatica import leer_gramatica, leer_gramatica_texto
from tests.oraculos import es_expresion_valida

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cargar(nombre):
    # lee una gramatica de gramaticas/
    return leer_gramatica(os.path.join(RAIZ, "gramaticas", nombre))


# las dos gramaticas ya convertidas, se calculan una sola vez
INGLES, _ = convertir_a_cnf(cargar("ingles.txt"))
EXPRESIONES, _ = convertir_a_cnf(cargar("expresiones.txt"))
REFERENCIA = cargar("expresiones_cnf_referencia.txt")


def analizar(g, frase):
    # atajo: normaliza la frase y corre cyk
    return cyk(g, normalizar(frase))


class VerificarArbol:
    """mezcla con un metodo que revisa que un arbol sea valido para la gramatica."""

    def verificar_arbol(self, g, resultado):
        arbol = resultado.arbol
        self.assertIsNotNone(arbol)
        # la raiz es el inicial
        self.assertEqual(arbol.simbolo, g.inicial)
        # las hojas leidas de izquierda a derecha son exactamente los tokens
        self.assertEqual(arbol.hojas(), resultado.tokens)
        # cada nodo interno respeta alguna produccion de la gramatica cnf
        pendientes = [arbol]
        while pendientes:
            nodo = pendientes.pop()
            if nodo.terminal:
                continue
            hijos = tuple(h.simbolo for h in nodo.hijos)
            self.assertIn(hijos, g.producciones[nodo.simbolo],
                          f"{nodo.simbolo} -> {hijos} no es produccion")
            pendientes.extend(nodo.hijos)


class PruebasNormalizacion(unittest.TestCase):
    def test_minusculas_y_espacios(self):
        self.assertEqual(normalizar("  She   EATS a  cake "), ["she", "eats", "a", "cake"])

    def test_puntuacion_no_se_borra(self):
        # el punto queda pegado y forma un token distinto
        self.assertEqual(normalizar("he cooks."), ["he", "cooks."])

    def test_vacia(self):
        self.assertEqual(normalizar("   "), [])


class PruebasIngles(VerificarArbol, unittest.TestCase):
    def test_ejemplos_oficiales(self):
        # she eats a cake with a fork:
        #   NP=she, VP=(VP=(V=eats NP=(a cake)) PP=(with NP=(a fork)))
        # the cat drinks the beer:
        #   NP=(the cat), VP=(V=drinks NP=(the beer))
        for frase in ["She eats a cake with a fork", "The cat drinks the beer"]:
            with self.subTest(frase=frase):
                r = analizar(INGLES, frase)
                self.assertTrue(r.aceptada)
                self.verificar_arbol(INGLES, r)

    def test_frase_corta(self):
        # S -> NP VP con NP -> he y VP -> cooks
        r = analizar(INGLES, "he cooks")
        self.assertTrue(r.aceptada)
        self.assertEqual(r.arbol.parentizado(), "(S (NP he) (VP cooks))")

    def test_valida_pero_sin_sentido(self):
        # sintacticamente es NP V NP aunque un tenedor no beba hornos
        r = analizar(INGLES, "the fork drinks the oven")
        self.assertTrue(r.aceptada)
        self.verificar_arbol(INGLES, r)

    def test_varios_pp(self):
        # VP -> VP PP se puede aplicar varias veces
        r = analizar(INGLES, "he cuts the meat with a knife in the oven")
        self.assertTrue(r.aceptada)
        self.verificar_arbol(INGLES, r)

    def test_rechazadas(self):
        casos = {
            # el verbo antes del sujeto no encaja con S -> NP VP
            "orden invalido": "eats she a cake",
            # Det N sin verbo: falta el VP
            "incompleta": "the cat",
            # falta el NP despues de with (PP -> P NP)
            "pp incompleto": "she eats with",
            # pizza no es terminal de la gramatica
            "palabra desconocida": "she eats a pizza",
            # dos determinantes seguidos no los genera nadie
            "doble det": "the a cat cooks",
        }
        for nombre, frase in casos.items():
            with self.subTest(caso=nombre):
                r = analizar(INGLES, frase)
                self.assertFalse(r.aceptada)
                self.assertIsNone(r.arbol)

    def test_desconocidas_se_reportan(self):
        r = analizar(INGLES, "she eats a pizza")
        self.assertEqual(r.desconocidos, ["pizza"])

    def test_mayusculas_y_espacios_extra(self):
        r = analizar(INGLES, "   THE   Cat   drinks THE beer  ")
        self.assertTrue(r.aceptada)
        self.verificar_arbol(INGLES, r)

    def test_puntuacion_se_rechaza(self):
        # 'beer.' no es la palabra 'beer', se rechaza y se avisa
        r = analizar(INGLES, "The cat drinks the beer.")
        self.assertFalse(r.aceptada)
        self.assertEqual(r.desconocidos, ["beer."])

    def test_vacia_no_pertenece(self):
        # la gramatica del ingles no genera ε (S -> NP VP siempre pone palabras)
        r = analizar(INGLES, "")
        self.assertFalse(r.aceptada)
        self.assertIsNone(r.arbol)

    def test_tabla(self):
        r = analizar(INGLES, "he cooks")
        # celda de 'cooks': VP y V; celda de la frase completa: S
        self.assertEqual(set(r.tabla[1][1]), {"V", "VP"})
        self.assertEqual(set(r.tabla[0][2]), {"S"})
        self.assertIn("[0,2] 'he cooks': {S}", formatear_tabla(r))

    def test_dibujo(self):
        r = analizar(INGLES, "he cooks")
        self.assertEqual(dibujar_arbol(r.arbol, INGLES).splitlines(), [
            "S",
            "|-- NP",
            '|   `-- "he"',
            "`-- VP",
            '    `-- "cooks"',
        ])


class PruebasExpresiones(VerificarArbol, unittest.TestCase):
    def test_validas(self):
        for frase in ["id", "id + id * id", "( id + id ) * id"]:
            with self.subTest(frase=frase):
                r = analizar(EXPRESIONES, frase)
                self.assertTrue(r.aceptada)
                self.verificar_arbol(EXPRESIONES, r)

    def test_invalidas(self):
        for frase in ["id +", "( id", "id id", ") id (", "* id", "( )"]:
            with self.subTest(frase=frase):
                self.assertFalse(analizar(EXPRESIONES, frase).aceptada)

    def test_auxiliares_marcados_en_el_arbol(self):
        # ( id ) usa T_PAR_IZQ y E0_1, que son auxiliares de la cnf
        r = analizar(EXPRESIONES, "( id )")
        dibujo = dibujar_arbol(r.arbol, EXPRESIONES)
        self.assertIn("T_PAR_IZQ*", dibujo)
        self.assertIn("E0_1*", dibujo)

    def test_contra_referencia_y_reconocedor(self):
        # todas las cadenas de los 5 terminales de largo 1 a 6 (19530 cadenas):
        # nuestra cnf, la cnf de referencia y el reconocedor a mano deben coincidir
        terminales = ["id", "+", "*", "(", ")"]
        aceptadas = 0
        for largo in range(1, 7):
            for cadena in itertools.product(terminales, repeat=largo):
                tokens = list(cadena)
                esperado = es_expresion_valida(tokens)
                self.assertEqual(cyk(EXPRESIONES, tokens).aceptada, esperado, cadena)
                self.assertEqual(cyk(REFERENCIA, tokens).aceptada, esperado, cadena)
                aceptadas += esperado
        # control de que la prueba no es trivial (no todo rechazado)
        self.assertGreater(aceptadas, 10)


class PruebasCasosBorde(VerificarArbol, unittest.TestCase):
    def test_epsilon_aceptada(self):
        # S -> a S b | e genera la cadena vacia
        g, _ = convertir_a_cnf(leer_gramatica_texto("S -> a S b | e"))
        r = cyk(g, [])
        self.assertTrue(r.aceptada)
        self.assertEqual(r.arbol.parentizado(), "(S0 ε)")
        # y tambien a a b b, pero no a b b
        self.assertTrue(cyk(g, ["a", "a", "b", "b"]).aceptada)
        self.assertFalse(cyk(g, ["a", "b", "b"]).aceptada)

    def test_ambigua_da_un_arbol_fijo(self):
        # S -> S S | a con "a a a" tiene dos arboles: (a a) a  y  a (a a).
        # cyk guarda el primer puntero que encuentra (k mas chico primero),
        # entonces siempre sale a (a a): S -> S S con k = 1
        g, _ = convertir_a_cnf(leer_gramatica_texto("S -> S S | a"))
        r = cyk(g, ["a", "a", "a"])
        self.assertTrue(r.aceptada)
        self.verificar_arbol(g, r)
        self.assertEqual(r.arbol.parentizado(), "(S0 (S a) (S (S a) (S a)))")

    def test_lenguaje_vacio(self):
        g, _ = convertir_a_cnf(leer_gramatica_texto("S -> A\nA -> a A"))
        self.assertFalse(cyk(g, ["a"]).aceptada)
        self.assertFalse(cyk(g, []).aceptada)


if __name__ == "__main__":
    unittest.main()
