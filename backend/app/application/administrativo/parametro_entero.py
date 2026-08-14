import re


def parse_parametro_entero(valor_raw: object) -> int:
    """Semántica ENTERO compartida por la query #411 y el command #412."""
    if not isinstance(valor_raw, str) or re.fullmatch(r"-?[0-9]+", valor_raw) is None:
        raise ValueError("valor ENTERO persistido inválido")
    return int(valor_raw)
