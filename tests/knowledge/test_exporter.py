
import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from src.knowledge.models import KnowledgeNode, KnowledgeTree
from src.knowledge import exporter
from src.core.models import Metodologia


class TestExporter(unittest.TestCase):
    """Pruebas de Exporter."""

    def setUp(self):
        """Prepara un árbol de ejemplo con un nodo raíz y un hijo para las pruebas."""

        self.metodologia = Metodologia(
            nombre="MetodologiaTest"
        )
        
        self.hijo = KnowledgeNode(
            id="id_hijo",
            titulo="Hijo",
            nivel=2,
            chunk_ids=[3],
        )

        self.raiz = KnowledgeNode(
            id="id_raiz",
            titulo="Raíz",
            nivel=1,
            chunk_ids=[1, 2],
            hijos=[self.hijo],
        )

        self.arbol = KnowledgeTree(
            metodologia=self.metodologia,
            raiz=self.raiz,
        )

        

    def test_arbol_a_dict(self):
        """Comprueba que el árbol se convierte a un diccionario con la estructura esperada."""

        resultado = exporter.arbol_a_dict(self.arbol)

        esperado = {
            "metodologia": self.metodologia.nombre,
            "raiz": {
                "id": "id_raiz",
                "titulo": "Raíz",
                "nivel": 1,
                "chunk_ids": [1, 2],
                "hijos": [
                    {
                        "id": "id_hijo",
                        "titulo": "Hijo",
                        "nivel": 2,
                        "chunk_ids": [3],
                        "hijos": [],
                    }
                ],
            },
        }


        self.assertEqual(resultado, esperado)



    def test_arbol_a_dict_arbol_sin_hijos(self):
        """Comprueba: arbol a dict arbol sin hijos."""

        self.raiz.hijos = []

        resultado = exporter.arbol_a_dict(self.arbol)

        self.assertEqual(resultado["raiz"]["hijos"], [])



    def test_arbol_a_dict_arbol_sin_hijos(self):
        """Comprueba que un árbol sin hijos se exporta con el formato esperado."""

        self.raiz.hijos = []

        resultado = exporter.arbol_a_dict(self.arbol)

        esperado = {
            "metodologia": self.metodologia.nombre,
            "raiz": {
                "id": "id_raiz",
                "titulo": "Raíz",
                "nivel": 1,
                "chunk_ids": [1, 2],
                "hijos": [],
            },
        }

        self.assertEqual(resultado, esperado)



    def test_guardar_json_crea_fichero(self):
        """Comprueba que guardar_json crea el fichero JSON en la ruta indicada."""

        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "arbol.json"

            exporter.guardar_json(self.arbol, ruta)

            self.assertTrue(ruta.exists())


    def test_guardar_json_contenido_correcto(self):
        """Comprueba que el contenido guardado en el JSON coincide con el árbol exportado."""

        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "arbol.json"

            exporter.guardar_json(self.arbol, ruta)

            with ruta.open("r", encoding="utf-8") as fichero:
                contenido = json.load(fichero)

            self.assertEqual(contenido, exporter.arbol_a_dict(self.arbol))


    def test_guardar_json_crea_directorios(self):
        """Comprueba que guardar_json crea también los directorios intermedios si hacen falta."""

        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "carpeta1" / "carpeta2" / "arbol.json"

            exporter.guardar_json(self.arbol, ruta)

            self.assertTrue(ruta.exists())

        
if __name__ == "__main__":
    unittest.main()
