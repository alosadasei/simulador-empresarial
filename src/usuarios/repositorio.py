"""
Repositorio de usuarios sobre una base de datos SQLite.

Encapsula todo el acceso a la tabla ``usuarios``: creación del esquema,
alta de cuentas, autenticación y consultas. El resto de la aplicación
trabaja siempre con objetos :class:`Usuario`, nunca con filas de SQL.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.core.config import (
    CONTRASENA_PROFESOR,
    RUTA_BASE_DATOS_USUARIOS,
    USUARIO_PROFESOR,
)
from src.usuarios.modelos import (
    ROL_PROFESOR,
    ROL_USUARIO,
    ROLES_VALIDOS,
    Usuario,
)
from src.usuarios.seguridad import (
    contrasena_es_valida,
    documento_identidad_es_valido,
    email_es_valido,
    fecha_nacimiento_es_valida,
    hashear_contrasena,
    identificador_profesor_es_valido,
    normalizar_dni,
    verificar_contrasena,
)

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    dni              TEXT PRIMARY KEY,
    nombre_usuario   TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nombre           TEXT NOT NULL,
    fecha_nacimiento TEXT NOT NULL,
    email            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    rol              TEXT NOT NULL CHECK (rol IN ('usuario', 'profesor')),
    contrasena_hash  TEXT NOT NULL,
    activo           INTEGER NOT NULL DEFAULT 1,
    creado_en        TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

_COLUMNAS_USUARIO = (
    "dni, nombre_usuario, nombre, fecha_nacimiento, email, rol, activo"
)

class ErrorUsuarios(Exception):
    """Error genérico del repositorio de usuarios."""


class DatosInvalidos(ErrorUsuarios):
    """Los datos proporcionados no cumplen las validaciones."""


class UsuarioYaExiste(ErrorUsuarios):
    """Ya existe una cuenta con ese DNI, nombre de usuario o email."""


class UsuarioNoEncontrado(ErrorUsuarios):
    """No existe ninguna cuenta que cumpla la condición indicada."""


def _fila_a_usuario(fila: sqlite3.Row) -> Usuario:
    """Convierte una fila de la tabla en un objeto de dominio."""

    return Usuario(
        dni=fila["dni"],
        nombre_usuario=fila["nombre_usuario"],
        nombre=fila["nombre"],
        fecha_nacimiento=fila["fecha_nacimiento"],
        email=fila["email"],
        rol=fila["rol"],
        activo=bool(fila["activo"]),
    )


class RepositorioUsuarios:
    """
    Acceso a la base de datos de usuarios.

    Se instancia una sola vez y se reutiliza. Cada operación abre y
    cierra su propia conexión, por lo que es seguro compartir la
    instancia entre las peticiones de Flask.
    """

    def __init__(
        self,
        ruta_bd: Path | str = RUTA_BASE_DATOS_USUARIOS,
    ) -> None:
        """Guarda la ruta de la base de datos de usuarios."""
        self.ruta_bd = Path(ruta_bd)

    # ------------------------------------------------------------------
    # Infraestructura
    # ------------------------------------------------------------------
    @contextmanager
    def _conexion(self):
        """
        Abre una conexión a SQLite con claves foráneas activas y las
        filas accesibles por nombre de columna.
        """

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
        """
        Crea la tabla de usuarios si todavía no existe.

        También migra bases de datos creadas antes de añadir la
        columna ``activo``, dando por activas a las cuentas existentes.
        """

        with self._conexion() as conexion:
            conexion.executescript(_ESQUEMA)

            columnas = {
                fila["name"]
                for fila in conexion.execute(
                    "PRAGMA table_info(usuarios)"
                ).fetchall()
            }

            if "activo" not in columnas:
                conexion.execute(
                    "ALTER TABLE usuarios ADD COLUMN activo "
                    "INTEGER NOT NULL DEFAULT 1"
                )

    # ------------------------------------------------------------------
    # Altas y modificaciones
    # ------------------------------------------------------------------
    def crear_usuario(
        self,
        *,
        nombre_usuario: str,
        nombre: str,
        fecha_nacimiento: str,
        email: str,
        dni: str,
        contrasena: str,
        rol: str = ROL_USUARIO,
    ) -> Usuario:
        """
        Da de alta una cuenta nueva.

        Valida los datos, calcula el hash de la contraseña e inserta la
        fila. Lanza :class:`DatosInvalidos` si algún campo no es válido y
        :class:`UsuarioYaExiste` si el DNI, el nombre de usuario o el
        email ya están registrados.
        """

        datos = self._validar_datos(
            nombre_usuario=nombre_usuario,
            nombre=nombre,
            fecha_nacimiento=fecha_nacimiento,
            email=email,
            dni=dni,
            rol=rol,
        )

        if not contrasena_es_valida(contrasena):
            raise DatosInvalidos(
                "La contraseña debe tener al menos 8 caracteres."
            )

        datos["contrasena_hash"] = hashear_contrasena(contrasena)

        try:
            with self._conexion() as conexion:
                conexion.execute(
                    """
                    INSERT INTO usuarios (
                        dni,
                        nombre_usuario,
                        nombre,
                        fecha_nacimiento,
                        email,
                        rol,
                        contrasena_hash
                    ) VALUES (
                        :dni,
                        :nombre_usuario,
                        :nombre,
                        :fecha_nacimiento,
                        :email,
                        :rol,
                        :contrasena_hash
                    )
                    """,
                    datos,
                )
        except sqlite3.IntegrityError as error:
            raise UsuarioYaExiste(
                "Ya existe una cuenta con ese DNI, nombre de usuario o "
                "correo electrónico."
            ) from error

        return self.obtener_por_dni(datos["dni"])

    def cambiar_contrasena(
        self,
        dni: str,
        nueva_contrasena: str,
    ) -> None:
        """
        Actualiza la contraseña de una cuenta existente.
        """

        if not contrasena_es_valida(nueva_contrasena):
            raise DatosInvalidos(
                "La contraseña debe tener al menos 8 caracteres."
            )

        dni_normalizado = normalizar_dni(dni)

        with self._conexion() as conexion:
            cursor = conexion.execute(
                "UPDATE usuarios SET contrasena_hash = ? WHERE dni = ?",
                (
                    hashear_contrasena(nueva_contrasena),
                    dni_normalizado,
                ),
            )

        if cursor.rowcount == 0:
            raise UsuarioNoEncontrado(
                f"No existe ninguna cuenta con el DNI {dni_normalizado}."
            )

    def cambiar_estado(self, dni: str, activo: bool) -> None:
        """
        Da de alta o de baja una cuenta (columna ``activo``).

        Una cuenta dada de baja no puede iniciar sesión, pero conserva
        sus datos y conversaciones.
        """

        dni_normalizado = normalizar_dni(dni)

        with self._conexion() as conexion:
            cursor = conexion.execute(
                "UPDATE usuarios SET activo = ? WHERE dni = ?",
                (
                    1 if activo else 0,
                    dni_normalizado,
                ),
            )

        if cursor.rowcount == 0:
            raise UsuarioNoEncontrado(
                f"No existe ninguna cuenta con el DNI {dni_normalizado}."
            )

    def eliminar_usuario(self, dni: str) -> None:
        """
        Borra una cuenta por su DNI.
        """

        dni_normalizado = normalizar_dni(dni)

        with self._conexion() as conexion:
            cursor = conexion.execute(
                "DELETE FROM usuarios WHERE dni = ?",
                (dni_normalizado,),
            )

        if cursor.rowcount == 0:
            raise UsuarioNoEncontrado(
                f"No existe ninguna cuenta con el DNI {dni_normalizado}."
            )

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def obtener_por_dni(self, dni: str) -> Usuario | None:
        """Devuelve la cuenta con ese DNI, o ``None`` si no existe."""

        return self._buscar_uno(
            "dni = ?",
            (normalizar_dni(dni),),
        )

    def obtener_por_nombre_usuario(
        self,
        nombre_usuario: str,
    ) -> Usuario | None:
        """Devuelve la cuenta con ese nombre de usuario, o ``None``."""

        return self._buscar_uno(
            "nombre_usuario = ? COLLATE NOCASE",
            (nombre_usuario.strip(),),
        )

    def obtener_por_email(self, email: str) -> Usuario | None:
        """Devuelve la cuenta con ese email, o ``None``."""

        return self._buscar_uno(
            "email = ? COLLATE NOCASE",
            (email.strip(),),
        )

    def listar(self, rol: str | None = None) -> list[Usuario]:
        """
        Devuelve todas las cuentas, opcionalmente filtradas por rol,
        ordenadas por nombre de usuario.
        """

        consulta = f"SELECT {_COLUMNAS_USUARIO} FROM usuarios"
        parametros: tuple = ()

        if rol is not None:
            consulta += " WHERE rol = ?"
            parametros = (rol,)

        consulta += " ORDER BY nombre_usuario COLLATE NOCASE"

        with self._conexion() as conexion:
            filas = conexion.execute(consulta, parametros).fetchall()

        return [_fila_a_usuario(fila) for fila in filas]

    def contar(self, rol: str | None = None) -> int:
        """Número de cuentas registradas (filtrable por rol)."""

        consulta = "SELECT COUNT(*) FROM usuarios"
        parametros: tuple = ()

        if rol is not None:
            consulta += " WHERE rol = ?"
            parametros = (rol,)

        with self._conexion() as conexion:
            (total,) = conexion.execute(consulta, parametros).fetchone()

        return total

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------
    def autenticar(
        self,
        identificador: str,
        contrasena: str,
    ) -> Usuario | None:
        """
        Comprueba las credenciales y devuelve el :class:`Usuario`
        correspondiente, o ``None`` si no coinciden.

        El ``identificador`` puede ser el nombre de usuario, el DNI o el
        correo electrónico.
        """

        identificador = identificador.strip()

        if not identificador or not contrasena:
            return None

        with self._conexion() as conexion:
            fila = conexion.execute(
                """
                SELECT * FROM usuarios
                WHERE nombre_usuario = :ident COLLATE NOCASE
                   OR email = :ident COLLATE NOCASE
                   OR dni = :dni
                LIMIT 1
                """,
                {
                    "ident": identificador,
                    "dni": normalizar_dni(identificador),
                },
            ).fetchone()

        if fila is None:
            # Se calcula un hash de todos modos para no revelar por
            # tiempos de respuesta si la cuenta existe.
            verificar_contrasena(contrasena, "")
            return None

        if not verificar_contrasena(contrasena, fila["contrasena_hash"]):
            return None

        return _fila_a_usuario(fila)

    # ------------------------------------------------------------------
    # Siembra del profesor inicial
    # ------------------------------------------------------------------
    def asegurar_profesor_inicial(
        self,
        nombre_usuario: str = USUARIO_PROFESOR,
        contrasena: str = CONTRASENA_PROFESOR,
    ) -> None:
        """
        Crea una cuenta de profesor de arranque si todavía no hay
        ninguna cuenta con rol ``profesor``.

        Los datos personales son marcadores de posición: se espera que
        el profesor los edite más adelante. El DNI se deriva del nombre
        de usuario para que sea estable entre reinicios.
        """

        if self.contar(rol=ROL_PROFESOR) > 0:
            return

        if self.obtener_por_nombre_usuario(nombre_usuario) is not None:
            return

        dni_placeholder = self._dni_placeholder(nombre_usuario)

        try:
            self.crear_usuario(
                nombre_usuario=nombre_usuario,
                nombre="Profesorado",
                fecha_nacimiento="1970-01-01",
                email=f"{nombre_usuario}@ejemplo.local",
                dni=dni_placeholder,
                contrasena=contrasena,
                rol=ROL_PROFESOR,
            )
        except UsuarioYaExiste:
            # Otro proceso lo ha creado simultáneamente: no es un error.
            pass

    # ------------------------------------------------------------------
    # Auxiliares privados
    # ------------------------------------------------------------------
    def _buscar_uno(
        self,
        condicion: str,
        parametros: tuple,
    ) -> Usuario | None:
        """Ejecuta una consulta con la condición dada y devuelve el primer usuario o None."""
        consulta = (
            f"SELECT {_COLUMNAS_USUARIO} FROM usuarios "
            f"WHERE {condicion} LIMIT 1"
        )

        with self._conexion() as conexion:
            fila = conexion.execute(consulta, parametros).fetchone()

        return _fila_a_usuario(fila) if fila is not None else None

    def _validar_datos(
        self,
        *,
        nombre_usuario: str,
        nombre: str,
        fecha_nacimiento: str,
        email: str,
        dni: str,
        rol: str,
    ) -> dict:
        """Valida y normaliza los datos de un usuario; lanza error si alguno no es válido."""
        nombre_usuario = (nombre_usuario or "").strip()
        nombre = (nombre or "").strip()
        fecha_nacimiento = (fecha_nacimiento or "").strip()
        email = (email or "").strip()
        dni_normalizado = normalizar_dni(dni or "")

        if rol not in ROLES_VALIDOS:
            raise DatosInvalidos(f"El rol '{rol}' no es válido.")

        if len(nombre_usuario) < 3:
            raise DatosInvalidos(
                "El nombre de usuario debe tener al menos 3 caracteres."
            )

        if not nombre:
            raise DatosInvalidos("El nombre es obligatorio.")

        if not documento_identidad_es_valido(dni_normalizado) and not (
            rol == ROL_PROFESOR
            and identificador_profesor_es_valido(dni_normalizado)
        ):
            raise DatosInvalidos("El DNI/NIE/pasaporte no es válido.")

        if not email_es_valido(email):
            raise DatosInvalidos("El correo electrónico no es válido.")

        if not fecha_nacimiento_es_valida(fecha_nacimiento):
            raise DatosInvalidos(
                "La fecha de nacimiento no es válida "
                "(formato AAAA-MM-DD y no puede estar en el futuro)."
            )

        return {
            "dni": dni_normalizado,
            "nombre_usuario": nombre_usuario,
            "nombre": nombre,
            "fecha_nacimiento": fecha_nacimiento,
            "email": email,
            "rol": rol,
        }

    @staticmethod
    def _dni_placeholder(semilla: str) -> str:
        """
        Genera un identificador sintético para cuentas de profesorado
        sin DNI real (empieza por ``P``, formato imposible en un DNI
        auténtico, así que nunca puede coincidir con uno de verdad).

        Es determinista: la misma semilla produce siempre el mismo
        identificador, de modo que los reinicios no crean cuentas
        duplicadas.
        """

        import hashlib

        from src.usuarios.seguridad import _LETRAS_DNI

        digest = hashlib.sha256(semilla.encode("utf-8")).hexdigest()
        numero = int(digest[:12], 16) % 10_000_000
        letra = _LETRAS_DNI[numero % 23]

        return f"P{numero:07d}{letra}"