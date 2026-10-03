from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.core.config import CARPETA_MARKDOWN_CLEAN, CARPETA_MARKDOWN_RAW
from src.ingestion.text_cleaner import eliminar_lineas_vacias, eliminar_marcadores_imagen, eliminar_cabeceras_y_pies, eliminar_numeros_pagina, eliminar_simbolos_ocr, eliminar_isbn, es_elemento_markdown, limpiar_archivo_markdown, limpiar_markdowns, limpiar_texto, normalizar_formato, unir_palabras_partidas, unir_parrafos_partidos

class TestTextCleaner(unittest.TestCase):
    """Pruebas de TextCleaner."""

    def test_limpiar_texto(self):        
        """Comprueba que el texto se limpia correctamente."""

        texto = """
        <!-- image -->
        Lean Startup en Educación
        ISBN: 978-84-123456-78-9

        genera-
        ción

        Este es un   párrafo.
        """

        esperado = (
            "generación\n\n"
            "Este es un párrafo."
        )

        resultado = limpiar_texto(texto)

        self.assertEqual(resultado, esperado)
        

    def test_eliminar_marcadores_img(self):
        """Comprueba que elimina los marcadores de imagen."""
        
        texto = "Hola\n<!-- image -->\nMundo"
        esperado = "Hola\n\nMundo"
        
        resultado = eliminar_marcadores_imagen(texto)        
        self.assertEqual(resultado, esperado)
        

    def test_eliminar_cabeceras_y_pies(self):
        """Comprueba que elimina las cabeceras y pies de página repetidos."""
        
        texto = (
        "Lean Startup en Educación\n"
        "Contenido útil"
        )
        
        esperado = "Contenido útil"

        resultado = eliminar_cabeceras_y_pies(texto)
        self.assertEqual(resultado, esperado)
        

    def test_eliminar_numeros_paginas(self):
        """Comprueba que elimina números de página."""
        
        texto = (
        "5\n"
        "Contenido\n"
        "10"
        )
        
        esperado = "Contenido"
        
        resultado = eliminar_numeros_pagina(texto)
        self.assertEqual(resultado, esperado)
        

    def test_eliminar_simbolos_ocr(self):
        """Comprueba que elimina símbolos de OCR."""
        
        texto = "Hola  mundo ！口"

        esperado = "Hola  mundo "
        
        resultado = eliminar_simbolos_ocr(texto)
        self.assertEqual(resultado, esperado)
        
    
    def test_eliminar_isbn(self):
        """Comprueba que elimina líneas ISBN."""

        texto = (
            "ISBN: 978-84-123456-78-9\n"
            "Contenido"
        )

        esperado = "Contenido"
        
        resultado = eliminar_isbn(texto)
        self.assertEqual(resultado, esperado)
        
        
    def test_unir_palabras_partidas(self):
        """Comprueba que une palabras partidas."""

        texto = "genera-\nción"

        esperado = "generación"

        resultado = unir_palabras_partidas(texto)
        self.assertEqual(resultado, esperado)
        
    
    def test_unir_parrafos_partidos(self):
        """Comprueba que une líneas del mismo párrafo."""

        texto = (
            "Esto es\n"
            "un párrafo."
        )

        esperado = "Esto es un párrafo."
        
        resultado = unir_parrafos_partidos(texto)
        self.assertEqual(resultado, esperado)
        
        
    def test_conserva_titulo_markdown(self):
        """Comprueba que no une títulos Markdown."""

        texto = (
            "# Título\n"
            "Contenido"
        )

        esperado = (
            "# Título\n"
            "Contenido"
        )

        resultado = unir_parrafos_partidos(texto)
        self.assertEqual(resultado, esperado)
        
        
    def test_es_elemento_markdown(self):
        """Comprueba que detecta elementos Markdown."""

        self.assertTrue(es_elemento_markdown("# Título"))
        self.assertTrue(es_elemento_markdown("- Lista"))
        self.assertTrue(es_elemento_markdown("| tabla |"))
        self.assertTrue(es_elemento_markdown("1. Lista"))
        self.assertFalse(es_elemento_markdown("Texto normal"))
        
        
    def test_normalizar_formato(self):
        """Comprueba que normaliza espacios."""

        texto = "Hola    mundo\t!"

        esperado = "Hola mundo !"

        resultado = normalizar_formato(texto)
        self.assertEqual(resultado, esperado)
        
        
    def test_eliminar_lineas_vacias(self):
        """Comprueba que conserva como máximo una línea vacía."""

        texto = "Hola\n\n\n\nMundo"

        esperado = "Hola\n\nMundo"

        resultado = eliminar_lineas_vacias(texto)
        self.assertEqual(resultado, esperado)
    
    
    def test_archivo_no_existe(self):
        """Comprueba que falla si el archivo no existe."""

        with self.assertRaises(FileNotFoundError):
            limpiar_archivo_markdown(
                Path("no_existe.md"),
                Path("salida.md"),
            )
    
    def test_extension_incorrecta(self):
        """Comprueba que falla si el archivo no es Markdown."""

        with tempfile.TemporaryDirectory() as temp:

            archivo = Path(temp) / "texto.txt"

            archivo.write_text(
                "Contenido",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                limpiar_archivo_markdown(
                    archivo,
                    Path(temp) / "salida.md",
                )
    
    def test_limpiar_archivo_correctamente(self):
        """Comprueba que limpia correctamente un archivo Markdown."""

        with tempfile.TemporaryDirectory() as temp:

            entrada = Path(temp) / "entrada.md"
            salida = Path(temp) / "salida.md"

            entrada.write_text(
                "<!-- image -->\nHola",
                encoding="utf-8",
            )

            resultado = limpiar_archivo_markdown(
                entrada,
                salida,
            )

            self.assertEqual(
                resultado,
                salida,
            )

            self.assertTrue(
                salida.exists(),
            )

            self.assertEqual(
                salida.read_text(encoding="utf-8"),
                "Hola",
            )
    
    def test_lista_vacia(self):
        """Comprueba que devuelve una lista vacía."""

        resultado = limpiar_markdowns([])

        self.assertEqual(
            resultado,
            [],
        )
        
    @patch("src.ingestion.text_cleaner.limpiar_archivo_markdown")
    def test_limpiar_varios_archivos(
        self,
        mock_limpiar,
    ):
        """Comprueba que limpia todos los archivos Markdown."""

        ruta1 = (
            CARPETA_MARKDOWN_RAW
            / "lean_startup"
            / "manual1.md"
        )

        ruta2 = (
            CARPETA_MARKDOWN_RAW
            / "simulacion_empresarial"
            / "manual2.md"
        )

        salida1 = (
            CARPETA_MARKDOWN_CLEAN
            / "lean_startup"
            / "manual1.md"
        )

        salida2 = (
            CARPETA_MARKDOWN_CLEAN
            / "simulacion_empresarial"
            / "manual2.md"
        )

        mock_limpiar.side_effect = [
            salida1,
            salida2,
        ]        
        
        resultado = limpiar_markdowns([
            ruta1,
            ruta2,
        ])

        self.assertEqual(
            resultado,
            [
                salida1,
                salida2,
            ],
        )

        self.assertEqual(
            mock_limpiar.call_count,
            2,
        )
        
        mock_limpiar.assert_any_call(
                    ruta1,
                    salida1,
                )
        
        mock_limpiar.assert_any_call(
            ruta2,
            salida2,
        )
    
if __name__ == "__main__":
    unittest.main()