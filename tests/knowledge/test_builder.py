import unittest
from uuid import UUID

from src.core.models import Metodologia
from src.ingestion.markdown_parser import MarkdownNode
from src.knowledge.builder import crear_arbol

class TestBuilder(unittest.TestCase):
    """Pruebas de Builder."""

    def test_crear_arbol(self):
        """Comprueba que se crea un árbol con la raíz y metodología esperadas."""

        raiz = MarkdownNode(
            titulo="Tema 1",
            nivel=1,
        )

        arbol = crear_arbol(raiz, "MetodologiaTest")

        self.assertEqual(arbol.raiz.titulo, "Tema 1")
        self.assertEqual(arbol.raiz.nivel, 1)
        self.assertEqual(arbol.metodologia, "MetodologiaTest")


    def test_crear_arbol_convierte_hijos_recursivamente(self):
        """Comprueba que los hijos del nodo se convierten de forma recursiva."""
        nieto = MarkdownNode(
            titulo="Apartado",
            nivel=3,
        )

        hijo = MarkdownNode(
            titulo="Sección",
            nivel=2,
        )

        hijo.hijos.append(nieto)

        raiz = MarkdownNode(
            titulo="Tema",
            nivel=1,
        )

        raiz.hijos.append(hijo)

        arbol = crear_arbol(raiz, "MetodologiaTest")

        self.assertEqual(len(arbol.raiz.hijos), 1)
        self.assertEqual(arbol.raiz.hijos[0].titulo, "Sección")
        self.assertEqual(
            arbol.raiz.hijos[0].hijos[0].titulo,
            "Apartado",
        )


    def test_crear_arbol_genera_ids_validos(self):
        """Comprueba que los nodos del árbol reciben identificadores válidos."""
        raiz = MarkdownNode(
            titulo="Tema",
            nivel=1,
        )

        arbol = crear_arbol(raiz, "MetodologiaTest")

        UUID(arbol.raiz.id)


    def test_crear_arbol_nodo_sin_hijos(self):
        """Comprueba que un nodo sin hijos queda con una lista vacía."""
        raiz = MarkdownNode(
            titulo="Tema",
            nivel=1,
        )

        arbol = crear_arbol(raiz, "MetodologiaTest")

        self.assertEqual(arbol.raiz.hijos, [])


if __name__ == "__main__":
    unittest.main()
