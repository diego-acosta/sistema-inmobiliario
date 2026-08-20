from pathlib import Path


RESET_BAT = Path(__file__).resolve().parents[1] / "scripts" / "reset_db.bat"


def test_reset_bat_fija_utf8_antes_de_invocar_psql() -> None:
    lines = RESET_BAT.read_text(encoding="utf-8").splitlines()
    encoding_index = next(
        index
        for index, line in enumerate(lines)
        if line.strip().casefold() == "set pgclientencoding=utf8"
    )
    psql_indexes = [
        index for index, line in enumerate(lines) if "%pgbin%\\psql" in line.casefold()
    ]

    assert psql_indexes
    assert lines.index("setlocal") < encoding_index < min(psql_indexes)
