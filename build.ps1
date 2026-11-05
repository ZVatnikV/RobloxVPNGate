$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Icon"
py -3 -m pip install Pillow --quiet
py -3 .\build_assets\make_icon.py

Write-Host "==> PyInstaller"
if (Test-Path .\dist\RobloxVPNGate) { Remove-Item -Recurse -Force .\dist\RobloxVPNGate }
if (Test-Path .\build\RobloxVPNGate) { Remove-Item -Recurse -Force .\build\RobloxVPNGate }
py -3 -m PyInstaller --noconfirm .\RobloxVPNGate.spec

$iscc = @(
  "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) { throw "Inno Setup ISCC.exe not found" }

Write-Host "==> Inno Setup ($iscc)"
New-Item -ItemType Directory -Force -Path .\dist\installer | Out-Null
& $iscc .\installer\RobloxVPNGate.iss

Write-Host "==> Done"
Get-ChildItem .\dist\installer | Format-Table Name, Length, LastWriteTime
