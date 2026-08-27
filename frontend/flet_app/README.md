# Sistema Inmobiliario — App Desktop Flet

Aplicación desktop del Sistema Inmobiliario construida con **Flet**. Consume la API HTTP del backend y concentra la experiencia operativa de escritorio.

## Requisitos

- Python 3.11+.
- Backend del proyecto corriendo, por defecto en `http://localhost:8000`.

Dependencias principales:

- Flet `0.25.x`.
- `httpx`.
- `openpyxl` para funciones de importación desde Excel.

## Instalación

Desde la raíz del repositorio:

```powershell
cd frontend\flet_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuración

La URL del backend se configura con `API_BASE_URL`:

```powershell
$env:API_BASE_URL = "http://localhost:8000"
```

Si no se define, la app usa `http://localhost:8000`.

## Ejecución

```powershell
python main.py
```

## Estructura

```text
flet_app/
├── app/
│   ├── api_client.py
│   ├── config.py
│   ├── components/
│   ├── importers/
│   ├── pages/
│   ├── router.py
│   └── shell.py
├── documentacion/
├── prototypes/
├── tests/
├── main.py
└── requirements.txt
```

## Áreas implementadas o materializadas en la UI

La aplicación contiene actualmente componentes y páginas para:

- Home.
- Partes / Personas, incluyendo listado y ficha detallada.
- Inmuebles, incluyendo flujos de alta/edición y soporte de importación desde Excel.
- Contratos.
- Ventas, incluyendo wizards y pantallas auxiliares del plan de pago.
- Finanzas.

Algunas áreas están más desarrolladas que otras. La presencia de una ruta, página o placeholder no debe interpretarse como cierre funcional de todo el dominio.

## Integración con la API

`app/api_client.py` concentra el acceso HTTP al backend. La UI debe respetar los contratos expuestos por el backend y no duplicar reglas de negocio o ownership de dominio.

El backend define autenticación, autorización, persistencia, consistencia, versionado e infraestructura CORE-EF cuando corresponda.

Para conocer los endpoints vigentes debe usarse la implementación real y Swagger/OpenAPI del backend; no se mantiene en este README una lista exhaustiva que pueda quedar obsoleta.

## Tests

Desde `frontend/flet_app/`:

```powershell
pytest
```

Los tests están bajo `tests/`. No se afirma cobertura total de flujos visuales o integraciones solo por su existencia.

## Documentación relacionada

- [README del frontend](../README.md).
- [README del backend](../../backend/README.md).
- [README general](../../README.md).
- [Estado operativo del proyecto](../../PROJECT-STATUS.md).

## Estado

El frontend está en desarrollo activo y evoluciona junto con la API. Las capacidades disponibles deben verificarse contra código, backend y tests reales antes de considerarse completas.
