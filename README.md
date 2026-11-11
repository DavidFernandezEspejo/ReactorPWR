# ReactorPWR

Simulador academico de reactor PWR orientado a la asignatura de Diseno de Modelos de Simulacion.

El proyecto implementa los bloques principales descritos en el PDF de especificacion:
- motor de eventos discretos para la evolucion temporal,
- modelo de estado validado con Pydantic,
- dinamica estocastica de neutrones (fision / captura / fuga),
- SCRAM acoplado a la reactividad efectiva,
- balance termico simplificado y potencia electrica,
- panel 2D de supervision con `pygame-ce`,
- runner de los 4 experimentos del PDF.

## Ejecutar (Windows)

### Opcion A - Ejecutable

1. Genera el `.exe` (solo la primera vez o tras cambios):

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name ReactorPWR --paths . --hidden-import=pygame --collect-binaries pygame run_reactor.py
```

2. Lanza la GUI:

- Doble clic en `ReactorPWR.bat`, o
- Doble clic en `dist\ReactorPWR.exe`

Controles en la interfaz:
- **LIVE**: neutrones chocando en el nucleo + telemetria
- **E**: recorre los 4 experimentos del PDF en orden (objetivo, metodo y resultado)
- **N**: siguiente experimento
- **L**: volver a modo live
- **ESPACIO**: pausa
- **ESC**: salir

### Opcion B - Desde Python (desarrollo)

```powershell
cd C:\Users\Usuario\Desktop\ReactorPWR
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
python run_reactor.py
```

### Experimentos del PDF

```powershell
$env:PYTHONPATH = (Get-Location).Path
python src/scripts/run_experiments.py
```

Salida: `logs/experimentos/resultados_experimentos.json`

## Requisitos

- Python 3.12+ (probado con 3.13 en Windows)
- Dependencias en `requirements.txt`

## Instalacion rapida

```powershell
cd C:\Users\Usuario\Desktop\ReactorPWR
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para generar el ejecutable tambien:

```powershell
pip install pyinstaller
```

## Leer la especificacion PDF

- En Cursor: extension PDF Viewer + abrir `docs/Especificación Diseño de Modelos de Simulación.pdf`
- Resumen: `docs/spec_summary.md`
- Trazabilidad: `docs/traceability.md`

```powershell
python src/scripts/read_pdf_spec.py
```

## Validacion

Suite grande (~100 tests): unitarios + integracion + validacion Monte Carlo/SCRAM.

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q --cov=src --cov-report=term-missing --cov-fail-under=70
```

Solo validacion pesada:

```powershell
pytest tests/validation -v
```

CI (`.github/workflows/ci-physics.yml`) en cada `push` / `pull_request`:
1. Lint + mypy
2. Unit tests en Python 3.12 y 3.13
3. Integracion + validacion + cobertura >= 70% + experimentos PDF
4. Artefactos: `coverage.xml` y `logs/`

## Flujo Git

- `main`: estable
- `develop`: integracion
- `feature/<tema>`: trabajo puntual (ej. `feature/scram-feedback-fix`)
