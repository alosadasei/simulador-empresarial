"""
Módulo encargado de generar embeddings para preguntas y chunks.

Los embeddings representan el contenido semántico de un texto
mediante vectores numéricos que posteriormente pueden compararse
para recuperar los chunks más relevantes para una pregunta.
"""

import logging
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.models import Chunk
from src.core.config import MODELO_EMBEDDINGS

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def cargar_modelo() -> SentenceTransformer:
    """
    Carga el modelo de embeddings configurado.

    El decorador lru_cache evita cargar el modelo varias veces
    durante una misma ejecución del programa.
    """

    logger.info(
        "Cargando modelo de embeddings:\n%s",
        MODELO_EMBEDDINGS
    )

    modelo = SentenceTransformer(
        MODELO_EMBEDDINGS
    )

    modelo.max_seq_length = 1536

    logger.info(
        "Modelo cargado correctamente. " "Longitud máxima de secuencia: %s\n",
        modelo.max_seq_length,
    )

    return modelo


def crear_embedding_texto(
    texto: str,
) -> np.ndarray:
    """
    Convierte un texto en un vector NumPy normalizado.

    Se utiliza principalmente para generar el embedding de una
    pregunta que posteriormente será comparada con los embeddings
    almacenados en el vector store.
    """

    if not texto or not texto.strip():
        raise ValueError(
            "No se puede crear un embedding "
            "de un texto vacío."
        )

    modelo = cargar_modelo()

    embedding = modelo.encode(
        texto.strip().lower(),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return embedding.astype(
        np.float32
    )


def crear_embeddings_textos(
    textos: list[str],
    tamanio_lote: int = 8,
) -> np.ndarray:
    """
    Convierte una lista de textos en una matriz de embeddings
    normalizados.

    Cada fila de la matriz corresponde al embedding de un texto.
    Los textos se procesan por lotes para controlar el consumo
    de memoria durante la generación de embeddings.

    La dimensión de los vectores depende del modelo configurado.
    """

    if not textos:
        return np.empty(
            shape=(0, 0),
            dtype=np.float32,
        )

    textos_limpios: list[str] = []

    for texto in textos:

        if not texto or not texto.strip():
            raise ValueError(
                "La lista contiene un texto vacío."
            )

        textos_limpios.append(
            texto.strip().lower()
        )

    if tamanio_lote <= 0:
        raise ValueError(
            "El tamaño del lote debe ser "
            "mayor que cero."
        )

    modelo = cargar_modelo()

    embeddings = modelo.encode(
        textos_limpios,
        batch_size=tamanio_lote,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return embeddings.astype(
        np.float32
    )


def crear_embeddings_chunks(
    chunks: list[Chunk],
    tamanio_lote: int = 8,
) -> np.ndarray:
    """ "
    Convierte una lista de objetos Chunk en una matriz de embeddings
    normalizados.

    El orden de los vectores será el mismo que el orden de los chunks.

    Cada Chunk proporciona su representación mediante
    texto_embedding(), que incorpora el contexto jerárquico necesario
    para mejorar su representación semántica.
    """

    textos = [chunk.texto_embedding() for chunk in chunks]

    return crear_embeddings_textos(
        textos=textos,
        tamanio_lote=tamanio_lote,
    )


if __name__ == "__main__":

    logger.info("Este módulo proporciona funciones para generar embeddings.")
