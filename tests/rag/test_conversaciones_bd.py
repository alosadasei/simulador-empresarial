import tempfile
import unittest
from pathlib import Path

from src.core.models import Mensaje
from src.rag.conversaciones_bd import (
    MAXIMO_CONVERSACIONES,
    TITULO_POR_DEFECTO,
    ConversacionNoEncontrada,
    LimiteConversaciones,
    RepositorioConversaciones,
)
from src.usuarios import RepositorioUsuarios

DNI = "12345678Z"
OTRO_DNI = "00000001R"


class TestRepositorioConversaciones(unittest.TestCase):
    """Pruebas de RepositorioConversaciones."""

    def setUp(self):
        """Crea una base de datos temporal con un usuario y el repositorio de conversaciones."""
        self.directorio = tempfile.TemporaryDirectory()
        ruta_bd = Path(self.directorio.name) / "usuarios.db"

        usuarios = RepositorioUsuarios(ruta_bd=ruta_bd)
        usuarios.inicializar()
        usuarios.crear_usuario(
            nombre_usuario="ana",
            nombre="Ana",
            fecha_nacimiento="2000-01-01",
            email="ana@ejemplo.com",
            dni=DNI,
            contrasena="contrasena-larga",
        )
        usuarios.crear_usuario(
            nombre_usuario="bea",
            nombre="Bea",
            fecha_nacimiento="2000-01-01",
            email="bea@ejemplo.com",
            dni=OTRO_DNI,
            contrasena="contrasena-larga",
        )

        self.repo = RepositorioConversaciones(ruta_bd=ruta_bd)
        self.repo.inicializar()

    def tearDown(self):
        """Elimina la base de datos temporal."""
        self.directorio.cleanup()

    def test_crear_y_listar(self):
        """Comprueba: crear y listar."""
        conversacion = self.repo.crear(DNI, metodologia="lean_startup")

        self.assertEqual(conversacion.titulo, TITULO_POR_DEFECTO)
        self.assertEqual(conversacion.metodologia, "lean_startup")

        conversaciones = self.repo.listar(DNI)
        self.assertEqual(len(conversaciones), 1)
        self.assertEqual(conversaciones[0].id, conversacion.id)

    def test_limite_de_cinco_conversaciones(self):
        """Comprueba: limite de cinco conversaciones."""
        for _ in range(MAXIMO_CONVERSACIONES):
            self.repo.crear(DNI)

        with self.assertRaises(LimiteConversaciones):
            self.repo.crear(DNI)

        # Otro usuario no se ve afectado por el límite del primero.
        self.assertIsNotNone(self.repo.crear(OTRO_DNI))

    def test_obtener_solo_del_propietario(self):
        """Comprueba: obtener solo del propietario."""
        conversacion = self.repo.crear(DNI)

        self.assertIsNotNone(self.repo.obtener(conversacion.id, DNI))
        self.assertIsNone(self.repo.obtener(conversacion.id, OTRO_DNI))

    def test_agregar_mensaje_actualiza_historial_y_titulo(self):
        """Comprueba: agregar mensaje actualiza historial y titulo."""
        conversacion = self.repo.crear(DNI)

        self.repo.agregar_mensaje(
            conversacion.id,
            Mensaje("user", "¿Qué es el lienzo de propuesta de valor?"),
        )
        self.repo.agregar_mensaje(
            conversacion.id,
            Mensaje("bot", "Es una herramienta para..."),
        )

        historial = self.repo.obtener_historial(conversacion.id)
        self.assertEqual([m.rol for m in historial], ["user", "bot"])

        actualizada = self.repo.obtener(conversacion.id, DNI)
        self.assertEqual(
            actualizada.titulo,
            "¿Qué es el lienzo de propuesta de valor?",
        )
        self.assertEqual(actualizada.numero_mensajes, 2)

    def test_titulo_largo_se_recorta(self):
        """Comprueba: titulo largo se recorta."""
        conversacion = self.repo.crear(DNI)
        pregunta = "palabra " * 30

        self.repo.agregar_mensaje(conversacion.id, Mensaje("user", pregunta))

        titulo = self.repo.obtener(conversacion.id, DNI).titulo
        self.assertLessEqual(len(titulo), 49)
        self.assertTrue(titulo.endswith("…"))

    def test_obtener_contexto_devuelve_ultimos(self):
        """Comprueba: obtener contexto devuelve ultimos."""
        conversacion = self.repo.crear(DNI)

        for indice in range(10):
            self.repo.agregar_mensaje(
                conversacion.id,
                Mensaje("user", f"pregunta {indice}"),
            )

        contexto = self.repo.obtener_contexto(conversacion.id, max_mensajes=3)
        self.assertEqual(
            [m.contenido for m in contexto],
            ["pregunta 7", "pregunta 8", "pregunta 9"],
        )

    def test_reiniciar_vacia_mensajes_y_estado(self):
        """Comprueba: reiniciar vacia mensajes y estado."""
        conversacion = self.repo.crear(DNI)
        self.repo.agregar_mensaje(conversacion.id, Mensaje("user", "hola"))
        self.repo.guardar_estado_guiado(
            conversacion.id,
            {"activo": True, "completados": ["p1"]},
        )

        self.repo.reiniciar(conversacion.id, DNI)

        self.assertEqual(self.repo.obtener_historial(conversacion.id), [])
        self.assertIsNone(self.repo.obtener_estado_guiado(conversacion.id))
        self.assertEqual(
            self.repo.obtener(conversacion.id, DNI).titulo,
            TITULO_POR_DEFECTO,
        )
        # Sigue contando como una conversación de la lista.
        self.assertEqual(len(self.repo.listar(DNI)), 1)

    def test_reiniciar_conversacion_ajena_falla(self):
        """Comprueba: reiniciar conversacion ajena falla."""
        conversacion = self.repo.crear(DNI)

        with self.assertRaises(ConversacionNoEncontrada):
            self.repo.reiniciar(conversacion.id, OTRO_DNI)

    def test_eliminar_conversacion(self):
        """Comprueba: eliminar conversacion."""
        conversacion = self.repo.crear(DNI)

        self.repo.eliminar(conversacion.id, DNI)

        self.assertEqual(self.repo.listar(DNI), [])
        with self.assertRaises(ConversacionNoEncontrada):
            self.repo.eliminar(conversacion.id, DNI)

    def test_estado_guiado_ida_y_vuelta(self):
        """Comprueba: estado guiado ida y vuelta."""
        conversacion = self.repo.crear(DNI)

        self.assertIsNone(self.repo.obtener_estado_guiado(conversacion.id))

        estado = {
            "activo": True,
            "completados": ["p1", "p2"],
            "paso_actual": "p2",
            "pasos_ids": ["p1", "p2", "p3"],
        }
        self.repo.guardar_estado_guiado(conversacion.id, estado)

        self.assertEqual(
            self.repo.obtener_estado_guiado(conversacion.id),
            estado,
        )

    def test_obtener_o_crear_actual(self):
        """Comprueba: obtener o crear actual."""
        primera = self.repo.obtener_o_crear_actual(DNI)
        segunda = self.repo.obtener_o_crear_actual(DNI)

        self.assertEqual(primera.id, segunda.id)
        self.assertEqual(len(self.repo.listar(DNI)), 1)

    def test_borrar_usuario_arrastra_sus_conversaciones(self):
        """Comprueba: borrar usuario arrastra sus conversaciones."""
        conversacion = self.repo.crear(DNI)
        self.repo.agregar_mensaje(conversacion.id, Mensaje("user", "hola"))

        usuarios = RepositorioUsuarios(ruta_bd=self.repo.ruta_bd)
        usuarios.eliminar_usuario(DNI)

        self.assertEqual(self.repo.listar(DNI), [])


if __name__ == "__main__":
    unittest.main()
