# Crea en GitHub un issue por cada tarea de docs/tareas (opcional).
# El tablero (docs/tareas/README.md) ya es el registro; los issues sirven para asignar
# a cada persona y que GitHub le avise.
#
# Requisitos: GitHub CLI (https://cli.github.com) instalado y "gh auth login" hecho.
# Uso, desde la raíz del repo:   .\docs\tareas\crear-issues.ps1
# Se corre UNA sola vez: si se repite, crea los issues de nuevo.

$ErrorActionPreference = "Stop"
$repo = "FRRe-DS/2026-01-TPI"
$base = "https://github.com/$repo/blob/desarrollo-m2/docs/tareas"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "No está instalado GitHub CLI (gh). Instalalo desde https://cli.github.com o creá los issues a mano." -ForegroundColor Yellow
    exit 1
}

gh label create "tarea" --repo $repo --color "0f766e" --description "Tarea del tablero docs/tareas" --force | Out-Null

$archivos = Get-ChildItem -Path (Join-Path $PSScriptRoot "*.md") | Where-Object { $_.Name -ne "README.md" } | Sort-Object Name
foreach ($archivo in $archivos) {
    $titulo = (Get-Content $archivo.FullName -Encoding UTF8 -TotalCount 1) -replace '^#\s*', ''
    $cuerpo = @"
Guía completa: $base/$($archivo.Name)

Pasos para trabajarla:
1. Rama propia desde ``desarrollo-m2``.
2. Seguir la guía, con las pruebas.
3. PR hacia ``desarrollo-m2`` con el CI en verde.
4. Actualizar el tablero (``docs/tareas/README.md``) con el estado y el número de PR.
"@
    Write-Host "Creando: $titulo"
    gh issue create --repo $repo --title $titulo --body $cuerpo --label "tarea" | Out-Host
}

Write-Host "Listo. Asigná cada issue a su responsable desde GitHub (Assignees)." -ForegroundColor Green
