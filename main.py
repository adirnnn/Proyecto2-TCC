"""
programa principal: pide una frase y dice si pertenece al lenguaje (SÍ / NO),
cuanto tardo cyk en validarla y, si se acepta, muestra su arbol de analisis.

uso normal (solo pide la frase):
    python main.py

opciones:
    --frase "..."       pasa la frase directo, sin preguntar
    --gramatica RUTA    usa otra gramatica (por defecto gramaticas/ingles.txt)
    --etapas            muestra como queda la gramatica en cada paso de la cnf
    --tabla             muestra la tabla de cyk (que variables hay en cada celda)
"""

import argparse
import os
import sys
import time

from parser_cyk.cnf import convertir_a_cnf, formatear_etapas
from parser_cyk.cyk import cyk, dibujar_arbol, formatear_tabla, normalizar
from parser_cyk.gramatica import ErrorGramatica, leer_gramatica

# carpeta donde esta este archivo, para encontrar la gramatica por defecto
# aunque el programa se ejecute desde otra carpeta
CARPETA = os.path.dirname(os.path.abspath(__file__))
GRAMATICA_POR_DEFECTO = os.path.join(CARPETA, "gramaticas", "ingles.txt")


def configurar_utf8():
    # en windows, cuando la salida se redirige (pipe o archivo) python usa
    # cp1252 y truena al imprimir 'ε'; forzamos utf-8 en la salida
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    # en la entrada usamos utf-8-sig: powershell al hacer "texto" | python
    # manda una marca invisible (bom) al inicio que se pegaba a la primera
    # palabra y la volvia desconocida; utf-8-sig la quita
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8-sig", errors="replace")


def leer_argumentos(argv):
    # definimos las opciones de la linea de comandos
    parser = argparse.ArgumentParser(
        description="Valida frases con el algoritmo CYK sobre una gramática convertida a CNF."
    )
    parser.add_argument("--frase", help="frase a validar (si no se da, se pide por teclado)")
    parser.add_argument("--gramatica", default=GRAMATICA_POR_DEFECTO,
                        help="archivo de gramática (por defecto gramaticas/ingles.txt)")
    parser.add_argument("--etapas", action="store_true",
                        help="muestra la gramática después de cada paso de la conversión a CNF")
    parser.add_argument("--tabla", action="store_true",
                        help="muestra las celdas de la tabla de CYK")
    return parser.parse_args(argv)


def formatear_tiempo(nanosegundos):
    # mostramos milisegundos con decimales y tambien los nanosegundos exactos
    return f"{nanosegundos / 1_000_000:.4f} ms ({nanosegundos} ns)"


def main(argv=None):
    configurar_utf8()
    args = leer_argumentos(argv)

    # 1) leer la gramatica del archivo
    try:
        original = leer_gramatica(args.gramatica)
    except (OSError, ErrorGramatica) as error:
        print(f"Error al leer la gramática: {error}", file=sys.stderr)
        return 2

    # 2) convertir a cnf (se mide aparte, no cuenta en el tiempo de cyk)
    inicio_conversion = time.perf_counter_ns()
    gramatica, etapas = convertir_a_cnf(original)
    tiempo_conversion = time.perf_counter_ns() - inicio_conversion

    if args.etapas:
        # modo diagnostico: todas las etapas de la conversion
        print(formatear_etapas(etapas))
        print(f"\nTiempo de conversión a CNF: {formatear_tiempo(tiempo_conversion)}\n")

    # 3) obtener la frase (por opcion o preguntando)
    if args.frase is not None:
        frase = args.frase
    else:
        try:
            frase = input("Ingrese la frase: ")
        except EOFError:
            # se cerro la entrada sin escribir nada (ej: ctrl+z / ctrl+d)
            print("\nNo se recibió ninguna frase.", file=sys.stderr)
            return 1

    # 4) normalizar: minusculas y separar por espacios
    tokens = normalizar(frase)

    # 5) correr cyk midiendo SOLO el algoritmo (incluye guardar los punteros
    # del arbol, pero no la espera del teclado, ni imprimir, ni la conversion)
    inicio = time.perf_counter_ns()
    resultado = cyk(gramatica, tokens)
    tiempo_cyk = time.perf_counter_ns() - inicio

    # 6) mostrar resultados
    print(f"Frase normalizada: {' '.join(tokens) if tokens else '(vacía)'}")
    print(f"Tokens ({len(tokens)}): {' | '.join(tokens) if tokens else '-'}")
    print(f"Resultado: {'SÍ' if resultado.aceptada else 'NO'}")
    print(f"Tiempo de validación CYK: {formatear_tiempo(tiempo_cyk)}")

    if resultado.desconocidos:
        # avisamos que palabras no conoce la gramatica (puntuacion incluida)
        print("Tokens desconocidos (no son terminales de la gramática): "
              + ", ".join(resultado.desconocidos))

    if args.tabla and tokens:
        print("\nTabla CYK [inicio,largo] 'pedazo': {variables}")
        print(formatear_tabla(resultado))

    if resultado.aceptada:
        print("\nÁrbol de análisis (gramática en CNF):")
        print(dibujar_arbol(resultado.arbol, gramatica))
        print(f"\nNotación parentizada: {resultado.arbol.parentizado()}")
        # si la cnf es igual a la original, el arbol tambien vale para la original
        if gramatica.inicial == original.inicial and gramatica.producciones == original.producciones:
            print("Nota: la CNF es idéntica a la gramática original, así que este árbol "
                  "también es un árbol de la gramática original.")
        else:
            print("Nota: * marca variables auxiliares creadas por la conversión a CNF; "
                  "el árbol es de la gramática CNF, no de la original.")
    else:
        print("\nNo existe árbol de análisis para esta frase bajo esta gramática.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
