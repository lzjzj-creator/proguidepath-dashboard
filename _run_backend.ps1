$RootDir = $args[0]
$VenvDir = "$RootDir\backend\.venv"
$env:PYTHONPATH = "$RootDir\backend"
Set-Location "$RootDir\backend"
$Host.UI.RawUI.WindowTitle = "Resume Platform - Backend (8000)"
& "$VenvDir\Scripts\python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
