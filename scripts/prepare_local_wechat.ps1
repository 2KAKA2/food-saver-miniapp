param(
    [Parameter(Mandatory = $true)]
    [string]$LanIp,

    [string]$OperatorName = "食尽其用开发者",

    [switch]$Force
)

$parsedIp = $null
if (-not [System.Net.IPAddress]::TryParse($LanIp, [ref]$parsedIp) -or $parsedIp.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw "LanIp 必须是有效的 IPv4 地址。"
}

$octets = $parsedIp.GetAddressBytes()
$isPrivate = $octets[0] -eq 10 -or `
    ($octets[0] -eq 172 -and $octets[1] -ge 16 -and $octets[1] -le 31) -or `
    ($octets[0] -eq 192 -and $octets[1] -eq 168)
if (-not $isPrivate) {
    throw "LanIp 必须是 10.x、172.16-31.x 或 192.168.x 的局域网地址。"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $projectRoot "miniapp\src\manifest.json"
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ($manifest.'mp-weixin'.appid -ne "wx30ddd1061d78b551") {
    throw "manifest.json 中的 AppID 与已确认的 AppID 不一致。"
}

$envPath = Join-Path $projectRoot "miniapp\.env.local"
if ((Test-Path -LiteralPath $envPath) -and -not $Force) {
    throw "miniapp/.env.local 已存在。请先确认内容；确需覆盖时增加 -Force。"
}
$content = @(
    "VITE_API_BASE_URL=http://${LanIp}:8000/api/v1"
    "VITE_AUTH_MODE=wechat"
    "VITE_LEGAL_VERSION=2026-08-17"
    "VITE_OPERATOR_NAME=$OperatorName"
    "VITE_AI_PROVIDER_NAME=北京智谱华章科技有限公司（智谱AI）"
)
Set-Content -LiteralPath $envPath -Value $content -Encoding utf8

Write-Host "已生成 miniapp/.env.local：$LanIp"
Write-Host "请在 api/.env 私下填写 WECHAT_APP_SECRET，并确认以下值："
Write-Host "WECHAT_APP_ID=wx30ddd1061d78b551"
Write-Host "ALLOWED_HOSTS=127.0.0.1,localhost,$LanIp"
Write-Host "然后启动后端并重新执行 npm run build:mp-weixin。"
