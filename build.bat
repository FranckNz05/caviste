@echo off
rem Construit l'application de bureau et son installeur Windows.
rem Résultat : dist\Caviste-Installation-1.0.0.exe
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
)
.venv\Scripts\python -m pip install -q -r requirements.txt -r requirements-desktop.txt || goto :err
.venv\Scripts\python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\caviste.spec || goto :err

set ISCC=
for %%P in ("%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do if exist %%P set ISCC=%%P
if not defined ISCC (
  echo Inno Setup 6 introuvable : l'application est dans dist\Caviste, mais sans installeur.
  echo Installer Inno Setup : https://jrsoftware.org/isdl.php
  exit /b 1
)
%ISCC% /Q packaging\caviste.iss || goto :err
echo.
echo Installeur pret : dist\Caviste-Installation-1.0.0.exe
exit /b 0
:err
echo Echec de la construction.
exit /b 1
