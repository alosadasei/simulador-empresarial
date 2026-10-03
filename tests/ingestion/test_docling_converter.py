import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from src.ingestion.docling_converter import convertir_carpeta, convertir_pdf_a_markdown

class TestDoclingConverter(unittest.TestCase):
    """Pruebas de DoclingConverter."""

    def test_pdf_no_existe(self):
        """Comprueba: pdf no existe."""
        with self.assertRaises(FileNotFoundError):
            convertir_pdf_a_markdown("no_existe.pdf")
            
    def test_ruta_no_es_archivo(self):
        """Comprueba: ruta no es archivo."""
        with tempfile.TemporaryDirectory() as temp:
            carpeta = Path(temp)

            with self.assertRaises(ValueError):
                convertir_pdf_a_markdown(carpeta)
                
    def test_extension_no_pdf(self):
        """Comprueba: extension no pdf."""
        with tempfile.TemporaryDirectory() as temp:
            archivo = Path(temp) / "texto.txt"
            archivo.write_text("hola")

            with self.assertRaises(ValueError):
                convertir_pdf_a_markdown(archivo)

    @patch("src.ingestion.docling_converter.converter")
    def test_conversion_correcta(self, mock_converter):
        """Comprueba: conversion correcta."""
        with tempfile.TemporaryDirectory() as temp:

            pdf = (
                Path(temp)
                / "lean_startup"
                / "manual.pdf"
            )

            pdf.parent.mkdir()
            pdf.touch()

            resultado = Mock()
            resultado.document.export_to_markdown.return_value = "# Hola"

            mock_converter.convert.return_value = resultado

            ruta_md = convertir_pdf_a_markdown(pdf)

            self.assertTrue(ruta_md.exists())
            self.assertEqual(
                ruta_md.read_text(encoding="utf-8"),
                "# Hola",
            )
            
    @patch("src.ingestion.docling_converter.converter")
    def test_error_conversion(self, mock_converter):
        """Comprueba: error conversion."""

        with tempfile.TemporaryDirectory() as temp:

            pdf = (
                Path(temp)
                / "lean_startup"
                / "manual.pdf"
            )

            pdf.parent.mkdir()
            pdf.touch()

            mock_converter.convert.side_effect = Exception("boom")

            with self.assertRaises(RuntimeError):
                convertir_pdf_a_markdown(pdf)
                
    def test_carpeta_no_existe(self):
        """Comprueba: carpeta no existe."""
        with self.assertRaises(FileNotFoundError):
            convertir_carpeta("no_existe")
            
    def test_no_es_carpeta(self):
        """Comprueba: no es carpeta."""
        with tempfile.TemporaryDirectory() as temp:

            archivo = Path(temp) / "archivo.pdf"
            archivo.touch()

            with self.assertRaises(ValueError):
                convertir_carpeta(archivo)
                
    @patch(
    "src.ingestion.docling_converter.convertir_pdf_a_markdown"
    )
    def test_convertir_todos(self, mock_convertir):
        """Comprueba: convertir todos."""

        with tempfile.TemporaryDirectory() as temp:

            carpeta = Path(temp)

            (carpeta / "uno.pdf").touch()
            (carpeta / "dos.pdf").touch()

            mock_convertir.side_effect = [
                Path("uno.md"),
                Path("dos.md"),
            ]

            resultado = convertir_carpeta(carpeta)

            self.assertEqual(len(resultado), 2)
            self.assertEqual(mock_convertir.call_count, 2)


if __name__ == "__main__":
    unittest.main()
