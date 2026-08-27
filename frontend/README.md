# Frontend — Sistema Inmobiliario

El frontend del sistema está implementado actualmente como una aplicación de escritorio en **Flet** y consume la API HTTP del backend.

## Implementación actual

La aplicación principal se encuentra en:

```text
frontend/flet_app/
```

Tecnologías principales:

- Python 3.11+.
- Flet `0.25.x`.
- `httpx` para comunicación con el backend.
- `openpyxl` para funciones de importación desde Excel.

## Estructura

```text
frontend/
└── flet_app/
    ├── app/
    │   ├── api_client.py       # Cliente HTTP del backend
    │   ├── config.py           # Configuración local
    │   ├── components/         # Componentes reutilizables
    │   ├── importers/          # Utilidades de importación
    │   ├── pages/              # Pantallas funcionales
    │   ├── router.py           # Routing interno
    │   └── shell.py            # Shell y navegación principal
    ├── documentacion/
    ├── prototypes/
    ├── tests/
    ├── main.py                 # Punto de entrada
    └── requirements.txt
```

## Áreas visibles en la aplicación

La implementación contiene pantallas y flujos para distintos frentes, entre ellos:

- Home.
- Partes / Personas.
- Inmuebles.
- Contratos.
- Ventas.
- Finanzas.
- Importación de inmuebles desde Excel.

La existencia de una pantalla no implica necesariamente que todo el dominio esté completo. El estado funcional debe verificarse contra el backend y `PROJECT-STATUS.md`.

## Instalación

Desde la raíz del repositorio:

```powershell
cd frontend\flet_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuración del backend

La URL base se controla con la variable de entorno `API_BASE_URL`.

```powershell
$env:API_BASE_URL = "http://localhost:8000"
```

Si no se configura, la aplicación usa:

```text
http://localhost:8000
```

El backend debe estar iniciado antes de usar las funciones que consumen la API.

## Ejecución

```powershell
cd frontend\flet_app
python main.py
```

## Tests

Los tests del frontend están en:

```text
frontend/flet_app/tests/
```

Pueden ejecutarse desde `frontend/flet_app/` con:

```powershell
pytest
```

La presencia de tests no implica cobertura completa de todos los flujos visuales o integraciones.

## Relación con el backend

El frontend debe tratar al backend como fuente de reglas de negocio, persistencia, autorización y consistencia. La UI no debe redefinir ownership de dominios ni asumir capacidades no expuestas por la API real.

Para configuración y ejecución del servidor consultar [../backend/README.md](../backend/README.md).

## Documentación específica de Flet

Para detalles propios de la aplicación desktop consultar [flet_app/README.md](flet_app/README.md).
