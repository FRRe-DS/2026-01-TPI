# Conector a M6 (Viajes): M2 le pide los viajes por su API, nunca a su base (RNF-05).
#
# PROVISORIO: por ahora solo está la firma de obtener_viaje, para poder programar y probar las
# calificaciones (T03). La implementación real (pedido HTTP, 2 s por intento, un reintento y 503)
# es parte de T02: hay que completar el cuerpo sin cambiar el nombre ni los parámetros, porque
# rutas/calificaciones.py ya la usa. Ver docs/tareas/T02-historial-de-viajes.md.
from errores import ErrorDominio


def obtener_viaje(viaje_id: str, autorizacion: str) -> dict | None:
    """GET /trips/{id} de M6. Devuelve None si M6 responde 404."""
    # Hasta que T02 la implemente, M2 responde como si M6 no contestara
    raise ErrorDominio(503, "/errores/dependencia-no-disponible", "M6 no está disponible",
                       "Todavía no está conectado M6 (Viajes). Probá de nuevo más tarde.")
