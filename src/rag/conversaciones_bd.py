"""
Repositorio de conversaciones del chatbot en la base de datos.

Guarda cada conversación de un usuario junto con sus mensajes y el
progreso del modo guiado, de modo que al volver a entrar pueda
retomarla donde la dejó. Cada usuario puede tener como máximo cinco
conversaciones guardadas.

Además de gestionar la lista de conversaciones, esta clase implementa
la interfaz que el pipeline RAG espera para el historial
(``obtener_historial``, ``obtener_contexto``, ``agregar_mensaje`` y
``eliminar_conversacion``), por lo que puede pasarse directamente como
``historial`` a :class:`~src.rag.rag_pipeline.RAG`.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from src.core.config import RUTA_BASE_DATOS_USUARIOS
from src.core.models import Mensaje

# Número máximo de conversaciones guardadas por usuario.
MAXIMO_CONVERSACIONES = 5

# Título que recibe una conversación mientras no tiene mensajes.
TITULO_POR_DEFECTO = "Nueva conversación"

# Longitud máxima del título generado automáticamente a partir del
# primer mensaje del usuario.
_LONGITUD_TITULO_AUTOMATICO = 48

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS conversaciones (
    id             TEXT PRIMARY KEY,
    dni            TEXT NOT NULL
                   REFERENCES usuarios (dni) ON DELETE CASCADE,
    titulo         TEXT NOT NULL DEFAULT 'Nueva conversación',
    metodologia    TEXT,
    estado_guiado  TEXT,
    creada_en      TEXT NOT NULL DEFAULT (datetime('now')),
    actualizada_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mensajes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversacion_id TEXT NOT NULL
                    REFERENCES conversaciones (id) ON DELETE CASCADE,
    rol             TEXT NOT NULL,
    contenido       TEXT NOT NULL,
    creado_en       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion
    ON mensajes (conversacion_id, id);

CREATE INDEX IF NOT EXISTS idx_conversaciones_dni
    ON conversaciones (dni, actualizada_en);
"""


class ErrorConversaciones(Exception):
    """Error genérico del repositorio de conversaciones."""


class LimiteConversaciones(ErrorConversaciones):
    """El usuario ya tiene el máximo de conversaciones permitidas."""


class ConversacionNoEncontrada(ErrorConversaciones):
    """No existe la conversación indicada para ese usuario."""


@dataclass(frozen=True, slots=True)
class Conversacion:
    """
    Datos de cabecera de una conversación (sin los mensajes).
    """

    id: str
    dni: str
    titulo: str
    metodologia: str | None
    creada_en: str
    actualizada_en: str
    numero_mensajes: int = 0


def _fila_a_conversacion(fila: sqlite3.Row) -> Conversacion:
    """Convierte una fila de SQLite en un objeto Conversacion."""
    columnas = fila.keys()

    return Conversacion(
        id=fila["id"],
        dni=fila["dni"],
        titulo=fila["titulo"],
        metodologia=fila["metodologia"],
        creada_en=fila["creada_en"],
        actualizada_en=fila["actualizada_en"],
        numero_mensajes=(
            fila["numero_mensajes"] if "numero_mensajes" in columnas else 0
        ),
    )


class RepositorioConversaciones:
    """
    Acceso a las conversaciones del chatbot guardadas en SQLite.

    Comparte el mismo fichero de base de datos que los usuarios. Cada
    operación abre y cierra su propia conexión, por lo que la instancia
    puede compartirse entre peticiones.
    """

    def __init__(
        self,
        ruta_bd: Path | str = RUTA_BASE_DATOS_USUARIOS,
    ) -> None:
        """Guarda la ruta de la base de datos de usuarios y conversaciones."""
        self.ruta_bd = Path(ruta_bd)

    # ------------------------------------------------------------------
    # Infraestructura
    # ------------------------------------------------------------------
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
        """Crea las tablas de conversaciones y mensajes si no existen."""

        with self._conexion() as conexion:
            conexion.executescript(_ESQUEMA)

    # ------------------------------------------------------------------
    # Gestión de la lista de conversaciones
    # ------------------------------------------------------------------
    def listar(self, dni: str) -> list[Conversacion]:
        """
        Devuelve las conversaciones del usuario, de la más reciente a la
        más antigua.
        """

        with self._conexion() as conexion:
            filas = conexion.execute(
                """
                SELECT co.id, co.dni, co.titulo, co.metodologia,
                       co.creada_en, co.actualizada_en,
                       COUNT(m.id) AS numero_mensajes
                FROM conversaciones AS co
                LEFT JOIN mensajes AS m
                       ON m.conversacion_id = co.id
                WHERE co.dni = ?
                GROUP BY co.id
                ORDER BY co.actualizada_en DESC, co.creada_en DESC
                """,
                (dni,),
            ).fetchall()

        return [_fila_a_conversacion(fila) for fila in filas]

    def contar(self, dni: str) -> int:
        """Número de conversaciones guardadas por el usuario."""

        with self._conexion() as conexion:
            (total,) = conexion.execute(
                "SELECT COUNT(*) FROM conversaciones WHERE dni = ?",
                (dni,),
            ).fetchone()

        return total

    def obtener(
        self,
        id_conversacion: str,
        dni: str,
    ) -> Conversacion | None:
        """
        Devuelve una conversación concreta del usuario, o ``None`` si no
        existe o no le pertenece.
        """

        with self._conexion() as conexion:
            fila = conexion.execute(
                """
                SELECT co.id, co.dni, co.titulo, co.metodologia,
                       co.creada_en, co.actualizada_en,
                       COUNT(m.id) AS numero_mensajes
                FROM conversaciones AS co
                LEFT JOIN mensajes AS m
                       ON m.conversacion_id = co.id
                WHERE co.id = ? AND co.dni = ?
                GROUP BY co.id
                """,
                (id_conversacion, dni),
            ).fetchone()

        return _fila_a_conversacion(fila) if fila is not None else None

    def crear(
        self,
        dni: str,
        *,
        metodologia: str | None = None,
        titulo: str = TITULO_POR_DEFECTO,
    ) -> Conversacion:
        """
        Crea una conversación vacía para el usuario.

        Lanza :class:`LimiteConversaciones` si el usuario ya tiene el
        máximo permitido.
        """

        if self.contar(dni) >= MAXIMO_CONVERSACIONES:
            raise LimiteConversaciones(
                f"Solo puedes tener {MAXIMO_CONVERSACIONES} conversaciones "
                "guardadas. Elimina una para crear otra."
            )

        id_conversacion = str(uuid.uuid4())
        titulo_limpio = (titulo or "").strip() or TITULO_POR_DEFECTO

        with self._conexion() as conexion:
            conexion.execute(
                """
                INSERT INTO conversaciones (id, dni, titulo, metodologia)
                VALUES (?, ?, ?, ?)
                """,
                (id_conversacion, dni, titulo_limpio, metodologia),
            )

        return self.obtener(id_conversacion, dni)

    def obtener_o_crear_actual(
        self,
        dni: str,
        metodologia: str | None = None,
    ) -> Conversacion:
        """
        Devuelve la conversación más reciente del usuario. Si no tiene
        ninguna, crea la primera.
        """

        conversaciones = self.listar(dni)

        if conversaciones:
            return conversaciones[0]

        return self.crear(dni, metodologia=metodologia)

    def renombrar(
        self,
        id_conversacion: str,
        dni: str,
        titulo: str,
    ) -> None:
        """Cambia el título de una conversación del usuario."""

        titulo_limpio = (titulo or "").strip() or TITULO_POR_DEFECTO

        with self._conexion() as conexion:
            cursor = conexion.execute(
                """
                UPDATE conversaciones
                SET titulo = ?
                WHERE id = ? AND dni = ?
                """,
                (titulo_limpio[:120], id_conversacion, dni),
            )

        if cursor.rowcount == 0:
            raise ConversacionNoEncontrada(
                "La conversación no existe."
            )

    def eliminar(
        self,
        id_conversacion: str,
        dni: str,
    ) -> None:
        """Borra una conversación del usuario y todos sus mensajes."""

        with self._conexion() as conexion:
            cursor = conexion.execute(
                "DELETE FROM conversaciones WHERE id = ? AND dni = ?",
                (id_conversacion, dni),
            )

        if cursor.rowcount == 0:
            raise ConversacionNoEncontrada(
                "La conversación no existe."
            )

    def reiniciar(
        self,
        id_conversacion: str,
        dni: str,
    ) -> None:
        """
        Vacía una conversación: borra sus mensajes y su progreso guiado,
        pero conserva la conversación en la lista.
        """

        with self._conexion() as conexion:
            existe = conexion.execute(
                "SELECT 1 FROM conversaciones WHERE id = ? AND dni = ?",
                (id_conversacion, dni),
            ).fetchone()

            if existe is None:
                raise ConversacionNoEncontrada(
                    "La conversación no existe."
                )

            conexion.execute(
                "DELETE FROM mensajes WHERE conversacion_id = ?",
                (id_conversacion,),
            )

            conexion.execute(
                """
                UPDATE conversaciones
                SET estado_guiado = NULL,
                    titulo = ?,
                    actualizada_en = datetime('now')
                WHERE id = ?
                """,
                (TITULO_POR_DEFECTO, id_conversacion),
            )

    # ------------------------------------------------------------------
    # Metodología y progreso del modo guiado
    # ------------------------------------------------------------------
    def establecer_metodologia(
        self,
        id_conversacion: str,
        metodologia: str,
    ) -> None:
        """Guarda la metodología sobre la que trata la conversación."""

        with self._conexion() as conexion:
            conexion.execute(
                "UPDATE conversaciones SET metodologia = ? WHERE id = ?",
                (metodologia, id_conversacion),
            )

    def obtener_estado_guiado(
        self,
        id_conversacion: str,
    ) -> dict | None:
        """Devuelve el estado del modo guiado guardado, o ``None``."""

        with self._conexion() as conexion:
            fila = conexion.execute(
                "SELECT estado_guiado FROM conversaciones WHERE id = ?",
                (id_conversacion,),
            ).fetchone()

        if fila is None or not fila["estado_guiado"]:
            return None

        try:
            return json.loads(fila["estado_guiado"])
        except (json.JSONDecodeError, TypeError):
            return None

    def guardar_estado_guiado(
        self,
        id_conversacion: str,
        estado: dict | None,
    ) -> None:
        """Guarda (o borra, si es ``None``) el estado del modo guiado."""

        datos = (
            json.dumps(estado, ensure_ascii=False)
            if estado is not None
            else None
        )

        with self._conexion() as conexion:
            conexion.execute(
                """
                UPDATE conversaciones
                SET estado_guiado = ?, actualizada_en = datetime('now')
                WHERE id = ?
                """,
                (datos, id_conversacion),
            )

    # ------------------------------------------------------------------
    # Interfaz de historial usada por el pipeline RAG
    # ------------------------------------------------------------------
    def obtener_historial(
        self,
        id_conversacion: str,
    ) -> list[Mensaje]:
        """Devuelve todos los mensajes de la conversación, en orden."""

        with self._conexion() as conexion:
            filas = conexion.execute(
                """
                SELECT rol, contenido
                FROM mensajes
                WHERE conversacion_id = ?
                ORDER BY id
                """,
                (id_conversacion,),
            ).fetchall()

        return [
            Mensaje(rol=fila["rol"], contenido=fila["contenido"])
            for fila in filas
        ]

    def obtener_contexto(
        self,
        id_conversacion: str,
        max_mensajes: int = 6,
    ) -> list[Mensaje]:
        """Devuelve los últimos mensajes para usarlos como contexto."""

        return self.obtener_historial(id_conversacion)[-max_mensajes:]

    def agregar_mensaje(
        self,
        id_conversacion: str,
        mensaje: Mensaje,
    ) -> None:
        """
        Añade un mensaje a la conversación y actualiza su fecha de
        actividad. El primer mensaje del usuario se usa para titular la
        conversación automáticamente.
        """

        with self._conexion() as conexion:
            conexion.execute(
                """
                INSERT INTO mensajes (conversacion_id, rol, contenido)
                VALUES (?, ?, ?)
                """,
                (id_conversacion, mensaje.rol, mensaje.contenido),
            )

            if mensaje.rol == "user":
                fila = conexion.execute(
                    """
                    SELECT co.titulo AS titulo,
                           (
                               SELECT COUNT(*)
                               FROM mensajes
                               WHERE conversacion_id = co.id AND rol = 'user'
                           ) AS mensajes_usuario
                    FROM conversaciones AS co
                    WHERE co.id = ?
                    """,
                    (id_conversacion,),
                ).fetchone()

                if (
                    fila is not None
                    and fila["mensajes_usuario"] == 1
                    and (fila["titulo"] or "") == TITULO_POR_DEFECTO
                ):
                    conexion.execute(
                        "UPDATE conversaciones SET titulo = ? WHERE id = ?",
                        (
                            self._resumir_titulo(mensaje.contenido),
                            id_conversacion,
                        ),
                    )

            conexion.execute(
                """
                UPDATE conversaciones
                SET actualizada_en = datetime('now')
                WHERE id = ?
                """,
                (id_conversacion,),
            )

    def eliminar_conversacion(self, id_conversacion: str) -> None:
        """
        Borra una conversación por su identificador.

        Forma parte de la interfaz de historial del pipeline RAG; la
        comprobación de propiedad la hace la capa web con :meth:`eliminar`.
        """

        with self._conexion() as conexion:
            conexion.execute(
                "DELETE FROM conversaciones WHERE id = ?",
                (id_conversacion,),
            )

    # ------------------------------------------------------------------
    # Auxiliares privados
    # ------------------------------------------------------------------
    @staticmethod
    def _resumir_titulo(texto: str) -> str:
        """Genera un título corto a partir del primer mensaje, recortándolo si es largo."""
        texto = " ".join((texto or "").split())

        if not texto:
            return TITULO_POR_DEFECTO

        if len(texto) <= _LONGITUD_TITULO_AUTOMATICO:
            return texto

        return texto[:_LONGITUD_TITULO_AUTOMATICO].rstrip() + "…"
