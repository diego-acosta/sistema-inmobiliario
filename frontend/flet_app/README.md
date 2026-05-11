# Sistema Inmobiliario - App Desktop Flet V1

Base desktop Flet para consulta operativa V1.

## Requisitos

- Python 3.11+
- Backend corriendo, por defecto en `http://localhost:8000`

## Instalacion

```powershell
cd frontend\flet_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuracion

La URL del backend se configura con `API_BASE_URL`.

```powershell
$env:API_BASE_URL = "http://localhost:8000"
```

Si no se define, la app usa `http://localhost:8000`.

## Ejecucion

```powershell
python main.py
```

## Endpoints usados en este primer bloque

- `GET /api/v1/personas`
- `GET /api/v1/personas/{id_persona}/detalle-integral`

La UI muestra el dominio tecnico `personas` como **Partes**.

## Alcance V1

- Shell desktop con navegacion lateral.
- Home.
- Listado de Partes.
- Ficha de parte.
- Placeholders para Inmuebles, Contratos, Ventas y Finanzas.

## Limitaciones conocidas

- Sin autenticacion.
- Sin permisos.
- Sin altas ni edicion.
- Sin pagos.
- Sin UI completa para inmuebles, contratos, ventas ni finanzas.
- Manejo de errores basico para conexion, 400/404/409/500.
