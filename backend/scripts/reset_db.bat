@echo off
setlocal

set PGUSER=postgres
set PGPASSWORD=gc001
set PGBIN="C:\Program Files\PostgreSQL\18\bin"

rem Ruta base
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set BACKEND_DIR=%%~fI

set DEV_DB=inmobiliaria_dev
set TEST_DB=inmobiliaria_test

set SCHEMA_FILE=%BACKEND_DIR%\database\schema_inmobiliaria_20260418.sql
set SEED_FILE=%BACKEND_DIR%\database\seed_minimo.sql
set TECHNICAL_BASELINE_FILE=%BACKEND_DIR%\database\seed_test_baseline.sql
set PATCH_PLAN_PAGO_VENTA_CRONOGRAMA_V2_FILE=%BACKEND_DIR%\database\patch_plan_pago_venta_cronograma_v2_20260514.sql
set PATCH_PLAN_PAGO_VENTA_BLOQUES_V2_FILE=%BACKEND_DIR%\database\patch_plan_pago_venta_bloques_v2_20260515.sql
set PATCH_PLAN_PAGO_VENTA_METODO_PLAN_POR_BLOQUES_V2_FILE=%BACKEND_DIR%\database\patch_plan_pago_venta_metodo_plan_por_bloques_v2_20260515.sql
set PATCH_PLAN_PAGO_VENTA_BLOQUE_METODO_LIQUIDACION_FILE=%BACKEND_DIR%\database\patch_plan_pago_venta_bloque_metodo_liquidacion_20260527.sql
set PATCH_INDICES_FINANCIEROS_FILE=%BACKEND_DIR%\database\patch_indices_financieros_20260527.sql
set PATCH_PLAN_PAGO_VENTA_BLOQUE_INDEXACION_FILE=%BACKEND_DIR%\database\patch_plan_pago_venta_bloque_indexacion_20260528.sql
set PATCH_CORRIDAS_INDEXACION_CUOTAS_V2_FILE=%BACKEND_DIR%\database\patch_corridas_indexacion_cuotas_v2_20260710.sql
set PATCH_PREPARAR_CORRIDAS_INDEXACION_CUOTAS_V2_FILE=%BACKEND_DIR%\database\patch_preparar_corridas_indexacion_cuotas_v2_20260714.sql
set PATCH_RELACION_PERSONA_ROL_PORCENTAJE_FILE=%BACKEND_DIR%\database\patch_relacion_persona_rol_porcentaje_responsabilidad_20260601.sql
set PATCH_CATALOGOS_CORE_EF_FILE=%BACKEND_DIR%\database\patch_catalogos_core_ef_20260716.sql
set SEED_INDICES_FINANCIEROS_DEMO_FILE=%BACKEND_DIR%\database\seed_indices_financieros_demo.sql

echo ============================
echo Reset DB - Sistema Inmobiliario
echo ============================

echo.
echo Backend dir: %BACKEND_DIR%
echo Schema: %SCHEMA_FILE%
echo Seed: %SEED_FILE%
echo Technical baseline: %TECHNICAL_BASELINE_FILE%
echo Patch plan pago venta cronograma V2: %PATCH_PLAN_PAGO_VENTA_CRONOGRAMA_V2_FILE%
echo Patch plan pago venta bloques V2: %PATCH_PLAN_PAGO_VENTA_BLOQUES_V2_FILE%
echo Patch plan pago venta metodo PLAN_POR_BLOQUES V2: %PATCH_PLAN_PAGO_VENTA_METODO_PLAN_POR_BLOQUES_V2_FILE%
echo Patch plan pago venta bloque metodo liquidacion: %PATCH_PLAN_PAGO_VENTA_BLOQUE_METODO_LIQUIDACION_FILE%
echo Patch indices financieros: %PATCH_INDICES_FINANCIEROS_FILE%
echo Patch plan pago venta bloque indexacion: %PATCH_PLAN_PAGO_VENTA_BLOQUE_INDEXACION_FILE%
echo Patch corridas indexacion cuotas V2: %PATCH_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%
echo Patch preparar corridas indexacion cuotas V2: %PATCH_PREPARAR_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%
echo Patch CORE-EF catalogos administrativos: %PATCH_CATALOGOS_CORE_EF_FILE%
echo Seed indices financieros demo: %SEED_INDICES_FINANCIEROS_DEMO_FILE%

if not exist "%SCHEMA_FILE%" (
  echo ERROR: No existe el schema: %SCHEMA_FILE%
  pause
  exit /b 1
)

if not exist "%SEED_FILE%" (
  echo ERROR: No existe el seed: %SEED_FILE%
  pause
  exit /b 1
)

if not exist "%TECHNICAL_BASELINE_FILE%" (
  echo ERROR: No existe el baseline tecnico: %TECHNICAL_BASELINE_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_PLAN_PAGO_VENTA_CRONOGRAMA_V2_FILE%" (
  echo ERROR: No existe el patch de cronograma V2: %PATCH_PLAN_PAGO_VENTA_CRONOGRAMA_V2_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_PLAN_PAGO_VENTA_BLOQUES_V2_FILE%" (
  echo ERROR: No existe el patch de bloques V2: %PATCH_PLAN_PAGO_VENTA_BLOQUES_V2_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_PLAN_PAGO_VENTA_METODO_PLAN_POR_BLOQUES_V2_FILE%" (
  echo ERROR: No existe el patch de metodo PLAN_POR_BLOQUES V2: %PATCH_PLAN_PAGO_VENTA_METODO_PLAN_POR_BLOQUES_V2_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_PLAN_PAGO_VENTA_BLOQUE_METODO_LIQUIDACION_FILE%" (
  echo ERROR: No existe el patch de metodo_liquidacion por bloque: %PATCH_PLAN_PAGO_VENTA_BLOQUE_METODO_LIQUIDACION_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_INDICES_FINANCIEROS_FILE%" (
  echo ERROR: No existe el patch de indices financieros: %PATCH_INDICES_FINANCIEROS_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_PLAN_PAGO_VENTA_BLOQUE_INDEXACION_FILE%" (
  echo ERROR: No existe el patch de indexacion por bloque: %PATCH_PLAN_PAGO_VENTA_BLOQUE_INDEXACION_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%" (
  echo ERROR: No existe el patch de corridas indexacion cuotas V2: %PATCH_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%
  pause
  exit /b 1
)

if not exist "%SEED_INDICES_FINANCIEROS_DEMO_FILE%" (
  echo ERROR: No existe el seed demo de indices financieros: %SEED_INDICES_FINANCIEROS_DEMO_FILE%
  pause
  exit /b 1
)

if not exist "%PATCH_CATALOGOS_CORE_EF_FILE%" (
  echo ERROR: No existe el patch CORE-EF de catalogos: %PATCH_CATALOGOS_CORE_EF_FILE%
  pause
  exit /b 1
)

rem ============================
rem DEV
rem ============================

echo.
echo ============================
echo Reseteando %DEV_DB%
echo ============================

%PGBIN%\dropdb %DEV_DB%
%PGBIN%\createdb %DEV_DB%

echo.
echo Aplicando schema en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%SCHEMA_FILE%"
if errorlevel 1 (
  echo ERROR aplicando schema en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando baseline tecnico en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%TECHNICAL_BASELINE_FILE%"
if errorlevel 1 (
  echo ERROR aplicando baseline tecnico en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch plan pago venta cronograma V2 en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%PATCH_PLAN_PAGO_VENTA_CRONOGRAMA_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch plan pago venta cronograma V2 en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch plan pago venta bloques V2 en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%PATCH_PLAN_PAGO_VENTA_BLOQUES_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch plan pago venta bloques V2 en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch metodo PLAN_POR_BLOQUES V2 en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%PATCH_PLAN_PAGO_VENTA_METODO_PLAN_POR_BLOQUES_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch metodo PLAN_POR_BLOQUES V2 en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch metodo_liquidacion por bloque en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%PATCH_PLAN_PAGO_VENTA_BLOQUE_METODO_LIQUIDACION_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch metodo_liquidacion por bloque en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch indices financieros en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%PATCH_INDICES_FINANCIEROS_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch indices financieros en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch indexacion por bloque en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%PATCH_PLAN_PAGO_VENTA_BLOQUE_INDEXACION_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch indexacion por bloque en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch corridas indexacion cuotas V2 en %DEV_DB%...
%PGBIN%\psql -v ON_ERROR_STOP=1 -d %DEV_DB% -f "%PATCH_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch corridas indexacion cuotas V2 en %DEV_DB%
  pause
  exit /b 1
)

echo Aplicando patch preparar corridas indexacion cuotas V2 en %DEV_DB%...
%PGBIN%\psql -v ON_ERROR_STOP=1 -d %DEV_DB% -f "%PATCH_PREPARAR_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch preparar corridas indexacion cuotas V2 en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch porcentaje responsabilidad comprador en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%PATCH_RELACION_PERSONA_ROL_PORCENTAJE_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch porcentaje responsabilidad comprador en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch CORE-EF catalogos administrativos en %DEV_DB%...
%PGBIN%\psql -v ON_ERROR_STOP=1 -d %DEV_DB% -f "%PATCH_CATALOGOS_CORE_EF_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch CORE-EF catalogos administrativos en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando seed minimo en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%SEED_FILE%"
if errorlevel 1 (
  echo ERROR aplicando seed en %DEV_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando seed demo de indices financieros en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%SEED_INDICES_FINANCIEROS_DEMO_FILE%"
if errorlevel 1 (
  echo ERROR aplicando seed demo de indices financieros en %DEV_DB%
  pause
  exit /b 1
)

rem ============================
rem TEST
rem ============================

echo.
echo ============================
echo Reseteando %TEST_DB%
echo ============================

%PGBIN%\dropdb %TEST_DB%
%PGBIN%\createdb %TEST_DB%

echo.
echo Aplicando schema en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%SCHEMA_FILE%"
if errorlevel 1 (
  echo ERROR aplicando schema en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando baseline tecnico en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%TECHNICAL_BASELINE_FILE%"
if errorlevel 1 (
  echo ERROR aplicando baseline tecnico en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch plan pago venta cronograma V2 en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%PATCH_PLAN_PAGO_VENTA_CRONOGRAMA_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch plan pago venta cronograma V2 en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch plan pago venta bloques V2 en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%PATCH_PLAN_PAGO_VENTA_BLOQUES_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch plan pago venta bloques V2 en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch metodo PLAN_POR_BLOQUES V2 en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%PATCH_PLAN_PAGO_VENTA_METODO_PLAN_POR_BLOQUES_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch metodo PLAN_POR_BLOQUES V2 en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch metodo_liquidacion por bloque en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%PATCH_PLAN_PAGO_VENTA_BLOQUE_METODO_LIQUIDACION_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch metodo_liquidacion por bloque en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch indices financieros en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%PATCH_INDICES_FINANCIEROS_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch indices financieros en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch indexacion por bloque en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%PATCH_PLAN_PAGO_VENTA_BLOQUE_INDEXACION_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch indexacion por bloque en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch corridas indexacion cuotas V2 en %TEST_DB%...
%PGBIN%\psql -v ON_ERROR_STOP=1 -d %TEST_DB% -f "%PATCH_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch corridas indexacion cuotas V2 en %TEST_DB%
  pause
  exit /b 1
)

echo Aplicando patch preparar corridas indexacion cuotas V2 en %TEST_DB%...
%PGBIN%\psql -v ON_ERROR_STOP=1 -d %TEST_DB% -f "%PATCH_PREPARAR_CORRIDAS_INDEXACION_CUOTAS_V2_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch preparar corridas indexacion cuotas V2 en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch porcentaje responsabilidad comprador en %TEST_DB%...
%PGBIN%\psql -d %TEST_DB% -f "%PATCH_RELACION_PERSONA_ROL_PORCENTAJE_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch porcentaje responsabilidad comprador en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo Aplicando patch CORE-EF catalogos administrativos en %TEST_DB%...
%PGBIN%\psql -v ON_ERROR_STOP=1 -d %TEST_DB% -f "%PATCH_CATALOGOS_CORE_EF_FILE%"
if errorlevel 1 (
  echo ERROR aplicando patch CORE-EF catalogos administrativos en %TEST_DB%
  pause
  exit /b 1
)

echo.
echo NOTA: no se aplica seed de negocio en %TEST_DB%
echo Los tests deben crear sus propios datos de dominio.

echo.
echo ============================
echo Bases reseteadas correctamente
echo - %DEV_DB%  (baseline tecnico + seed + indices financieros demo)
echo - %TEST_DB% (solo baseline tecnico)
echo ============================

pause
