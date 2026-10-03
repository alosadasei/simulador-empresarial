import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from src.core.models import Metodologia
from src.ingestion.document_loader import cargar_documento, cargar_documentos

class TestDocumentLoader(unittest.TestCase):
    """Pruebas de DocumentLoader."""

    def test_archivo_no_existe(self):
        """Comprueba: archivo no existe."""
        with self.assertRaises(FileNotFoundError):
            cargar_documento(
                Path("no_existe.md"),
                Metodologia("lean_startup"),
            )

    def test_ruta_no_es_archivo(self):
        """Comprueba: ruta no es archivo."""
        with tempfile.TemporaryDirectory() as temp:
            carpeta = Path(temp)

            with self.assertRaises(ValueError):
                cargar_documento(
                    carpeta,
                    Metodologia("lean_startup"),
                )

    def test_extension_incorrecta(self):
        """Comprueba: extension incorrecta."""
        with tempfile.TemporaryDirectory() as temp:
            archivo = Path(temp) / "texto.txt"
            archivo.write_text("hola")

            with self.assertRaises(ValueError):
                cargar_documento(
                    archivo,
                    Metodologia("lean_startup"),
                )

    def test_carga_documento_correctamente(self):
        """Comprueba: carga documento correctamente."""
        with tempfile.TemporaryDirectory() as temp:

            archivo = Path(temp) / "manual.md"
            archivo.write_text(
                "# Hola",
                encoding="utf-8",
            )

            metodologia = Metodologia("lean_startup")

            documento = cargar_documento(
                archivo,
                metodologia,
            )

            self.assertEqual(documento.metodologia, metodologia)
            self.assertEqual(documento.nombre, "manual")
            self.assertEqual(documento.texto, "# Hola")
            self.assertEqual(documento.ruta, str(archivo))

    def test_lista_vacia(self):
        """Comprueba: lista vacia."""
        self.assertEqual(
            cargar_documentos([]),
            [],
        )

    @patch("src.ingestion.document_loader.cargar_documento")
    def test_cargar_varios_documentos(
        self,
        mock_cargar,
    ):
        """Comprueba: cargar varios documentos."""

        ruta1 = Path("lean_startup/manual1.md")
        ruta2 = Path("design_thinking/manual2.md")

        doc1 = Mock()
        doc2 = Mock()

        mock_cargar.side_effect = [
            doc1,
            doc2,
        ]

        resultado = cargar_documentos([
            ruta1,
            ruta2,
        ])

        self.assertEqual(resultado, [doc1, doc2])
        self.assertEqual(mock_cargar.call_count, 2)

    @patch("src.ingestion.document_loader.cargar_documento")
    def test_detecta_metodologia(
        self,
        mock_cargar,
    ):
        """Comprueba: detecta metodologia."""

        ruta = Path("lean_startup/manual.md")

        mock_cargar.return_value = Mock()

        cargar_documentos([ruta])

        _, kwargs = mock_cargar.call_args

        self.assertEqual(
            kwargs["metodologia"].nombre,
            "lean_startup",
        )

if __name__ == "__main__":
    unittest.main()
