import tempfile
import unittest
from pathlib import Path

from src.usuarios import (
    ROL_PROFESOR,
    ROL_USUARIO,
    DatosInvalidos,
    RepositorioUsuarios,
    UsuarioNoEncontrado,
    UsuarioYaExiste,
)

# DNIs con letra de control válida usados en las pruebas.
DNI_VALIDO = "12345678Z"
OTRO_DNI_VALIDO = "00000001R"

# NIE con letra de control válida usado en las pruebas.
NIE_VALIDO = "X1234567L"

# Pasaporte válido usado en las pruebas (sin letra de control).
PASAPORTE_VALIDO = "AB123456"

DATOS_BASE = {
    "nombre_usuario": "ana",
    "nombre": "Ana Pérez",
    "fecha_nacimiento": "2000-05-17",
    "email": "ana@ejemplo.com",
    "dni": DNI_VALIDO,
    "contrasena": "contrasena-larga",
}


class TestRepositorioUsuarios(unittest.TestCase):
    """Pruebas de RepositorioUsuarios."""

    def setUp(self):
        """Crea una base de datos temporal de usuarios."""
        self.directorio = tempfile.TemporaryDirectory()
        ruta_bd = Path(self.directorio.name) / "usuarios.db"

        self.repositorio = RepositorioUsuarios(ruta_bd=ruta_bd)
        self.repositorio.inicializar()

    def tearDown(self):
        """Elimina la base de datos temporal."""
        self.directorio.cleanup()

    def test_crear_usuario_rol_por_defecto(self):
        """Comprueba: crear usuario rol por defecto."""
        usuario = self.repositorio.crear_usuario(**DATOS_BASE)

        self.assertEqual(usuario.rol, ROL_USUARIO)
        self.assertFalse(usuario.es_profesor)
        self.assertEqual(usuario.dni, DNI_VALIDO)

    def test_dni_se_normaliza(self):
        """Comprueba: dni se normaliza."""
        datos = {**DATOS_BASE, "dni": "12345678-z"}

        usuario = self.repositorio.crear_usuario(**datos)

        self.assertEqual(usuario.dni, DNI_VALIDO)
        self.assertIsNotNone(self.repositorio.obtener_por_dni("12345678z"))

    def test_dni_invalido_rechazado(self):
        """Comprueba: dni invalido rechazado."""
        datos = {**DATOS_BASE, "dni": "12345678A"}

        with self.assertRaises(DatosInvalidos):
            self.repositorio.crear_usuario(**datos)

    def test_nie_valido_aceptado(self):
        """Comprueba: nie valido aceptado."""
        datos = {**DATOS_BASE, "dni": NIE_VALIDO}

        usuario = self.repositorio.crear_usuario(**datos)

        self.assertEqual(usuario.dni, NIE_VALIDO)

    def test_nie_se_normaliza(self):
        """Comprueba: nie se normaliza."""
        datos = {**DATOS_BASE, "dni": "x1234567-l"}

        usuario = self.repositorio.crear_usuario(**datos)

        self.assertEqual(usuario.dni, NIE_VALIDO)
        self.assertIsNotNone(self.repositorio.obtener_por_dni("x1234567l"))

    def test_nie_invalido_rechazado(self):
        """Comprueba: nie invalido rechazado."""
        datos = {**DATOS_BASE, "dni": "X1234567A"}

        with self.assertRaises(DatosInvalidos):
            self.repositorio.crear_usuario(**datos)

    def test_pasaporte_valido_aceptado(self):
        """Comprueba: pasaporte valido aceptado."""
        datos = {**DATOS_BASE, "dni": PASAPORTE_VALIDO}

        usuario = self.repositorio.crear_usuario(**datos)

        self.assertEqual(usuario.dni, PASAPORTE_VALIDO)

    def test_pasaporte_se_normaliza(self):
        """Comprueba: pasaporte se normaliza."""
        datos = {**DATOS_BASE, "dni": "ab123456"}

        usuario = self.repositorio.crear_usuario(**datos)

        self.assertEqual(usuario.dni, PASAPORTE_VALIDO)
        self.assertIsNotNone(self.repositorio.obtener_por_dni("ab123456"))

    def test_pasaporte_demasiado_corto_rechazado(self):
        """Comprueba: pasaporte demasiado corto rechazado."""
        datos = {**DATOS_BASE, "dni": "AB12"}

        with self.assertRaises(DatosInvalidos):
            self.repositorio.crear_usuario(**datos)

    def test_dni_mal_escrito_no_se_cuela_como_pasaporte(self):
        # Tiene la forma exacta de un DNI (8 dígitos + letra), pero la
        # letra de control no es correcta: debe rechazarse como DNI
        # inválido y no aceptarse como si fuera un pasaporte.
        """Comprueba: dni mal escrito no se cuela como pasaporte."""
        datos = {**DATOS_BASE, "dni": "12345678A"}

        with self.assertRaises(DatosInvalidos):
            self.repositorio.crear_usuario(**datos)

    def test_email_invalido_rechazado(self):
        """Comprueba: email invalido rechazado."""
        datos = {**DATOS_BASE, "email": "sin-arroba"}

        with self.assertRaises(DatosInvalidos):
            self.repositorio.crear_usuario(**datos)

    def test_fecha_futura_rechazada(self):
        """Comprueba: fecha futura rechazada."""
        datos = {**DATOS_BASE, "fecha_nacimiento": "2999-01-01"}

        with self.assertRaises(DatosInvalidos):
            self.repositorio.crear_usuario(**datos)

    def test_contrasena_corta_rechazada(self):
        """Comprueba: contrasena corta rechazada."""
        datos = {**DATOS_BASE, "contrasena": "corta"}

        with self.assertRaises(DatosInvalidos):
            self.repositorio.crear_usuario(**datos)

    def test_dni_duplicado_rechazado(self):
        """Comprueba: dni duplicado rechazado."""
        self.repositorio.crear_usuario(**DATOS_BASE)

        datos = {
            **DATOS_BASE,
            "nombre_usuario": "otra",
            "email": "otra@ejemplo.com",
        }

        with self.assertRaises(UsuarioYaExiste):
            self.repositorio.crear_usuario(**datos)

    def test_nombre_usuario_duplicado_ignora_mayusculas(self):
        """Comprueba: nombre usuario duplicado ignora mayusculas."""
        self.repositorio.crear_usuario(**DATOS_BASE)

        datos = {
            **DATOS_BASE,
            "nombre_usuario": "ANA",
            "email": "otra@ejemplo.com",
            "dni": OTRO_DNI_VALIDO,
        }

        with self.assertRaises(UsuarioYaExiste):
            self.repositorio.crear_usuario(**datos)

    def test_autenticar_con_nombre_dni_o_email(self):
        """Comprueba: autenticar con nombre dni o email."""
        self.repositorio.crear_usuario(**DATOS_BASE)

        for identificador in ("ana", "ANA", DNI_VALIDO, "ana@ejemplo.com"):
            with self.subTest(identificador=identificador):
                usuario = self.repositorio.autenticar(
                    identificador,
                    "contrasena-larga",
                )
                self.assertIsNotNone(usuario)
                self.assertEqual(usuario.nombre_usuario, "ana")

    def test_autenticar_contrasena_incorrecta(self):
        """Comprueba: autenticar contrasena incorrecta."""
        self.repositorio.crear_usuario(**DATOS_BASE)

        self.assertIsNone(
            self.repositorio.autenticar("ana", "otra-cosa")
        )

    def test_autenticar_usuario_inexistente(self):
        """Comprueba: autenticar usuario inexistente."""
        self.assertIsNone(
            self.repositorio.autenticar("fantasma", "contrasena-larga")
        )

    def test_cambiar_contrasena(self):
        """Comprueba: cambiar contrasena."""
        self.repositorio.crear_usuario(**DATOS_BASE)

        self.repositorio.cambiar_contrasena(DNI_VALIDO, "nueva-contrasena")

        self.assertIsNone(
            self.repositorio.autenticar("ana", "contrasena-larga")
        )
        self.assertIsNotNone(
            self.repositorio.autenticar("ana", "nueva-contrasena")
        )

    def test_eliminar_usuario_inexistente(self):
        """Comprueba: eliminar usuario inexistente."""
        with self.assertRaises(UsuarioNoEncontrado):
            self.repositorio.eliminar_usuario(OTRO_DNI_VALIDO)

    def test_listar_y_contar_por_rol(self):
        """Comprueba: listar y contar por rol."""
        self.repositorio.crear_usuario(**DATOS_BASE)
        self.repositorio.crear_usuario(
            nombre_usuario="prof",
            nombre="Profe",
            fecha_nacimiento="1980-01-01",
            email="prof@ejemplo.com",
            dni=OTRO_DNI_VALIDO,
            contrasena="contrasena-profe",
            rol=ROL_PROFESOR,
        )

        self.assertEqual(self.repositorio.contar(), 2)
        self.assertEqual(self.repositorio.contar(rol=ROL_PROFESOR), 1)

        usuarios = self.repositorio.listar(rol=ROL_USUARIO)
        self.assertEqual([u.nombre_usuario for u in usuarios], ["ana"])

    def test_asegurar_profesor_inicial_es_idempotente(self):
        """Comprueba: asegurar profesor inicial es idempotente."""
        self.repositorio.asegurar_profesor_inicial("profe_test", "clave-larga")
        self.repositorio.asegurar_profesor_inicial("profe_test", "clave-larga")

        self.assertEqual(self.repositorio.contar(rol=ROL_PROFESOR), 1)

        profesor = self.repositorio.autenticar("profe_test", "clave-larga")
        self.assertIsNotNone(profesor)
        self.assertTrue(profesor.es_profesor)


if __name__ == "__main__":
    unittest.main()
