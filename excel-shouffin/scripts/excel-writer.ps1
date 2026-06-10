#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageDir = Join-Path (Split-Path $ScriptDir -Parent) "packages\excel"

$OriginalPwd = Get-Location

if ($args.Count -eq 0) {
    Write-Host "Usage: excel-writer.ps1 <input.json> [output.xlsx]"
    Write-Host ""
    Write-Host "Arguments:"
    Write-Host "  input.json   - JSON file describing Excel structure"
    Write-Host "  output.xlsx  - Optional: output Excel file path (default: <input_stem>.xlsx)"
    Write-Host ""
    Write-Host "JSON Format:"
    Write-Host '  {'
    Write-Host '    "sheets": ['
    Write-Host '      {'
    Write-Host '        "name": "Sheet1",'
    Write-Host '        "title": "Report Title",'
    Write-Host '        "headers": ["Col1", "Col2"],'
    Write-Host '        "data": [["val1", "val2"]],'
    Write-Host '        "column_widths": [15, 20],'
    Write-Host '        "merge_cells": ["A1:B2"]'
    Write-Host '      }'
    Write-Host '    ]'
    Write-Host '  }'
    Write-Host ""
    Write-Host "Fields:"
    Write-Host "  name           - Optional: sheet name (default: Sheet1)"
    Write-Host "  title          - Optional: title row text"
    Write-Host "  headers        - Optional: column headers"
    Write-Host "  data           - Required: 2D array of cell values"
    Write-Host "  column_widths  - Optional: array of column widths"
    Write-Host "  merge_cells    - Optional: array of merge ranges"
    exit 1
}

$InputFile = $args[0]
$OutputFile = if ($args.Count -gt 1) { $args[1] } else { "" }

if (-not [System.IO.Path]::IsPathRooted($InputFile)) {
    $InputFile = Join-Path $OriginalPwd $InputFile
}

if ($OutputFile -and -not [System.IO.Path]::IsPathRooted($OutputFile)) {
    $OutputFile = Join-Path $OriginalPwd $OutputFile
}

Push-Location $PackageDir

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "Error: uv is not installed. Please install uv first:"
    Write-Error "  irm https://astral.sh/uv/install.ps1 | iex"
    Pop-Location
    exit 1
}

uv sync --quiet

if ($OutputFile) {
    uv run python writer.py $InputFile $OutputFile
} else {
    uv run python writer.py $InputFile
}

Pop-Location
