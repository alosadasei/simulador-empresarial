"""
Define la estructura del modo guiado para cada metodología.

Este módulo decide qué elementos del árbol son relevantes
para mostrar en el checklist.

GuidedMode no conoce las metodologías concretas.
"""


def obtener_pasos_simulacion(arbol):
    """
    Obtiene los bloques de Simulación empresarial
    que contienen fases reales.
    """

    procesos = []

    def recorrer(nodo):
        """Recorre el árbol recursivamente y acumula los nodos que contienen fases de simulación."""
        if nodo.titulo and "simulación empresarial" in nodo.titulo.lower():
            fases = obtener_fases_simulacion(nodo)

            if fases:
                procesos.append(nodo)

        for hijo in nodo.hijos:
            recorrer(hijo)

    recorrer(arbol.raiz)

    return procesos


def obtener_fases_simulacion(proceso):
    """
    Obtiene únicamente las fases de un bloque
    de Simulación empresarial.

    Los ejemplos no se consideran pasos.
    """

    return [
        hijo
        for hijo in proceso.hijos
        if (hijo.titulo and hijo.titulo.lower().startswith("fase "))
    ]


def obtener_pasos_lean(arbol):
    """
    Obtiene los módulos principales de Lean Startup.

    Solo se incluyen los módulos 1 a 6.
    Introducción, módulo 0 y anexos quedan fuera.
    """

    pasos = []

    for nodo in arbol.raiz.hijos:

        if not nodo.titulo:
            continue

        titulo = nodo.titulo.upper()

        if any(titulo.startswith(f"MÓDULO {numero}.") for numero in range(1, 7)):
            pasos.append(nodo)

    return pasos


def es_actividad_lean(nodo):
    """
    Determina si un nodo de Lean Startup representa
    una actividad que el alumno puede completar.
    """

    if not nodo.titulo:
        return False

    titulo = nodo.titulo.upper()

    return titulo.startswith("ACTIVIDAD NÚMERO")


def obtener_actividades_lean(nodo):
    """
    Busca recursivamente las actividades de un módulo.

    Las actividades pueden encontrarse en distintos niveles
    del árbol.
    """

    actividades = []

    for hijo in nodo.hijos:

        if es_actividad_lean(hijo):
            actividades.append(hijo)

        actividades.extend(obtener_actividades_lean(hijo))

    return actividades


def obtener_pasos(metodologia: str, arbol):
    """
    Devuelve los bloques principales de la guía
    correspondiente a la metodología.
    """

    if metodologia == "simulacion_empresarial":
        return obtener_pasos_simulacion(arbol)

    if metodologia == "lean_startup":
        return obtener_pasos_lean(arbol)

    raise ValueError(f"No existe una guía para la metodología: {metodologia}")


def obtener_ids_pasos(metodologia: str, arbol) -> list[str]:
    """
    Devuelve los IDs de todos los elementos que pueden
    seleccionarse/completarse en el checklist.
    """

    if metodologia == "simulacion_empresarial":
        procesos = obtener_pasos_simulacion(arbol)

        ids = []

        for proceso in procesos:
            fases = obtener_fases_simulacion(proceso)

            for fase in fases:
                ids.append(fase.id)

        return ids

    if metodologia == "lean_startup":
        modulos = obtener_pasos_lean(arbol)

        ids = []

        for modulo in modulos:
            actividades = obtener_actividades_lean(modulo)

            for actividad in actividades:
                ids.append(actividad.id)

        return ids

    raise ValueError(f"No existe una guía para la metodología: {metodologia}")
