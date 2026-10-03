import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.usuarios import RepositorioUsuarios
from src.usuarios.modelos import ROL_PROFESOR
from src.usuarios.restablecimiento import RepositorioRestablecimiento
from src.usuarios.verificacion import (
    RESULTADO_INCORRECTO,
    RESULTADO_OK,
    RepositorioVerificacion,
)

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DNI_ALUMNO = "12345678Z"
DNI_PROFE = "00000001R"
EMAIL_ALUMNO = "alumno@ejemplo.com"
EMAIL_PROFE = "profe@ejemplo.com"


def _sembrar_usuarios(ruta_bd):
    """Crea en la base de datos los usuarios usados por las pruebas."""
    usuarios = RepositorioUsuarios(ruta_bd=ruta_bd)
    usuarios.inicializar()
    usuarios.crear_usuario(
        nombre_usuario="alumno",
        nombre="Alumno",
        fecha_nacimiento="2001-01-01",
        email=EMAIL_ALUMNO,
        dni=DNI_ALUMNO,
        contrasena="clave-original",
    )
    usuarios.crear_usuario(
        nombre_usuario="profe",
        nombre="Profe",
        fecha_nacimiento="1980-01-01",
        email=EMAIL_PROFE,
        dni=DNI_PROFE,
        contrasena="clave-original",
        rol=ROL_PROFESOR,
    )
    return usuarios


class TestRepositorioRestablecimiento(unittest.TestCase):
    """Pruebas de RepositorioRestablecimiento."""

    def setUp(self):
        """Prepara la base de datos temporal (y, en los flujos, una app Flask con el envío de correo simulado)."""
        self.directorio = tempfile.TemporaryDirectory()
        self.ruta_bd = Path(self.directorio.name) / "usuarios.db"
        _sembrar_usuarios(self.ruta_bd)

        self.repo = RepositorioRestablecimiento(ruta_bd=self.ruta_bd)
        self.repo.inicializar()

    def tearDown(self):
        """Elimina la base de datos temporal."""
        self.directorio.cleanup()

    def test_usa_tabla_independiente(self):
        """Comprueba: usa tabla independiente."""
        verificacion = RepositorioVerificacion(ruta_bd=self.ruta_bd)
        verificacion.inicializar()

        codigo = self.repo.crear_codigo(DNI_ALUMNO)

        conexion = sqlite3.connect(self.ruta_bd)
        try:
            (n_rest,) = conexion.execute(
                "SELECT COUNT(*) FROM codigos_restablecimiento"
            ).fetchone()
            (n_verif,) = conexion.execute(
                "SELECT COUNT(*) FROM codigos_verificacion"
            ).fetchone()
        finally:
            conexion.close()

        self.assertEqual(n_rest, 1)
        self.assertEqual(n_verif, 0)
        self.assertEqual(self.repo.comprobar(DNI_ALUMNO, codigo), RESULTADO_OK)

    def test_codigo_incorrecto(self):
        """Comprueba: codigo incorrecto."""
        self.repo.crear_codigo(DNI_ALUMNO)

        self.assertEqual(
            self.repo.comprobar(DNI_ALUMNO, "000000"),
            RESULTADO_INCORRECTO,
        )


class TestFlujoRecuperarContrasena(unittest.TestCase):
    """Pruebas de FlujoRecuperarContrasena."""

    def setUp(self):
        """Prepara la base de datos temporal (y, en los flujos, una app Flask con el envío de correo simulado)."""
        from flask import Flask

        import web.services.restablecimiento as rest
        import web.services.usuarios as su
        import web.services.verificacion as verif
        from web.auth import auth_bp
        from web.profesorado import profesorado_bp

        self.directorio = tempfile.TemporaryDirectory()
        ruta_bd = Path(self.directorio.name) / "usuarios.db"

        self.rest = rest
        su.repositorio.ruta_bd = ruta_bd
        verif.repositorio.ruta_bd = ruta_bd
        rest.repositorio.ruta_bd = ruta_bd

        self.correos = []
        rest.enviar_correo = lambda destino, asunto, cuerpo: self.correos.append(
            (destino, asunto, cuerpo)
        )
        rest.correo_configurado = lambda: True

        app = Flask(
            "test_app_recuperar",
            template_folder=os.path.join(_RAIZ, "web", "templates"),
            static_folder=os.path.join(_RAIZ, "web", "static"),
        )
        app.secret_key = "test"
        app.register_blueprint(auth_bp)
        app.register_blueprint(profesorado_bp)
        app.add_url_rule("/", "public.inicio", lambda: "inicio")
        app.add_url_rule(
            "/prof",
            "profesor.gestionar_documentos",
            lambda: "panel",
        )

        su.inicializar_usuarios()
        _sembrar_usuarios(ruta_bd)

        self.cliente = app.test_client()

    def tearDown(self):
        """Elimina la base de datos temporal."""
        self.directorio.cleanup()

    def _codigo(self):
        """Extrae el código de 6 dígitos del último correo enviado."""
        return re.search(r"\b(\d{6})\b", self.correos[-1][2]).group(1)

    # -- enlaces en ambos accesos --------------------------------------
    def test_enlace_en_ambos_login(self):
        """Comprueba: enlace en ambos login."""
        alumnado = self.cliente.get("/login").get_data(as_text=True)
        profesorado = self.cliente.get("/profesorado/acceso").get_data(
            as_text=True
        )

        self.assertIn("/recuperar-contrasena", alumnado)
        self.assertIn("¿Has olvidado tu contraseña?", alumnado)
        self.assertIn("origen=profesorado", profesorado)

    # -- paso 1 -------------------------------------------------------
    def test_email_conocido_envia_codigo(self):
        """Comprueba: email conocido envia codigo."""
        respuesta = self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_ALUMNO, "origen": "alumnado"},
            follow_redirects=False,
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/restablecer-contrasena", respuesta.headers["Location"])
        self.assertEqual(len(self.correos), 1)

        with self.cliente.session_transaction() as sesion:
            self.assertEqual(
                sesion["restablecimiento_pendiente"]["dni"],
                DNI_ALUMNO,
            )

    def test_email_desconocido_no_envia_pero_responde_igual(self):
        """Comprueba: email desconocido no envia pero responde igual."""
        respuesta = self.cliente.post(
            "/recuperar-contrasena",
            data={"email": "nadie@ejemplo.com", "origen": "alumnado"},
            follow_redirects=True,
        )

        self.assertIn("Si existe una cuenta", respuesta.get_data(as_text=True))
        self.assertEqual(self.correos, [])

    def test_rol_no_coincide_no_envia(self):
        # Email de profesor entrando por la puerta de alumnado.
        """Comprueba: rol no coincide no envia."""
        self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_PROFE, "origen": "alumnado"},
        )
        self.assertEqual(self.correos, [])

        # Ahora por la puerta correcta.
        self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_PROFE, "origen": "profesorado"},
        )
        self.assertEqual(len(self.correos), 1)

    def test_bloqueado_si_correo_no_configurado(self):
        """Comprueba: bloqueado si correo no configurado."""
        self.rest.correo_configurado = lambda: False

        respuesta = self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_ALUMNO, "origen": "alumnado"},
            follow_redirects=True,
        )

        self.assertIn(
            "servicio de correo no está disponible",
            respuesta.get_data(as_text=True),
        )
        self.assertEqual(self.correos, [])

    # -- paso 2 -----------------------------------------------------
    def test_cambio_de_contrasena_completo(self):
        """Comprueba: cambio de contrasena completo."""
        self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_ALUMNO, "origen": "alumnado"},
        )
        codigo = self._codigo()

        respuesta = self.cliente.post(
            "/restablecer-contrasena",
            data={
                "codigo": codigo,
                "contrasena": "clave-nueva-2026",
                "confirmacion": "clave-nueva-2026",
            },
            follow_redirects=False,
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("/login"))

        usuarios = RepositorioUsuarios(ruta_bd=self.rest.repositorio.ruta_bd)
        self.assertIsNotNone(
            usuarios.autenticar(EMAIL_ALUMNO, "clave-nueva-2026")
        )
        self.assertIsNone(
            usuarios.autenticar(EMAIL_ALUMNO, "clave-original")
        )

        with self.cliente.session_transaction() as sesion:
            self.assertNotIn("restablecimiento_pendiente", sesion)
            self.assertNotIn("restablecimiento_origen", sesion)

    def test_profesor_vuelve_a_su_login(self):
        """Comprueba: profesor vuelve a su login."""
        self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_PROFE, "origen": "profesorado"},
        )
        codigo = self._codigo()

        respuesta = self.cliente.post(
            "/restablecer-contrasena",
            data={
                "codigo": codigo,
                "contrasena": "clave-nueva-2026",
                "confirmacion": "clave-nueva-2026",
            },
        )

        self.assertTrue(
            respuesta.headers["Location"].endswith("/profesorado/acceso")
        )

    def test_codigo_incorrecto_no_cambia_contrasena(self):
        """Comprueba: codigo incorrecto no cambia contrasena."""
        self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_ALUMNO, "origen": "alumnado"},
        )

        respuesta = self.cliente.post(
            "/restablecer-contrasena",
            data={
                "codigo": "000000",
                "contrasena": "clave-nueva-2026",
                "confirmacion": "clave-nueva-2026",
            },
            follow_redirects=True,
        )

        self.assertIn(
            "código no es correcto",
            respuesta.get_data(as_text=True),
        )

        usuarios = RepositorioUsuarios(ruta_bd=self.rest.repositorio.ruta_bd)
        self.assertIsNotNone(
            usuarios.autenticar(EMAIL_ALUMNO, "clave-original")
        )

    def test_contrasenas_no_coinciden_no_consume_codigo(self):
        """Comprueba: contrasenas no coinciden no consume codigo."""
        self.cliente.post(
            "/recuperar-contrasena",
            data={"email": EMAIL_ALUMNO, "origen": "alumnado"},
        )
        codigo = self._codigo()

        self.cliente.post(
            "/restablecer-contrasena",
            data={
                "codigo": codigo,
                "contrasena": "clave-nueva-2026",
                "confirmacion": "otra-cosa-distinta",
            },
        )

        # El código sigue siendo válido: segundo intento correcto funciona.
        respuesta = self.cliente.post(
            "/restablecer-contrasena",
            data={
                "codigo": codigo,
                "contrasena": "clave-nueva-2026",
                "confirmacion": "clave-nueva-2026",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        usuarios = RepositorioUsuarios(ruta_bd=self.rest.repositorio.ruta_bd)
        self.assertIsNotNone(
            usuarios.autenticar(EMAIL_ALUMNO, "clave-nueva-2026")
        )

    def test_restablecer_sin_origen_redirige(self):
        """Comprueba: restablecer sin origen redirige."""
        respuesta = self.cliente.get(
            "/restablecer-contrasena",
            follow_redirects=False,
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            respuesta.headers["Location"].endswith("/recuperar-contrasena")
        )


if __name__ == "__main__":
    unittest.main()
