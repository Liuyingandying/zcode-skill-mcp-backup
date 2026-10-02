# restore.ps1 - minimal single-component restore for the zcode-skill-mcp-backup archive
# Usage:
#   .\restore.ps1 list
#   .\restore.ps1 skill <name> [-Scope zcode|agents] [-Force]
#   .\restore.ps1 mcp <name>
# Never restores secrets. Never overwrites an existing component without -Force.
param(
  [Parameter(Position = 0)][string] $Action,
  [Parameter(Position = 1)][string] $Name,
  [string] $Scope = "zcode",         # -Scope agents for the Alvarmethod originals
  [switch] $Force
)
$ErrorActionPreference = "Stop"
$Repo = $PSScriptRoot
$Manifest = Get-Content (Join-Path $Repo "MANIFEST.json") -Raw | ConvertFrom-Json

function Get-Home { [Environment]::GetFolderPath("UserProfile") }

if (-not $Action -or $Action -eq "list") {
  Write-Host "== Archived skills (full source) ==" -ForegroundColor Cyan
  Get-ChildItem (Join-Path $Repo "skills\local") -Directory |
    Where-Object { $_.Name -ne "_commands" } |
    ForEach-Object { Write-Host ("  skill  {0}" -f $_.Name) }
  Write-Host "  skill  _commands   (slash-command .md set)"
  Write-Host "== MCP recipes ==" -ForegroundColor Cyan
  Get-ChildItem (Join-Path $Repo "mcp\install-recipes") -File |
    ForEach-Object { Write-Host ("  mcp    {0}" -f $_.BaseName) }
  Write-Host "`nUsage: .\restore.ps1 skill <name> | mcp <name>   (see RESTORE.md)"
  exit 0
}

if ($Action -eq "skill") {
  if (-not $Name) { Write-Error "skill name required"; exit 1 }
  $src = Join-Path $Repo "skills\local\$Name"
  if (-not (Test-Path $src)) { Write-Error "no archived skill '$Name'"; exit 1 }
  if ($Name -eq "_commands") {
    $dst = Join-Path (Get-Home) ".zcode\commands"
    if (Test-Path $dst) { Write-Host "target exists: $dst (files merge individually; use -Force to overwrite existing files)" }
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    Copy-Item (Join-Path $src "*.md") $dst -Force:$Force
    Write-Host "restored commands -> $dst"
    exit 0
  }
  $root = if ($Scope -eq "agents") { ".agents\skills" } else { ".zcode\skills" }
  $dst = Join-Path (Get-Home) "$root\$Name"
  if (Test-Path $dst) {
    if (-not $Force) { Write-Error "target already exists: $dst (use -Force to overwrite)"; exit 1 }
    Remove-Item $dst -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
  Copy-Item $src $dst -Recurse
  Write-Host "restored skill '$Name' -> $dst"
  Write-Host "restart your Z Code session to pick it up."
  exit 0
}

if ($Action -eq "mcp") {
  if (-not $Name) { Write-Error "mcp name required (run 'list')"; exit 1 }
  $recipe = Join-Path $Repo "mcp\install-recipes\$Name.md"
  if (-not (Test-Path $recipe)) { Write-Error "no recipe for '$Name'"; exit 1 }
  Write-Host "=== $recipe ==="
  Get-Content $recipe
  Write-Host "`nPaste the JSON under mcp.servers in: $(Get-Home)\.zcode\cli\config.json"
  Write-Host "Secrets are NOT included - provide tokens yourself (prefer env variables)."
  exit 0
}

Write-Error "unknown action '$Action' (use list / skill / mcp)"
