import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.usuarios import RepositorioUsuarios
from src.usuarios.correo import CorreoNoConfigurado, correo_configurado, enviar_correo
from src.usuarios.verificacion import (
    RESULTADO_BLOQUEADO,
    RESULTADO_EXPIRADO,
    RESULTADO_INCORRECTO,
    RESULTADO_OK,
    RESULTADO_SIN_CODIGO,
    RepositorioVerificacion,
)

DNI = "12345678Z"


def _crear_usuario(ruta_bd):
    """Crea el usuario de prueba en la base de datos."""
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
    return usuarios


class TestRepositorioVerificacion(unittest.TestCase):
    """Pruebas de RepositorioVerificacion."""

    def setUp(self):
        """Prepara la base de datos temporal (y, en los flujos, una app Flask con el envío de correo simulado)."""
        self.directorio = tempfile.TemporaryDirectory()
        self.ruta_bd = Path(self.directorio.name) / "usuarios.db"
        self.usuarios = _crear_usuario(self.ruta_bd)

        self.repo = RepositorioVerificacion(ruta_bd=self.ruta_bd)
        self.repo.inicializar()

    def tearDown(self):
        """Elimina la base de datos temporal."""
        self.directorio.cleanup()

    def test_crear_codigo_formato(self):
        """Comprueba: crear codigo formato."""
        codigo = self.repo.crear_codigo(DNI)

        self.assertRegex(codigo, r"^\d{6}$")

    def test_codigo_correcto_una_sola_vez(self):
        """Comprueba: codigo correcto una sola vez."""
        codigo = self.repo.crear_codigo(DNI)

        self.assertEqual(self.repo.comprobar(DNI, codigo), RESULTADO_OK)
        # Ya no queda código pendiente.
        self.assertEqual(self.repo.comprobar(DNI, codigo), RESULTADO_SIN_CODIGO)

    def test_codigo_incorrecto_incrementa_intentos_y_bloquea(self):
        """Comprueba: codigo incorrecto incrementa intentos y bloquea."""
        self.repo.crear_codigo(DNI)

        for _ in range(5):
            self.assertEqual(
                self.repo.comprobar(DNI, "000000"),
                RESULTADO_INCORRECTO,
            )

        # Sexto intento: bloqueado y código eliminado.
        self.assertEqual(self.repo.comprobar(DNI, "000000"), RESULTADO_BLOQUEADO)
        self.assertEqual(self.repo.comprobar(DNI, "000000"), RESULTADO_SIN_CODIGO)

    def test_crear_codigo_reemplaza_el_anterior(self):
        """Comprueba: crear codigo reemplaza el anterior."""
        primero = self.repo.crear_codigo(DNI)
        segundo = self.repo.crear_codigo(DNI)

        self.assertNotEqual(primero, segundo)
        self.assertEqual(self.repo.comprobar(DNI, primero), RESULTADO_INCORRECTO)
        self.assertEqual(self.repo.comprobar(DNI, segundo), RESULTADO_OK)

    def test_codigo_expirado(self):
        """Comprueba: codigo expirado."""
        codigo = self.repo.crear_codigo(DNI)

        with sqlite3.connect(self.ruta_bd) as conexion:
            conexion.execute(
                "UPDATE codigos_verificacion SET expira_en = '2000-01-01 00:00:00' "
                "WHERE dni = ?",
                (DNI,),
            )

        self.assertEqual(self.repo.comprobar(DNI, codigo), RESULTADO_EXPIRADO)
        self.assertEqual(self.repo.comprobar(DNI, codigo), RESULTADO_SIN_CODIGO)

    def test_espera_para_reenviar(self):
        """Comprueba: espera para reenviar."""
        self.assertEqual(self.repo.segundos_para_reenviar(DNI), 0)

        self.repo.crear_codigo(DNI)
        espera = self.repo.segundos_para_reenviar(DNI)

        self.assertGreater(espera, 0)
        self.assertLessEqual(espera, 60)

    def test_limpiar(self):
        """Comprueba: limpiar."""
        self.repo.crear_codigo(DNI)
        self.repo.limpiar(DNI)

        self.assertEqual(self.repo.comprobar(DNI, "000000"), RESULTADO_SIN_CODIGO)

    def test_borrar_usuario_arrastra_su_codigo(self):
        """Comprueba: borrar usuario arrastra su codigo."""
        self.repo.crear_codigo(DNI)

        self.usuarios.eliminar_usuario(DNI)

        with sqlite3.connect(self.ruta_bd) as conexion:
            (total,) = conexion.execute(
                "SELECT COUNT(*) FROM codigos_verificacion"
            ).fetchone()

        self.assertEqual(total, 0)


class TestCorreo(unittest.TestCase):
    """Pruebas de Correo."""

    def test_no_configurado_por_defecto(self):
        # En el entorno de pruebas no hay variables SMTP.
        """Comprueba: no configurado por defecto."""
        self.assertFalse(correo_configurado())

        with self.assertRaises(CorreoNoConfigurado):
            enviar_correo("a@b.com", "asunto", "cuerpo")


class TestFlujoLoginDosPasos(unittest.TestCase):
    """Integración de las rutas de acceso en dos pasos."""

    def setUp(self):
        """Prepara la base de datos temporal (y, en los flujos, una app Flask con el envío de correo simulado)."""
        from flask import Flask

        import web.services.usuarios as su
        import web.services.verificacion as verif
        from web.auth import auth_bp

        self.directorio = tempfile.TemporaryDirectory()
        ruta_bd = Path(self.directorio.name) / "usuarios.db"

        self.su = su
        self.verif = verif
        su.repositorio.ruta_bd = ruta_bd
        verif.repositorio.ruta_bd = ruta_bd

        # Captura de los correos "enviados".
        self.correos = []
        verif.enviar_correo = lambda destino, asunto, cuerpo: self.correos.append(
            (destino, asunto, cuerpo)
        )
        verif.correo_configurado = lambda: True

        app = Flask(
            "test_app_dos_pasos",
            template_folder=os.path.join(_RAIZ, "web", "templates"),
            static_folder=os.path.join(_RAIZ, "web", "static"),
        )
        app.secret_key = "test"
        app.register_blueprint(auth_bp)

        app.add_url_rule("/", "public.inicio", lambda: "inicio")
        app.add_url_rule(
            "/prof",
            "profesor.gestionar_documentos",
            lambda: "panel",
        )

        su.inicializar_usuarios()
        su.repositorio.crear_usuario(
            nombre_usuario="lucia",
            nombre="Lucia",
            fecha_nacimiento="2001-01-01",
            email="lucia@ejemplo.com",
            dni=DNI,
            contrasena="clave12345",
        )

        self.cliente = app.test_client()

    def tearDown(self):
        """Elimina la base de datos temporal."""
        self.directorio.cleanup()

    def _codigo_del_ultimo_correo(self):
        """Extrae el código del último correo enviado."""
        cuerpo = self.correos[-1][2]
        return re.search(r"\b(\d{6})\b", cuerpo).group(1)

    def test_login_no_autentica_sin_codigo(self):
        """Comprueba: login no autentica sin codigo."""
        respuesta = self.cliente.post(
            "/login",
            data={"identificador": "lucia", "contrasena": "clave12345"},
            follow_redirects=False,
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login/verificar", respuesta.headers["Location"])
        self.assertEqual(len(self.correos), 1)

        with self.cliente.session_transaction() as sesion:
            self.assertIsNone(sesion.get("usuario"))
            self.assertEqual(
                sesion["verificacion_pendiente"]["dni"],
                DNI,
            )

    def test_codigo_correcto_completa_el_login(self):
        """Comprueba: codigo correcto completa el login."""
        self.cliente.post(
            "/login",
            data={"identificador": "lucia", "contrasena": "clave12345"},
        )

        codigo = self._codigo_del_ultimo_correo()

        respuesta = self.cliente.post(
            "/login/verificar",
            data={"codigo": codigo},
            follow_redirects=False,
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("/"))

        with self.cliente.session_transaction() as sesion:
            self.assertEqual(sesion["usuario"]["dni"], DNI)
            self.assertNotIn("verificacion_pendiente", sesion)

    def test_codigo_incorrecto_no_autentica(self):
        """Comprueba: codigo incorrecto no autentica."""
        self.cliente.post(
            "/login",
            data={"identificador": "lucia", "contrasena": "clave12345"},
        )

        respuesta = self.cliente.post(
            "/login/verificar",
            data={"codigo": "000000"},
            follow_redirects=True,
        )

        self.assertIn("no es correcto", respuesta.get_data(as_text=True))

        with self.cliente.session_transaction() as sesion:
            self.assertIsNone(sesion.get("usuario"))

    def test_contrasena_incorrecta_no_envia_codigo(self):
        """Comprueba: contrasena incorrecta no envia codigo."""
        respuesta = self.cliente.post(
            "/login",
            data={"identificador": "lucia", "contrasena": "mal"},
            follow_redirects=True,
        )

        self.assertIn(
            "usuario o la contraseña no son correctos",
            respuesta.get_data(as_text=True),
        )
        self.assertEqual(self.correos, [])

    def test_login_bloqueado_si_correo_no_configurado(self):
        """Comprueba: login bloqueado si correo no configurado."""
        self.verif.correo_configurado = lambda: False

        respuesta = self.cliente.post(
            "/login",
            data={"identificador": "lucia", "contrasena": "clave12345"},
            follow_redirects=True,
        )

        self.assertIn(
            "servicio de correo no está disponible",
            respuesta.get_data(as_text=True),
        )
        self.assertEqual(self.correos, [])

    def test_verificar_sin_pendiente_redirige_a_login(self):
        """Comprueba: verificar sin pendiente redirige a login."""
        respuesta = self.cliente.get("/login/verificar", follow_redirects=False)

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("/login"))

    def test_profesor_entra_por_el_login_de_alumnos(self):
        """Comprueba: profesor entra por el login de alumnos."""
        from src.usuarios.modelos import ROL_PROFESOR, ROL_USUARIO

        self.su.repositorio.crear_usuario(
            nombre_usuario="profe",
            nombre="Profe",
            fecha_nacimiento="1980-01-01",
            email="profe@ejemplo.com",
            dni="00000001R",
            contrasena="clave12345",
            rol=ROL_PROFESOR,
        )

        respuesta = self.cliente.post(
            "/login",
            data={"identificador": "profe", "contrasena": "clave12345"},
            follow_redirects=False,
        )

        # Se le deja pasar: se envía el código como a cualquier cuenta.
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login/verificar", respuesta.headers["Location"])

        codigo = self._codigo_del_ultimo_correo()

        respuesta = self.cliente.post(
            "/login/verificar",
            data={"codigo": codigo},
            follow_redirects=False,
        )

        # Aterriza en la parte pública, NO en el panel de profesorado.
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("/"))
        self.assertFalse(respuesta.headers["Location"].endswith("/prof"))

        with self.cliente.session_transaction() as sesion:
            self.assertEqual(sesion["usuario"]["rol"], "profesor")

        # Nunca aparece en el listado de alumnado.
        dnis_alumnado = [
            u.dni for u in self.su.repositorio.listar(rol=ROL_USUARIO)
        ]
        self.assertNotIn("00000001R", dnis_alumnado)


if __name__ == "__main__":
    unittest.main()
