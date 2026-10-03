"""
Utilidades de seguridad y validación de datos de usuario.

- Hash y verificación de contraseñas con bcrypt.
- Validación de DNI/NIE/pasaporte, correo electrónico y fecha de
  nacimiento.
"""

import re
from datetime import date

import bcrypt

# Longitud mínima exigida a las contraseñas.
LONGITUD_MINIMA_CONTRASENA = 8

# bcrypt trabaja sobre los bytes de la contraseña y trunca a 72.
_MAXIMO_BYTES_CONTRASENA = 72

_PATRON_EMAIL = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
)

_PATRON_DNI = re.compile(
    r"^\d{8}[A-Z]$",
)

# NIE (identificación de extranjero): letra X/Y/Z + 7 dígitos + letra
# de control. Usa la misma letra sintética "P" que el identificador de
# profesorado no, así que no hay riesgo de colisión con
# _PATRON_DNI_PROFESOR_SINTETICO (que solo empieza por "P").
_PATRON_NIE = re.compile(
    r"^[XYZ]\d{7}[A-Z]$",
)

# Cada letra inicial del NIE equivale a un dígito para el cálculo de la
# letra de control, igual que en el DNI.
_PREFIJOS_NIE = {"X": "0", "Y": "1", "Z": "2"}

# Pasaporte: no existe un dígito de control estándar (el formato varía
# según el país emisor), así que solo se comprueba que sea alfanumérico
# y de una longitud razonable.
_PATRON_PASAPORTE = re.compile(
    r"^[A-Z0-9]{5,12}$",
)

# Identificador sintético para cuentas de profesorado sin DNI real
# (el registro de profesorado no lo pide). Empieza por una letra, algo
# que un DNI real nunca tiene en esa posición, así que estructuralmente
# no puede coincidir jamás con un DNI auténtico de alumnado.
_PATRON_DNI_PROFESOR_SINTETICO = re.compile(
    r"^P\d{7}[A-Z]$",
)

# Letra de control del DNI/NIE en función del resto de dividir el
# número entre 23.
_LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def hashear_contrasena(contrasena: str) -> str:
    """
    Devuelve el hash bcrypt de una contraseña en texto plano.

    El hash resultante incluye la sal y se guarda como texto en la
    base de datos.
    """

    contrasena_bytes = contrasena.encode("utf-8")[:_MAXIMO_BYTES_CONTRASENA]

    hash_bytes = bcrypt.hashpw(
        contrasena_bytes,
        bcrypt.gensalt(),
    )

    return hash_bytes.decode("utf-8")


def verificar_contrasena(
    contrasena: str,
    hash_guardado: str,
) -> bool:
    """
    Comprueba si una contraseña en texto plano coincide con su hash.
    """

    if not hash_guardado:
        return False

    contrasena_bytes = contrasena.encode("utf-8")[:_MAXIMO_BYTES_CONTRASENA]

    try:
        return bcrypt.checkpw(
            contrasena_bytes,
            hash_guardado.encode("utf-8"),
        )
    except ValueError:
        # El hash guardado no tiene un formato válido.
        return False


def normalizar_dni(dni: str) -> str:
    """
    Deja el DNI en su forma canónica: sin espacios ni guiones y en
    mayúsculas.
    """

    return re.sub(r"[\s-]", "", dni).upper()


def dni_es_valido(dni: str) -> bool:
    """
    Valida un DNI español: 8 dígitos y la letra de control correcta.
    """

    dni_normalizado = normalizar_dni(dni)

    if not _PATRON_DNI.match(dni_normalizado):
        return False

    numero = int(dni_normalizado[:8])
    letra = dni_normalizado[8]

    return _LETRAS_DNI[numero % 23] == letra


def nie_es_valido(nie: str) -> bool:
    """
    Valida un NIE (identificación de extranjero): letra inicial
    X/Y/Z, 7 dígitos y la letra de control correcta.
    """

    nie_normalizado = normalizar_dni(nie)

    if not _PATRON_NIE.match(nie_normalizado):
        return False

    numero = int(_PREFIJOS_NIE[nie_normalizado[0]] + nie_normalizado[1:8])
    letra = nie_normalizado[8]

    return _LETRAS_DNI[numero % 23] == letra


def pasaporte_es_valido(pasaporte: str) -> bool:
    """
    Valida un pasaporte: alfanumérico de 5 a 12 caracteres. No hay
    letra de control que comprobar (cada país emisor usa su propio
    formato), así que se descartan las cadenas con forma de DNI o NIE
    para no aceptar como pasaporte lo que en realidad es un DNI o un
    NIE mal escrito (con la letra de control equivocada).
    """

    pasaporte_normalizado = normalizar_dni(pasaporte)

    if not _PATRON_PASAPORTE.match(pasaporte_normalizado):
        return False

    if _PATRON_DNI.match(pasaporte_normalizado):
        return False

    if _PATRON_NIE.match(pasaporte_normalizado):
        return False

    return True


def documento_identidad_es_valido(documento: str) -> bool:
    """
    Valida un documento de identidad: DNI, NIE o pasaporte. Se usa en
    el registro de alumnado y profesorado para admitir tanto a
    nacionales como a extranjeros.
    """

    return (
        dni_es_valido(documento)
        or nie_es_valido(documento)
        or pasaporte_es_valido(documento)
    )


def identificador_profesor_es_valido(valor: str) -> bool:
    """
    Valida un identificador sintético de profesorado (``P`` + 7 dígitos
    + letra de control). No es un DNI real ni pretende serlo: es solo
    la clave interna que identifica a una cuenta de profesor que no ha
    aportado su DNI.
    """

    valor_normalizado = normalizar_dni(valor)

    if not _PATRON_DNI_PROFESOR_SINTETICO.match(valor_normalizado):
        return False

    numero = int(valor_normalizado[1:8])
    letra = valor_normalizado[8]

    return _LETRAS_DNI[numero % 23] == letra


def email_es_valido(email: str) -> bool:
    """
    Comprobación básica del formato de un correo electrónico.
    """

    return bool(_PATRON_EMAIL.match(email.strip()))


def fecha_nacimiento_es_valida(fecha_nacimiento: str) -> bool:
    """
    Valida que la fecha tenga formato ``AAAA-MM-DD``, exista en el
    calendario y no esté en el futuro.
    """

    try:
        fecha = date.fromisoformat(fecha_nacimiento.strip())
    except ValueError:
        return False

    return fecha <= date.today()


def contrasena_es_valida(contrasena: str) -> bool:
    """
    Exige una longitud mínima para la contraseña.
    """

    return len(contrasena) >= LONGITUD_MINIMA_CONTRASENA