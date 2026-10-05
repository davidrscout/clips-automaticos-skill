# Instala la skill en Antigravity, Codex y (si existe) Claude Code. Uso (PowerShell, desde esta carpeta):
#   powershell -ExecutionPolicy Bypass -File instalar_skill.ps1
$origen = Join-Path $PSScriptRoot "skills\clips-automaticos"
$destinos = @("$HOME\.gemini\config\skills\clips-automaticos", "$HOME\.agents\skills\clips-automaticos")
if (Test-Path "$HOME\.claude") { $destinos += "$HOME\.claude\skills\clips-automaticos" }
foreach ($d in $destinos) {
    New-Item -ItemType Directory -Force (Split-Path $d) | Out-Null
    if (Test-Path $d) { Remove-Item -Recurse -Force $d }
    Copy-Item -Recurse $origen $d
    Write-Host "Skill instalada en $d"
}
Write-Host "Listo: Antigravity (reinicialo), Codex y Claude Code. Pidele al agente: 'monta los clips automaticos'."
