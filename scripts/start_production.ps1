param(
    [string]$ListenAddress = "127.0.0.1",
    [int]$Port = 8800
)

$ErrorActionPreference = "Stop"

# Localiza a raiz do projeto de forma relativa a este script
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WaitressExe = Join-Path $ProjectRoot ".venv\Scripts\waitress-serve.exe"

if (-not (Test-Path $WaitressExe)) {
    Write-Error "Waitress nao encontrado em: $WaitressExe. Instale as dependencias executando: pip install -r requirements.txt"
    exit 1
}

Set-Location $ProjectRoot

$ListenParam = "${ListenAddress}:${Port}"

Write-Host "=================================================="
Write-Host "Iniciando SST Freedom em http://$ListenParam"
Write-Host "WSGI Application: config.wsgi:application"
Write-Host "=================================================="

& $WaitressExe `
    --listen=$ListenParam `
    config.wsgi:application
