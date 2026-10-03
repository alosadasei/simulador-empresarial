"""
    Modulo (de prueba) para la función de indexación de documentos.
    
    Para cuando se tenga q volver a indexar la base de datos NO desde el boton del chatbot
    Terminal: python -m pruebas_codigo.prueba_indexador    
"""
import logging
from src.ingestion.indexador import indexar_documentos


def boton_actualizar_base_datos():
    """Simula el botón del panel de administración que reindexa los documentos."""
    indexar_documentos()


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
    )

    # Simulación de pulsar botón
    boton_actualizar_base_datos()
