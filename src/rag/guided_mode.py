"""
Gestiona el estado del checklist del modo guiado.

GuidedMode no conoce ninguna metodología concreta.
La estructura de pasos la prepara guided_steps.py.
"""


class GuidedMode:
    """Gestiona el progreso del alumno en el modo checklist."""

    def estado_inicial(self, pasos_ids: list[str]) -> dict:
        """
        Crea el estado inicial del checklist.
        """

        return {
            "activo": True,
            "pasos_ids": pasos_ids,
            "completados": [],
            "paso_actual": None,
        }

    def seleccionar_paso(
        self,
        estado: dict,
        paso_id: str,
    ) -> dict:
        """Selecciona el elemento que el alumno quiere trabajar."""

        if not estado.get("activo"):
            return estado

        if paso_id not in estado.get("pasos_ids", []):
            return estado

        estado["paso_actual"] = paso_id

        return estado

    def marcar_completado(
        self,
        estado: dict,
        paso_id: str,
    ) -> dict:
        """Marca un elemento como completado."""

        if paso_id not in estado.get("pasos_ids", []):
            return estado

        if paso_id not in estado["completados"]:
            estado["completados"].append(paso_id)

        return estado

    def desmarcar_completado(
        self,
        estado: dict,
        paso_id: str,
    ) -> dict:
        """Permite desmarcar un elemento previamente completado."""

        if paso_id in estado.get("completados", []):
            estado["completados"].remove(paso_id)

        return estado

    def obtener_paso_actual(
        self,
        estado: dict,
        arbol,
    ):
        """Devuelve el nodo actualmente seleccionado."""

        paso_id = estado.get("paso_actual")

        if not paso_id:
            return None

        return arbol.buscar_por_id(paso_id)

    def esta_completado(
        self,
        estado: dict,
        paso_id: str,
    ) -> bool:
        """Indica si un elemento está completado."""

        return paso_id in estado.get("completados", [])

    def esta_activo(self, estado: dict) -> bool:
        """Indica si el modo guiado está activo."""

        return estado.get("activo", False)
