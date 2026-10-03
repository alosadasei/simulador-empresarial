import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.ingestion.docling_converter import convertir_pdf_a_markdown
from src.ingestion.text_cleaner import limpiar_archivo_markdown
from src.rag import embeddings
from src.ingestion.indexador import _obtener_markdowns_limpios, indexar_documentos
from src.core.config import CARPETA_MARKDOWN_CLEAN, CARPETA_MARKDOWN_RAW

class TestIndexador(unittest.TestCase):
    """Pruebas de la indexación de documentos."""

    @patch("src.ingestion.indexador.VectorStore")
    @patch("src.ingestion.indexador.crear_embeddings_chunks")
    @patch("src.ingestion.indexador.crear_chunks_documentos")
    @patch("src.ingestion.indexador.cargar_documentos")
    @patch("src.ingestion.indexador._obtener_markdowns_limpios")
    def test_indexacion_correcta(
        self,
        mock_markdowns,
        mock_documentos,
        mock_chunks,
        mock_embeddings,
        mock_vector_store,
    ):
        """Comprueba que el pipeline se ejecuta correctamente."""

        # Datos simulados
        markdowns = [Path("manual.md")]
        documentos = [Mock()]
        chunks = [Mock()]
        embeddings = [Mock()]

        # Configurar los mocks para devolver los datos simulados
        mock_markdowns.return_value = markdowns
        mock_documentos.return_value = documentos
        mock_chunks.return_value = chunks
        mock_embeddings.return_value = embeddings

        # Ejecutar la función a probar
        indexar_documentos()

        # Verificar que cada función fue llamada con los argumentos correctos
        mock_markdowns.assert_called_once()

        mock_documentos.assert_called_once_with(markdowns)

        mock_chunks.assert_called_once_with(documentos)

        mock_embeddings.assert_called_once_with(chunks)

        mock_vector_store.return_value.indexar_chunks.assert_called_once_with(
            chunks,
            embeddings,
        )

    @patch("src.ingestion.indexador.cargar_documentos")
    @patch("src.ingestion.indexador._obtener_markdowns_limpios")
    def test_no_hay_markdowns(self, mock_markdowns, mock_cargar):
        """Comprueba que se maneja correctamente el caso en que no hay markdowns."""

        mock_markdowns.return_value = []

        indexar_documentos()

        mock_cargar.assert_not_called()

    @patch("src.ingestion.indexador.cargar_documentos")
    @patch("src.ingestion.indexador._obtener_markdowns_limpios")
    def test_error_indexacion(self, mock_markdowns, mock_documentos):
        """Comprueba que se propagan los errores del pipeline."""

        mock_markdowns.return_value = [Path("manual.md")]
        mock_documentos.side_effect = RuntimeError("Error de prueba")
        with self.assertRaises(RuntimeError):
            indexar_documentos()


    @patch("src.ingestion.indexador.CARPETA_DOCUMENTOS")
    def test_no_hay_pdfs(
        self,
        mock_carpeta,
    ):
        """Comprueba que falla si no existen PDFs."""

        mock_carpeta.rglob.return_value = []

        with self.assertRaises(FileNotFoundError):
            _obtener_markdowns_limpios()


if __name__ == "__main__":
    unittest.main()
