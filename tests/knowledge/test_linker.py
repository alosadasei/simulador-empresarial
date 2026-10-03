import unittest

from src.knowledge import linker
from src.knowledge.models import KnowledgeNode, KnowledgeTree
from src.core.models import Metodologia, Chunk, Documento

"""Pruebas del módulo linker para verificar la vinculación de chunks
con nodos de un árbol de conocimiento.
"""

class TestLinker(unittest.TestCase):
    """Pruebas de Linker."""

    def setUp(self):
        """
        Inicializa un árbol de conocimiento sencillo con una raíz,
        un título y dos secciones, y define un documento de prueba.
        """
        self.raiz = KnowledgeNode(
            id="0",
            titulo=None,
            nivel=0,
        )

        self.titulo = KnowledgeNode(
            id="1",
            titulo="Título 1",
            nivel=1,
            padre=self.raiz,
        )

        self.seccion1 = KnowledgeNode(
            id="2",
            titulo="Sección 1",
            nivel=2,
            padre=self.titulo,
        )

        self.seccion2 = KnowledgeNode(
            id="3",
            titulo="Sección 2",
            nivel=2,
            padre=self.titulo,
        )

        self.documento = Documento(
            metodologia=Metodologia(nombre="test"),
            nombre="Documento de prueba",
            texto="Texto de prueba",
            ruta="documento.md",
        )

        self.raiz.hijos.append(self.titulo)
        self.titulo.hijos.extend([self.seccion1, self.seccion2])

        self.arbol = KnowledgeTree(
            metodologia=Metodologia(nombre="test"),
            raiz=self.raiz,
        )



    def test_buscar_hijo_existente(self):
        """
        Comprueba que _buscar_hijo devuelve el hijo cuyo título coincide.
        """
        nodo = linker._buscar_hijo(self.raiz, "Título 1")

        self.assertIs(nodo, self.titulo)


    def test_buscar_hijo_inexistente(self):
        """
        Comprueba que _buscar_hijo devuelve None cuando el hijo no existe.
        """
        nodo = linker._buscar_hijo(self.raiz, "Título inexistente")

        self.assertIsNone(nodo)


    def test_buscar_nodo_primer_nivel(self):
        """
        Comprueba que _buscar_nodo localiza un nodo de primer nivel.
        """
        chunk = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto de prueba",
            titulo="Título 1",
        )

        nodo = linker._buscar_nodo(self.arbol, chunk)

        self.assertIs(nodo, self.titulo)


    def test_buscar_nodo_varios_niveles(self):
        """
        Comprueba que _buscar_nodo localiza un nodo siguiendo
        una jerarquía de varios niveles.
        """
        chunk = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto de prueba",
            titulo="Título 1",
            subtitulo="Sección 1",
        )

        nodo = linker._buscar_nodo(self.arbol, chunk)

        self.assertIs(nodo, self.seccion1)


    def test_buscar_nodo_inexistente(self):
        """
        Comprueba que _buscar_nodo lanza ValueError cuando
        no encuentra un nodo en la jerarquía.
        """
        chunk = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto de prueba",
            titulo="Título inexistente",
        )

        with self.assertRaises(ValueError):
            linker._buscar_nodo(self.arbol, chunk)


    def test_enlazar_chunk_nodo(self):
        """
        Comprueba que al enlazar un chunk con un nodo:
        - el chunk recibe el id del nodo.
        - el nodo registra el índice del chunk.
        """
        chunk = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto de prueba",
        )

        linker._enlazar_chunk_nodo(chunk, self.seccion1)

        self.assertEqual(chunk.node_id, self.seccion1.id)
        self.assertIn(chunk.indice, self.seccion1.chunk_ids)


    def test_enlazar_chunk_nodo_no_duplica_indice(self):
        """
        Comprueba que enlazar un chunk ya registrado no duplica
        su índice dentro del nodo.
        """
        chunk = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto de prueba",
        )

        self.seccion1.chunk_ids.append(chunk.indice)

        linker._enlazar_chunk_nodo(chunk, self.seccion1)

        self.assertEqual(self.seccion1.chunk_ids, [0])


    def test_enlazar(self):
        """
        Comprueba que enlazar relaciona correctamente un chunk
        con el nodo correspondiente del árbol.
        """
        chunk = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto de prueba",
            titulo="Título 1",
            subtitulo="Sección 1",
        )

        linker.enlazar(self.arbol, [chunk])

        self.assertEqual(chunk.node_id, self.seccion1.id)
        self.assertIn(chunk.indice, self.seccion1.chunk_ids)


    def test_enlazar_varios_chunks(self):
        """
        Comprueba que enlazar procesa correctamente varios chunks
        y los asigna a sus nodos correspondientes.
        """
        chunk1 = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto sección 1",
            titulo="Título 1",
            subtitulo="Sección 1",
        )

        chunk2 = Chunk(
            documento=self.documento,
            indice=1,
            texto="Texto sección 2",
            titulo="Título 1",
            subtitulo="Sección 2",
        )

        linker.enlazar(self.arbol, [chunk1, chunk2])

        self.assertEqual(chunk1.node_id, self.seccion1.id)
        self.assertEqual(chunk2.node_id, self.seccion2.id)

        self.assertIn(chunk1.indice, self.seccion1.chunk_ids)
        self.assertIn(chunk2.indice, self.seccion2.chunk_ids)


    def test_enlazar_chunk_inexistente(self):
        """
        Comprueba que enlazar lanza ValueError cuando un chunk
        no tiene un nodo correspondiente en el árbol.
        """
        chunk = Chunk(
            documento=self.documento,
            indice=0,
            texto="Texto de prueba",
            titulo="Título inexistente",
        )

        with self.assertRaisesRegex(ValueError, "Título inexistente"):
            linker.enlazar(self.arbol, [chunk])


if __name__ == "__main__":
    unittest.main()
