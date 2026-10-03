import unittest
from pathlib import Path


from src.ingestion.chunker import crear_chunks_documento
from src.core.models import Documento, Metodologia


class TestCrearChunksDocumento(unittest.TestCase):


        # POSIBILIDAD DE AÑADIR UN SETUP Y UN TEARDOWN MÁS TARDE COMO MEJORA

    """Pruebas de CrearChunksDocumento."""

    def _crear_documento(self, texto: str) -> Documento:
        """Crea un documento de prueba con el texto indicado."""
        return Documento(
            metodologia=Metodologia(nombre="Test"),
            nombre="documento",
            texto=texto,
            ruta=Path("test.md"),
        )

    def test_documento_vacio(self):
        """Comprueba: documento vacio."""

        documento = self._crear_documento("")

        chunks = crear_chunks_documento(documento)

        self.assertFalse(chunks)

    def test_solo_titulo(self):
        """Comprueba: solo titulo."""

        documento = self._crear_documento("# MÓDULO 1")

        chunks = crear_chunks_documento(documento)

        self.assertFalse(chunks)

    def test_titulo_subtitulo_y_contenido(self):
        """Comprueba: titulo subtitulo y contenido."""

        documento = self._crear_documento(
            "# MÓDULO 1\n\n"
            "## Introducción\n\n"
            "Este es el contenido del subtítulo."
        )

        chunks = crear_chunks_documento(documento)
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]        

        self.assertEqual(chunk.titulo, "MÓDULO 1")
        self.assertEqual(chunk.subtitulo, "Introducción")
        self.assertIsNone(chunk.seccion)
        self.assertIsNone(chunk.subseccion)
        self.assertIsNone(chunk.apartado)
        self.assertEqual(chunk.texto, "Este es el contenido del subtítulo.")

    def test_titulo_subtitulo_seccion_y_contenido(self):
        """Comprueba: titulo subtitulo seccion y contenido."""

        documento = self._crear_documento(
            "# MÓDULO 1\n\n"
            "## Introducción\n\n"
            "### Sección 1\n\n"
            "Este es el contenido de la sección."
        )

        chunks = crear_chunks_documento(documento)
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]        

        self.assertEqual(chunk.titulo, "MÓDULO 1")
        self.assertEqual(chunk.subtitulo, "Introducción")
        self.assertEqual(chunk.seccion, "Sección 1")
        self.assertIsNone(chunk.subseccion)
        self.assertIsNone(chunk.apartado)
        self.assertEqual(chunk.texto, "Este es el contenido de la sección.")

    def test_titulo_subtitulo_seccion_subseccion_y_contenido(self):
        """Comprueba: titulo subtitulo seccion subseccion y contenido."""

        documento = self._crear_documento(
            "# MÓDULO 1\n\n"
            "## Introducción\n\n"
            "### Sección 1\n\n"
            "#### Subsección 1\n\n"
            "Este es el contenido de la subsección."
        )

        chunks = crear_chunks_documento(documento)
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]        

        self.assertEqual(chunk.titulo, "MÓDULO 1")
        self.assertEqual(chunk.subtitulo, "Introducción")
        self.assertEqual(chunk.seccion, "Sección 1")
        self.assertEqual(chunk.subseccion, "Subsección 1")
        self.assertIsNone(chunk.apartado)
        self.assertEqual(chunk.texto, "Este es el contenido de la subsección.")

    def test_jerarquia_entera_y_contenido(self):
        """Comprueba: jerarquia entera y contenido."""
        documento = self._crear_documento(
            "# MÓDULO 1\n\n"
            "## Introducción\n\n"
            "### Sección 1\n\n"
            "#### Subsección 1\n\n"
            "##### Apartado 1\n\n"
            "Este es el contenido de la subsección."
        )

        chunks = crear_chunks_documento(documento)
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]        

        self.assertEqual(chunk.titulo, "MÓDULO 1")
        self.assertEqual(chunk.subtitulo, "Introducción")
        self.assertEqual(chunk.seccion, "Sección 1")
        self.assertEqual(chunk.subseccion, "Subsección 1")
        self.assertEqual(chunk.apartado, "Apartado 1")
        self.assertEqual(chunk.texto, "Este es el contenido de la subsección.")

    def test_titulo_subtitulos_y_contenido(self):
        """Comprueba: titulo subtitulos y contenido."""

        documento = self._crear_documento(
            "# MÓDULO 1\n\n"
            "## Apartado A\n\n"
            "### Sección A1\n\n"
            "Este es el contenido de la Sección A1.\n\n"
            "## Apartado B\n\n"
            "Este es el contenido del Apartado B."
        )

        chunks = crear_chunks_documento(documento)
        self.assertEqual(len(chunks), 2)

        self.assertEqual(chunks[0].indice, 0)
        self.assertEqual(chunks[1].indice, 1)

        self.assertEqual(chunks[0].subtitulo, "Apartado A")
        self.assertEqual(chunks[0].seccion, "Sección A1")
        self.assertEqual(chunks[0].texto, "Este es el contenido de la Sección A1.")
        self.assertEqual(chunks[1].subtitulo, "Apartado B")
        self.assertIsNone(chunks[1].seccion)
        self.assertEqual(chunks[1].texto, "Este es el contenido del Apartado B.")

if __name__ == "__main__":
    unittest.main()
