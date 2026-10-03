"""
Analiza el tamaño real de los chunks generados por el sistema.

Utiliza el mismo Chunker y la misma representación
texto_embedding() que se utilizan durante la indexación.

No modifica documentos, chunks ni la base vectorial.
"""

from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

from src.core.config import MODELO_EMBEDDINGS
from src.ingestion.document_loader import cargar_documentos
from src.ingestion.markdown_parser import parsear_markdown
from src.ingestion.chunker import crear_chunks_documentos

# ---------------------------------------------------------
# Configuración
# ---------------------------------------------------------

CARPETA_MARKDOWN = Path("data/markdown_clean")


# ---------------------------------------------------------
# Cargar tokenizer
# ---------------------------------------------------------

print("\nCargando tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(MODELO_EMBEDDINGS)

print(f"Modelo: {MODELO_EMBEDDINGS}")


# ---------------------------------------------------------
# Obtener archivos Markdown
# ---------------------------------------------------------

rutas_markdown = sorted(CARPETA_MARKDOWN.rglob("*.md"))

print(f"Archivos Markdown encontrados: " f"{len(rutas_markdown)}")


# ---------------------------------------------------------
# Cargar documentos
# ---------------------------------------------------------

documentos = cargar_documentos(rutas_markdown)

print(f"Documentos cargados: " f"{len(documentos)}")


# ---------------------------------------------------------
# Crear árboles Markdown
# ---------------------------------------------------------

arboles = []

for documento in documentos:

    arbol = parsear_markdown(documento.texto)

    arboles.append(arbol)


# ---------------------------------------------------------
# Crear chunks EXACTAMENTE como en el pipeline
# ---------------------------------------------------------

chunks = crear_chunks_documentos(
    documentos,
    arboles,
)

print(f"Chunks generados: " f"{len(chunks)}")


# ---------------------------------------------------------
# Medir tokens
# ---------------------------------------------------------

num_tokens = []

for chunk in chunks:

    texto = chunk.texto_embedding()

    tokens = tokenizer(
        texto,
        add_special_tokens=True,
        truncation=False,
    )["input_ids"]

    num_tokens.append(len(tokens))


# ---------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------

tokens = np.array(
    num_tokens,
    dtype=np.int32,
)

print("\n")
print("=" * 50)
print("ESTADÍSTICAS DE CHUNKS")
print("=" * 50)

print(f"Chunks totales: " f"{len(tokens)}")

print(f"Tokens mínimos: " f"{tokens.min()}")

print(f"Tokens máximos: " f"{tokens.max()}")

print(f"Tokens media: " f"{tokens.mean():.1f}")

print(f"Tokens mediana: " f"{np.median(tokens):.1f}")

print(f"P90: " f"{np.percentile(tokens, 90):.1f}")

print(f"P95: " f"{np.percentile(tokens, 95):.1f}")

print(f"P99: " f"{np.percentile(tokens, 99):.1f}")


# ---------------------------------------------------------
# Cobertura por límite
# ---------------------------------------------------------

print("\n")
print("=" * 50)
print("COBERTURA POR LÍMITE DE TOKENS")
print("=" * 50)

limites = [
    128,
    256,
    384,
    512,
    768,
    1024,
    1536,
    2048,
    4096,
    8192,
]

for limite in limites:

    cantidad = np.sum(tokens <= limite)

    porcentaje = (cantidad / len(tokens)) * 100

    print(
        f"{limite:>5} tokens: "
        f"{cantidad:>4}/{len(tokens)} "
        f"({porcentaje:>5.1f} %)"
    )


# ---------------------------------------------------------
# 20 chunks más grandes
# ---------------------------------------------------------

print("\n")
print("=" * 70)
print("20 CHUNKS MÁS GRANDES")
print("=" * 70)

indices = np.argsort(tokens)[::-1][:20]

for posicion, indice in enumerate(indices, start=1):

    chunk = chunks[indice]

    print(
        f"{posicion:>2}. "
        f"{tokens[indice]:>5} tokens | "
        f"{chunk.documento.nombre} | "
        f"{chunk.titulo or ''} > "
        f"{chunk.subtitulo or ''} > "
        f"{chunk.seccion or ''} > "
        f"{chunk.subseccion or ''} > "
        f"{chunk.apartado or ''}"
    )

print("\nAnálisis terminado.")
