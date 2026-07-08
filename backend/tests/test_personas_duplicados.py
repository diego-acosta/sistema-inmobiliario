from __future__ import annotations

from app.application.personas.duplicados import (
    TipoDuplicadoPersona,
    detectar_duplicado_persona,
    normalizar_documento_fiscal,
    normalizar_documento_principal,
    normalizar_email,
    normalizar_persona_para_duplicados,
    normalizar_texto_basico,
)


def test_normaliza_cuit_cuil_con_guiones_puntos_y_espacios() -> None:
    assert normalizar_documento_fiscal(" 20-12.345.678 - 3 ") == "20123456783"


def test_normaliza_documento_principal_con_separadores_comunes() -> None:
    assert normalizar_documento_principal(" A 12.345-678 / 9 ") == "a123456789"


def test_normaliza_nombre_apellido_y_razon_social() -> None:
    assert normalizar_texto_basico("  Juan   Carlos ") == "juan carlos"
    persona = normalizar_persona_para_duplicados(
        nombre="  María   DEL  ",
        apellido="  Río  ",
        razon_social="  ACME    SA  ",
    )
    assert persona.nombre == "maría del"
    assert persona.apellido == "río"
    assert persona.razon_social == "acme sa"


def test_detecta_duplicado_fuerte_por_cuit_cuil() -> None:
    nueva = normalizar_persona_para_duplicados(cuit_cuil="20-12345678-3")
    existente = normalizar_persona_para_duplicados(cuit_cuil="20.123.456.78 3")

    duplicado = detectar_duplicado_persona(nueva, existente, id_persona=10)

    assert duplicado is not None
    assert duplicado.tipo == TipoDuplicadoPersona.FUERTE
    assert duplicado.criterio == "cuit_cuil"
    assert duplicado.id_persona == 10


def test_detecta_duplicado_fuerte_por_documento_principal() -> None:
    nueva = normalizar_persona_para_duplicados(tipo_documento="DNI", numero_documento="12.345.678")
    existente = normalizar_persona_para_duplicados(tipo_documento=" dni ", numero_documento="12-345-678")

    duplicado = detectar_duplicado_persona(nueva, existente)

    assert duplicado is not None
    assert duplicado.tipo == TipoDuplicadoPersona.FUERTE
    assert duplicado.criterio == "documento_principal"


def test_detecta_posible_duplicado_por_email() -> None:
    assert normalizar_email(" USER@Example.COM ") == "user@example.com"
    nueva = normalizar_persona_para_duplicados(email="USER@Example.COM")
    existente = normalizar_persona_para_duplicados(email=" user@example.com ")

    duplicado = detectar_duplicado_persona(nueva, existente)

    assert duplicado is not None
    assert duplicado.tipo == TipoDuplicadoPersona.POSIBLE
    assert duplicado.criterio == "email"


def test_detecta_posible_duplicado_por_nombre_apellido() -> None:
    nueva = normalizar_persona_para_duplicados(tipo_persona="FISICA", nombre="Ana  María", apellido="Pérez")
    existente = normalizar_persona_para_duplicados(tipo_persona="fisica", nombre=" ana maría ", apellido=" pÉrez ")

    duplicado = detectar_duplicado_persona(nueva, existente)

    assert duplicado is not None
    assert duplicado.tipo == TipoDuplicadoPersona.POSIBLE
    assert duplicado.criterio == "nombre_apellido"


def test_detecta_posible_duplicado_por_razon_social() -> None:
    nueva = normalizar_persona_para_duplicados(tipo_persona="JURIDICA", razon_social="Acme   SA")
    existente = normalizar_persona_para_duplicados(tipo_persona="juridica", razon_social=" acme sa ")

    duplicado = detectar_duplicado_persona(nueva, existente)

    assert duplicado is not None
    assert duplicado.tipo == TipoDuplicadoPersona.POSIBLE
    assert duplicado.criterio == "razon_social"
