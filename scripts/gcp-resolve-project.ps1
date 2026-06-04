# Resolves GCP project: -ProjectId param > gcp.project.local > gcloud config
param([string]$ProjectId = "")

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$localFile = Join-Path $Root "gcp.project.local"

if ($ProjectId) {
    return $ProjectId.Trim()
}
if (Test-Path $localFile) {
    $id = (Get-Content $localFile -Raw).Trim()
    if ($id) { return $id }
}
$cfg = gcloud config get-value project 2>$null
if ($cfg -and $cfg -ne "(unset)") {
    return $cfg.Trim()
}
return $null
