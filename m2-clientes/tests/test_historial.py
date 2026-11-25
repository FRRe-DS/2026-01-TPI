import pytest
from pydantic import ValidationError
from models import ViajeResumen, PaginaViajes


def test_viaje_resumen_acepta_datos_validos():
    viaje = ViajeResumen(
        viajeId="550e8400-e29b-41d4-a716-446655440000",
        estado="COMPLETED",
        tipoVehiculo="AUTO",
        origen="Resistencia",
        destino="Corrientes",
        iniciadoEn="2026-11-24T10:00:00",
        conductorId="550e8400-e29b-41d4-a716-446655440001",
        calificado=True,
    )

    assert viaje.viajeId is not None
    assert viaje.estado == "COMPLETED"
    assert viaje.tipoVehiculo == "AUTO"


def test_viaje_resumen_rechaza_sin_viaje_id():
    with pytest.raises(ValidationError):
        ViajeResumen(
            estado="COMPLETED",
        )


def test_viaje_resumen_rechaza_sin_estado():
    with pytest.raises(ValidationError):
        ViajeResumen(
            viajeId="550e8400-e29b-41d4-a716-446655440000",
        )


def test_pagina_viajes_acepta_datos_validos():
    pagina = PaginaViajes(
        items=[],
        page=0,
        size=10,
        totalElementos=25,
        totalPaginas=3,
    )

    assert pagina.page == 0
    assert pagina.size == 10
    assert pagina.totalElementos == 25
    assert pagina.totalPaginas == 3
    assert pagina.items == []


def test_pagina_viajes_rechaza_sin_items():
    with pytest.raises(ValidationError):
        PaginaViajes(
            page=0,
            size=10,
            totalElementos=25,
            totalPaginas=3,
        )


def test_pagina_viajes_rechaza_sin_page():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            size=10,
            totalElementos=25,
            totalPaginas=3,
        )


def test_pagina_viajes_rechaza_sin_size():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            page=0,
            totalElementos=25,
            totalPaginas=3,
        )


def test_pagina_viajes_rechaza_sin_total_elementos():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            page=0,
            size=10,
            totalPaginas=3,
        )


def test_pagina_viajes_rechaza_sin_total_paginas():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            page=0,
            size=10,
            totalElementos=25,
        )


def test_viaje_resumen_rechaza_uuid_invalido():
    with pytest.raises(ValidationError):
        ViajeResumen(
            viajeId="123",
            estado="COMPLETED",
        )


def test_viaje_resumen_rechaza_tipo_vehiculo_invalido():
    with pytest.raises(ValidationError):
        ViajeResumen(
            viajeId="550e8400-e29b-41d4-a716-446655440000",
            estado="COMPLETED",
            tipoVehiculo="BICICLETA",
        )


def test_pagina_viajes_rechaza_page_negativo():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            page=-1,
            size=10,
            totalElementos=25,
            totalPaginas=3,
        )


def test_pagina_viajes_rechaza_size_cero():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            page=0,
            size=0,
            totalElementos=25,
            totalPaginas=3,
        )


def test_pagina_viajes_rechaza_total_elementos_negativo():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            page=0,
            size=10,
            totalElementos=-5,
            totalPaginas=3,
        )


def test_pagina_viajes_rechaza_total_paginas_negativo():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[],
            page=0,
            size=10,
            totalElementos=25,
            totalPaginas=-1,
        )


def test_pagina_viajes_rechaza_item_invalido():
    with pytest.raises(ValidationError):
        PaginaViajes(
            items=[
                {
                    "viajeId": "123",
                    "estado": "COMPLETED",
                }
            ],
            page=0,
            size=10,
            totalElementos=1,
            totalPaginas=1,
        )
