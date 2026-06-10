#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageDir = Join-Path (Split-Path $ScriptDir -Parent) "packages\docx"

$OriginalPwd = Get-Location

if ($args.Count -eq 0) {
    Write-Host "Usage: docx-read.ps1 <docx_file> [output_dir]"
    Write-Host ""
    Write-Host "Arguments:"
    Write-Host "  docx_file   - Path to the .docx file"
    Write-Host "  output_dir  - Optional: Output directory (default: docs/extracted)"
    Write-Host ""
    Write-Host "Output:"
    Write-Host "  Markdown: <output_dir>/<filename>.md"
    Write-Host "  Assets:   <output_dir>/<filename>/ (images, attachments)"
    exit 1
}

$DocxFile = $args[0]
$OutputDir = if ($args.Count -gt 1) { $args[1] } else { "" }

if (-not [System.IO.Path]::IsPathRooted($DocxFile)) {
    $DocxFile = Join-Path $OriginalPwd $DocxFile
}

if ($OutputDir -and -not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $OriginalPwd $OutputDir
}

if (-not $OutputDir) {
    $OutputDir = Join-Path $OriginalPwd "docs\extracted"
}

Push-Location $PackageDir

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "Error: uv is not installed. Please install uv first:"
    Write-Error "  irm https://astral.sh/uv/install.ps1 | iex"
    Pop-Location
    exit 1
}

uv sync --quiet
if ($OutputDir) {
    uv run python main.py $DocxFile $OutputDir
} else {
    uv run python main.py $DocxFile
}

Pop-Location
