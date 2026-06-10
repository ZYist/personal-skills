#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageDir = Join-Path (Split-Path $ScriptDir -Parent) "packages\docx"
$OriginalPwd = Get-Location

if ($args.Count -eq 0) {
    Write-Host "Usage: docx-write.ps1 <input.md> [output.docx] [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  --style-config <file>   Path to JSON style config"
    Write-Host "  --body-font <font>      Override body font"
    Write-Host "  --body-size <pt>        Override body size"
    Write-Host "  --h1-size <pt>          Override Heading 1 size"
    Write-Host "  --image-max-width <in>  Override image max width"
    exit 1
}

$InputMd = $args[0]
if (-not [System.IO.Path]::IsPathRooted($InputMd)) {
    $InputMd = Join-Path $OriginalPwd $InputMd
}

$remaining = if ($args.Count -gt 1) { $args[1..($args.Count - 1)] } else { @() }
$OutputDocx = ""
if ($remaining.Count -gt 0 -and -not $remaining[0].StartsWith("--")) {
    $OutputDocx = $remaining[0]
    if (-not [System.IO.Path]::IsPathRooted($OutputDocx)) {
        $OutputDocx = Join-Path $OriginalPwd $OutputDocx
    }
    $remaining = if ($remaining.Count -gt 1) { $remaining[1..($remaining.Count - 1)] } else { @() }
}

$extraArgs = @()
for ($i = 0; $i -lt $remaining.Count; $i++) {
    $arg = $remaining[$i]
    if ($arg -eq "--style-config") {
        if ($i + 1 -ge $remaining.Count) {
            Write-Error "Error: --style-config requires a file path"
            exit 1
        }
        $extraArgs += $arg
        $stylePath = $remaining[$i + 1]
        if (-not [System.IO.Path]::IsPathRooted($stylePath)) {
            $stylePath = Join-Path $OriginalPwd $stylePath
        }
        $extraArgs += $stylePath
        $i++
        continue
    }
    $extraArgs += $arg
}

Push-Location $PackageDir

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "Error: uv is not installed. Please install uv first:"
    Write-Error "  irm https://astral.sh/uv/install.ps1 | iex"
    Pop-Location
    exit 1
}

uv sync --quiet
if ($OutputDocx) {
    uv run python main.py write $InputMd $OutputDocx @extraArgs
} else {
    uv run python main.py write $InputMd @extraArgs
}

Pop-Location
