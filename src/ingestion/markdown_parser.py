"""Módulo para analizar y parsear documentos Markdown."""

import re

_HEADER_RE = re.compile(r"^(#{1,5})\s+(.*)")


class MarkdownNode:  
    """Nodo del árbol de encabezados"""

    __slots__ = ("nivel", "titulo", "lineas", "hijos")

    def __init__(self, nivel: int, titulo: str | None):
        """Crea un nodo vacío con su nivel de encabezado y su título."""
        self.nivel = nivel
        self.titulo = titulo
        self.lineas: list[str] = []
        self.hijos: list["MarkdownNode"] = []
        
    @property
    def texto(self) -> str:
        """Devuelve el contenido del nodo como un único texto."""
        return "\n".join(self.lineas).strip()


def parsear_markdown(texto: str) -> MarkdownNode:
    """Recibe Markdown y devuelve su representación estructurada."""

    raiz = MarkdownNode(nivel=0, titulo=None)
    pila: list[MarkdownNode] = [raiz]

    for linea in texto.splitlines():
        linea_limpia = linea.strip()
        match = _HEADER_RE.match(linea_limpia)

        if match:
            nivel = len(match.group(1))
            titulo = match.group(2).strip()

            # Desapilar hasta encontrar el padre correcto (nivel estrictamente menor)
            while pila[-1].nivel >= nivel:
                pila.pop()

            nuevo = MarkdownNode(nivel=nivel, titulo=titulo)
            pila[-1].hijos.append(nuevo)
            pila.append(nuevo)
        else:
            if linea_limpia:
                pila[-1].lineas.append(linea_limpia)
            elif pila[-1].lineas:
                pila[-1].lineas.append("")

    return raiz
