# Starts the local vanilla 1.20.1 agent sandbox server.
# Uses the Mojang-bundled Java 17 runtime so no separate JDK install is needed.
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

# Locate a Java 17 runtime: prefer PATH, fall back to the Mojang launcher runtime.
$java = (Get-Command java -ErrorAction SilentlyContinue).Source
if (-not $java) {
    $gamma = Get-ChildItem "$env:LOCALAPPDATA\Packages\Microsoft.4297127D64EC6_8wekyb3d8bbwe\LocalCache\Local\runtime\java-runtime-gamma" -Recurse -Filter "java.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    if ($gamma) { $java = $gamma }
}
if (-not $java) { throw "No Java found. Install Temurin 17 or run Minecraft once via Prism to provision the Mojang runtime." }

if (-not (Test-Path "$here\server.jar")) { throw "server.jar missing in $here. See README for the download step." }

Write-Host "Java:   $java"
Write-Host "Server: $here\server.jar (port 25565, offline-mode)"
& $java -Xms1G -Xmx2G -jar server.jar nogui
