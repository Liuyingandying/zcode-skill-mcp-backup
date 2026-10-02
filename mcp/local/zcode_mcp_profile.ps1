# zcode_mcp_profile.ps1 — ZCode MCP 按需加载切换器（最小复杂度实现）
# 机制：仅翻转 C:\Users\FAJ\.zcode\cli\config.json 中 mcp.servers.<name>.enabled
# 每次写入前自动备份到 .zcode_backup_profile_switch/，天然可回滚。
# 用法：
#   .\zcode_mcp_profile.ps1 list                      # 查看当前状态
#   .\zcode_mcp_profile.ps1 pinepaper on              # 临时开启单个 server
#   .\zcode_mcp_profile.ps1 pinepaper off             # 关闭
#   .\zcode_mcp_profile.ps1 profile documents         # 应用预设 profile
# 重启 ZCode 会话后生效（桌面端：新开会话即可）。
param(
  [Parameter(Position = 0)] [string] $Action,
  [Parameter(Position = 1)] [string] $Name
)
$ErrorActionPreference = "Stop"
$Cfg = "$env:USERPROFILE\.zcode\cli\config.json"
$BakDir = "$env:USERPROFILE\.zcode_backup_profile_switch"

# Profile 预设：core = 全量最小集；其余 = core + 专业组
$Profiles = @{
  core       = @{ on = @("zread","memory","context7","pandoc","research-knowledge","academic-office"); off = @("pinepaper","teach-mcp","ppt-server","word-document-server") }
  documents  = @{ on = @("zread","memory","context7","pandoc","research-knowledge","academic-office","word-document-server","ppt-server"); off = @("pinepaper","teach-mcp") }
  media      = @{ on = @("zread","memory","context7","pandoc","research-knowledge","academic-office","pinepaper"); off = @("teach-mcp","ppt-server","word-document-server") }
  learning   = @{ on = @("zread","memory","context7","pandoc","research-knowledge","academic-office","teach-mcp"); off = @("pinepaper","ppt-server","word-document-server") }
  everything = @{ on = @("zread","memory","context7","pandoc","research-knowledge","academic-office","pinepaper","teach-mcp","ppt-server","word-document-server"); off = @() }
}

function Save-WithBackup($json) {
  New-Item -ItemType Directory -Force -Path $BakDir | Out-Null
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  Copy-Item $Cfg "$BakDir\config.json.$stamp.bak"
  $json | ConvertTo-Json -Depth 20 | Set-Content -Path $Cfg -Encoding UTF8
  Write-Host "  (backup: config.json.$stamp.bak)"
}

if ($Action -eq "list" -or -not $Action) {
  $c = Get-Content $Cfg -Raw | ConvertFrom-Json
  foreach ($p in $c.mcp.servers.PSObject.Properties) {
    $enabled = if ($null -ne $p.Value.enabled) { $p.Value.enabled } else { $true }
    $state = if ($enabled) { "ON " } else { "off" }
    Write-Host ("  [{0}] {1}" -f $state, $p.Name)
  }
  Write-Host "`nprofiles: $($Profiles.Keys -join ', ')"
  exit 0
}

if ($Action -eq "profile") {
  if (-not $Profiles.ContainsKey($Name)) { Write-Error "unknown profile '$Name'"; exit 1 }
  $c = Get-Content $Cfg -Raw | ConvertFrom-Json
  foreach ($s in $Profiles[$Name].on)  { $c.mcp.servers.$s.enabled = $true }
  foreach ($s in $Profiles[$Name].off) { $c.mcp.servers.$s.enabled = $false }
  Save-WithBackup $c
  Write-Host "profile '$Name' applied. Restart session to take effect."
  exit 0
}

# 默认: <server> on|off
if ($Action -notin @("on", "off")) { Write-Error "usage: list | <server> on|off | profile <name>"; exit 1 }
$c = Get-Content $Cfg -Raw | ConvertFrom-Json
if (-not $c.mcp.servers.PSObject.Properties[$Name]) { Write-Error "server '$Name' not found"; exit 1 }
$c.mcp.servers.$Name.enabled = ($Action -eq "on")
Save-WithBackup $c
Write-Host "server '$Name' -> $Action. Restart session to take effect."
