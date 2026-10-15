# pruebas de la interfaz (main.py) ejecutandola de verdad como programa aparte

import os
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(RAIZ, "main.py")


def ejecutar(*argumentos, entrada=None, carpeta=RAIZ):
    # corre "python main.py ..." y devuelve (codigo de salida, texto impreso)
    proceso = subprocess.run(
        [sys.executable, MAIN, *argumentos],
        input=entrada.encode("utf-8") if entrada is not None else None,
        capture_output=True,
        cwd=carpeta,
    )
    # main.py fuerza utf-8, asi que decodificamos igual
    return proceso.returncode, proceso.stdout.decode("utf-8") + proceso.stderr.decode("utf-8")


class PruebasInterfaz(unittest.TestCase):
    def test_frase_por_teclado(self):
        # el flujo normal solo pide la frase
        codigo, salida = ejecutar(entrada="She eats a cake with a fork\n")
        self.assertEqual(codigo, 0)
        self.assertIn("Ingrese la frase:", salida)
        self.assertIn("Resultado: SÍ", salida)
        self.assertIn("Tiempo de validación CYK:", salida)
        self.assertIn('"fork"', salida)
        # la cnf del ingles es igual a la original
        self.assertIn("idéntica a la gramática original", salida)

    def test_frase_por_opcion(self):
        codigo, salida = ejecutar("--frase", "The cat drinks the beer")
        self.assertEqual(codigo, 0)
        self.assertIn("Frase normalizada: the cat drinks the beer", salida)
        self.assertIn("Resultado: SÍ", salida)
        self.assertIn("(S (NP (Det the) (N cat))", salida)

    def test_rechazada_con_desconocida(self):
        codigo, salida = ejecutar("--frase", "She eats a pizza.")
        self.assertEqual(codigo, 0)
        self.assertIn("Resultado: NO", salida)
        self.assertIn("Tokens desconocidos (no son terminales de la gramática): pizza.", salida)
        self.assertIn("No existe árbol", salida)
        # aunque se rechace, el tiempo se mide igual
        self.assertIn("Tiempo de validación CYK:", salida)

    def test_entrada_con_bom(self):
        # powershell manda "﻿" al inicio cuando se usa un pipe,
        # no debe pegarse a la primera palabra
        codigo, salida = ejecutar(entrada="﻿he cooks\n")
        self.assertEqual(codigo, 0)
        self.assertIn("Frase normalizada: he cooks", salida)
        self.assertIn("Resultado: SÍ", salida)

    def test_entrada_vacia(self):
        # la gramatica de ingles no genera ε, entonces la vacia es NO
        codigo, salida = ejecutar(entrada="\n")
        self.assertEqual(codigo, 0)
        self.assertIn("Frase normalizada: (vacía)", salida)
        self.assertIn("Resultado: NO", salida)

    def test_etapas_y_tabla_con_expresiones(self):
        codigo, salida = ejecutar(
            "--gramatica", os.path.join("gramaticas", "expresiones.txt"),
            "--etapas", "--tabla", "--frase", "( id + id ) * id",
        )
        self.assertEqual(codigo, 0)
        # se imprimen las etapas (con ε, que antes fallaba en windows) y la tabla
        self.assertIn("== 2. eliminación de producciones ε ==", salida)
        self.assertIn("Tiempo de conversión a CNF:", salida)
        self.assertIn("Tabla CYK", salida)
        self.assertIn("Resultado: SÍ", salida)
        # el arbol usa auxiliares y se avisa que es el de la cnf
        self.assertIn("T_PAR_IZQ*", salida)
        self.assertIn("el árbol es de la gramática CNF", salida)

    def test_desde_otra_carpeta(self):
        # la gramatica por defecto se encuentra aunque se ejecute desde otro lado
        with tempfile.TemporaryDirectory() as carpeta:
            codigo, salida = ejecutar("--frase", "he cooks", carpeta=carpeta)
        self.assertEqual(codigo, 0)
        self.assertIn("Resultado: SÍ", salida)

    def test_gramatica_inexistente(self):
        codigo, salida = ejecutar("--gramatica", "no_existe.txt", "--frase", "id")
        self.assertEqual(codigo, 2)
        self.assertIn("Error al leer la gramática", salida)

    def test_sin_entrada(self):
        # stdin cerrado sin nada: no hay frase
        codigo, salida = ejecutar(entrada="")
        self.assertEqual(codigo, 1)
        self.assertIn("No se recibió ninguna frase", salida)


if __name__ == "__main__":
    unittest.main()
