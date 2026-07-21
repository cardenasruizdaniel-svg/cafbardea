param([switch]$SkipDependencyInstall)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location $taskRoot

if (!$SkipDependencyInstall) {
  if (!(Test-Path '.buildenv_cafbardla\Scripts\python.exe')) { py -3 -m venv .buildenv_cafbardla }
  & .\.buildenv_cafbardla\Scripts\python.exe -m pip install --upgrade pip
  if ($LASTEXITCODE -ne 0) { throw 'No fue posible actualizar pip.' }
  & .\.buildenv_cafbardla\Scripts\python.exe -m pip install -r requirements-build.txt
  if ($LASTEXITCODE -ne 0) { throw 'No fue posible instalar las dependencias de compilación.' }
}

& .\.buildenv_cafbardla\Scripts\pyinstaller.exe --noconfirm --clean --onedir --name CafBarDLA --add-data 'app;app' launcher.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller no pudo crear el ejecutable.' }
if (Get-Command ISCC.exe -ErrorAction SilentlyContinue) {
  ISCC.exe installer\CafBarDLA.iss
  Write-Output 'Instalador creado en installer\Output'
} else {
  Write-Warning 'La aplicación está en dist\CafBarDLA. Instale Inno Setup y ejecute el script de nuevo para crear Setup.exe.'
}
