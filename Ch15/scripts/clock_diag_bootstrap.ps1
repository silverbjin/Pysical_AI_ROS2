param(
    [string]$Distro = 'Ubuntu-24.04',
    [ValidateRange(1,1200)][int]$Seconds = 620,
    [string]$NtpServer = 'time.windows.com',
    [string]$OutputRoot = (Join-Path $HOME 'ch15-clock-evidence'),
    [switch]$VerifyOnly
)
$ErrorActionPreference='Stop'
$pin='bd07d22da44e725e36ff2099b64f76f7b5e688c2'
$base="https://raw.githubusercontent.com/silverbjin/Pysical_AI_ROS2/$pin/Ch15"
$hashes=[ordered]@{
    'python/clock_diag.py'='c6ee266b655763f20a39fce748df75ab2433d0668e7ddd281ea524164a74fc89'
    'python/clock_drift_analyzer.py'='fb2715dadfbfb6f92dc46788a744c869e54a6467d0a785c464ff4c0654bca5ae'
    'python/clock_cross_layer_analyzer.py'='f8d98a0b2128b8e11f721ba489c7e56a7242c453a6fe551f0bb4c5aaa66e6723'
    'python/clock_timex_read.c'='681ae894cce1fdc6b7a44e12f810ede8a3ff4c5d1a1137bc70c3d3798554e776'
    'scripts/clock_diag_wsl2.sh'='284488e7742b5b0e009715d8f383ee9219982fa71fcf184f24199582d0a6f79c'
    'scripts/clock_diag_windows.ps1'='f202eddbf2149ac2e799b0769736459f4c888445f2d56cafbb1dc18a9fe6cbaf'
    'scripts/clock_diag_cross_layer.sh'='700abebfa883292b9c19584bea66ed9c7e19bf12d2a4d87a9a4db7243c250491'
}
$session=Join-Path $OutputRoot ([Guid]::NewGuid().ToString('N'))
$src=Join-Path $session 'verified-source'
New-Item -ItemType Directory -Path $src -Force | Out-Null
$verified=@()
foreach ($name in $hashes.Keys) {
    $path=Join-Path $src $name
    New-Item -ItemType Directory -Path (Split-Path $path -Parent) -Force | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri "$base/$name" -OutFile $path
    $actual=(Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $hashes[$name]) { throw "SOURCE_SHA256_MISMATCH $name" }
    $verified+=@{path=$name;sha256=$actual}
}
$receipt=Join-Path $session 'source-receipt.json'
@{source_pin=$pin;bootstrap_sha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant();verified_files=$verified;status='PASS'} | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $receipt
Write-Output "CH15_CLOCK_SOURCE_VERIFY_PASS $pin files=$($verified.Count) receipt=$receipt"
if ($VerifyOnly) { return }
$results=Join-Path $session 'results'
try {
    & (Join-Path $src 'scripts/clock_diag_windows.ps1') -Distro $Distro -Seconds $Seconds -NtpServer $NtpServer -OutputRoot $results -SourcePin $pin
} finally {
    Write-Output "SOURCE_RECEIPT=$receipt"
    Write-Output "RESULTS_DIRECTORY=$results"
    Write-Output 'Send evidence ZIP, ZIP SHA256, and source-receipt.json privately. No mission execution.'
}
