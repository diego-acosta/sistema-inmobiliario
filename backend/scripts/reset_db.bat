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

echo ============================
echo Reset DB - Sistema Inmobiliario
echo ============================

echo.
echo Backend dir: %BACKEND_DIR%
echo Schema: %SCHEMA_FILE%
echo Seed: %SEED_FILE%
echo Technical baseline: %TECHNICAL_BASELINE_FILE%

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
echo Aplicando seed minimo en %DEV_DB%...
%PGBIN%\psql -d %DEV_DB% -f "%SEED_FILE%"
if errorlevel 1 (
  echo ERROR aplicando seed en %DEV_DB%
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
echo NOTA: no se aplica seed de negocio en %TEST_DB%
echo Los tests deben crear sus propios datos de dominio.

echo.
echo ============================
echo Bases reseteadas correctamente
echo - %DEV_DB%  (baseline tecnico + seed)
echo - %TEST_DB% (solo baseline tecnico)
echo ============================

pause
