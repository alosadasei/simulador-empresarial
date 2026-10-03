"""
Repositorio de códigos de un solo uso enviados por correo.

Se usa tanto para la verificación en dos pasos del inicio de sesión
(tabla ``codigos_verificacion``) como para el restablecimiento de
contraseña (tabla ``codigos_restablecimiento``), que reutiliza esta
misma clase con otro nombre de tabla.

Cada usuario puede tener, como mucho, un código pendiente por tabla. Al
pedir uno nuevo se reemplaza el anterior. El código se guarda con hash
bcrypt y tiene fecha de caducidad y un número máximo de intentos.

Se guarda en el mismo fichero SQLite que los usuarios
(``data/usuarios.db``).
"""

import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.core.config import (
    RUTA_BASE_DATOS_USUARIOS,
    VERIFICACION_ESPERA_REENVIO_SEGUNDOS,
    VERIFICACION_LONGITUD_CODIGO,
    VERIFICACION_MAXIMO_INTENTOS,
    VERIFICACION_VALIDEZ_MINUTOS,
)
from src.usuarios.seguridad import hashear_contrasena, verificar_contrasena

# Resultados posibles de comprobar un código.
RESULTADO_OK = "ok"
RESULTADO_INCORRECTO = "incorrecto"
RESULTADO_EXPIRADO = "expirado"
RESULTADO_BLOQUEADO = "bloqueado"
RESULTADO_SIN_CODIGO = "sin_codigo"

_FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"

# Nombres de tabla admitidos. El nombre nunca procede de la entrada del
# usuario, pero se valida igualmente porque se interpola en el SQL.
TABLA_VERIFICACION = "codigos_verificacion"
TABLA_RESTABLECIMIENTO = "codigos_restablecimiento"
_TABLAS_PERMITIDAS = frozenset({TABLA_VERIFICACION, TABLA_RESTABLECIMIENTO})

_PLANTILLA_ESQUEMA = """
CREATE TABLE IF NOT EXISTS {tabla} (
    dni         TEXT PRIMARY KEY
                REFERENCES usuarios (dni) ON DELETE CASCADE,
    codigo_hash TEXT NOT NULL,
    expira_en   TEXT NOT NULL,
    intentos    INTEGER NOT NULL DEFAULT 0,
    enviado_en  TEXT NOT NULL
);
"""


def _ahora() -> datetime:
    """Momento actual en UTC."""
    return datetime.now(timezone.utc)


def _a_texto(momento: datetime) -> str:
    """Convierte una fecha al formato de texto guardado en la base de datos."""
    return momento.strftime(_FORMATO_FECHA)


def _desde_texto(texto: str) -> datetime:
    """Convierte el texto guardado en la base de datos a una fecha UTC."""
    return datetime.strptime(texto, _FORMATO_FECHA).replace(
        tzinfo=timezone.utc
    )


class RepositorioVerificacion:
    """Acceso a una tabla de códigos de un solo uso."""

    def __init__(
        self,
        ruta_bd: Path | str = RUTA_BASE_DATOS_USUARIOS,
        tabla: str = TABLA_VERIFICACION,
    ) -> None:
        """Guarda la ruta de la base de datos y valida que la tabla esté permitida."""
        if tabla not in _TABLAS_PERMITIDAS:
            raise ValueError(f"Nombre de tabla no permitido: {tabla!r}")

        self.ruta_bd = Path(ruta_bd)
        self._tabla = tabla

    @contextmanager
    def _conexion(self):
        """Abre una conexión SQLite con claves foráneas activas y la cierra al terminar."""
        if self.ruta_bd.parent and not self.ruta_bd.parent.exists():
            self.ruta_bd.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        conexion = sqlite3.connect(self.ruta_bd)
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON;")

        try:
            with conexion:
                yield conexion
        finally:
            conexion.close()

    def inicializar(self) -> None:
        """Crea la tabla de códigos si no existe."""

        with self._conexion() as conexion:
            conexion.executescript(
                _PLANTILLA_ESQUEMA.format(tabla=self._tabla)
            )

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    def crear_codigo(self, dni: str) -> str:
        """
        Genera un código nuevo para el usuario, reemplazando cualquier
        código anterior, y lo devuelve en claro para poder enviarlo.
        """

        codigo = "".join(
            secrets.choice("0123456789")
            for _ in range(VERIFICACION_LONGITUD_CODIGO)
        )

        ahora = _ahora()
        expira = ahora + timedelta(minutes=VERIFICACION_VALIDEZ_MINUTOS)

        with self._conexion() as conexion:
            conexion.execute(
                f"""
                INSERT INTO {self._tabla}
                    (dni, codigo_hash, expira_en, intentos, enviado_en)
                VALUES (?, ?, ?, 0, ?)
                ON CONFLICT (dni) DO UPDATE SET
                    codigo_hash = excluded.codigo_hash,
                    expira_en   = excluded.expira_en,
                    intentos    = 0,
                    enviado_en  = excluded.enviado_en
                """,
                (
                    dni,
                    hashear_contrasena(codigo),
                    _a_texto(expira),
                    _a_texto(ahora),
                ),
            )

        return codigo

    def comprobar(self, dni: str, codigo: str) -> str:
        """
        Comprueba el código introducido.

        Devuelve uno de: ``ok``, ``incorrecto``, ``expirado``,
        ``bloqueado`` o ``sin_codigo``. En todos los casos salvo
        ``incorrecto`` se elimina el código pendiente.
        """

        with self._conexion() as conexion:
            fila = conexion.execute(
                f"""
                SELECT codigo_hash, expira_en, intentos
                FROM {self._tabla}
                WHERE dni = ?
                """,
                (dni,),
            ).fetchone()

            if fila is None:
                return RESULTADO_SIN_CODIGO

            if _desde_texto(fila["expira_en"]) < _ahora():
                conexion.execute(
                    f"DELETE FROM {self._tabla} WHERE dni = ?",
                    (dni,),
                )
                return RESULTADO_EXPIRADO

            if fila["intentos"] >= VERIFICACION_MAXIMO_INTENTOS:
                conexion.execute(
                    f"DELETE FROM {self._tabla} WHERE dni = ?",
                    (dni,),
                )
                return RESULTADO_BLOQUEADO

            if verificar_contrasena(codigo, fila["codigo_hash"]):
                conexion.execute(
                    f"DELETE FROM {self._tabla} WHERE dni = ?",
                    (dni,),
                )
                return RESULTADO_OK

            conexion.execute(
                f"""
                UPDATE {self._tabla}
                SET intentos = intentos + 1
                WHERE dni = ?
                """,
                (dni,),
            )
            return RESULTADO_INCORRECTO

    def segundos_para_reenviar(self, dni: str) -> int:
        """
        Segundos que faltan para poder pedir otro código. ``0`` si ya se
        puede (o si no hay ninguno pendiente).
        """

        with self._conexion() as conexion:
            fila = conexion.execute(
                f"SELECT enviado_en FROM {self._tabla} WHERE dni = ?",
                (dni,),
            ).fetchone()

        if fila is None:
            return 0

        transcurrido = (_ahora() - _desde_texto(fila["enviado_en"])).total_seconds()
        restante = VERIFICACION_ESPERA_REENVIO_SEGUNDOS - transcurrido

        if restante <= 0:
            return 0

        return int(restante) + 1

    def limpiar(self, dni: str) -> None:
        """Elimina el código pendiente del usuario, si lo hay."""

        with self._conexion() as conexion:
            conexion.execute(
                f"DELETE FROM {self._tabla} WHERE dni = ?",
                (dni,),
            )
