# Creates (or reuses) a local self-signed code-signing certificate, trusts it
# on this machine, and signs dist\TorMeter.exe.
#
# NOTE: This only establishes trust on the machine that runs this script.
# Other users' PCs will still see "Unknown Publisher"/SmartScreen warnings —
# a CA-issued certificate is required for that.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts/sign_build.ps1

$ErrorActionPreference = 'Stop'

$subject = 'CN=TorMeter Self-Signed'
$exePath = Join-Path $PSScriptRoot '..\dist\TorMeter.exe'
if (-not (Test-Path $exePath)) {
    throw "$exePath not found. Run the Build Executable task first."
}
$exePath = (Resolve-Path $exePath).Path

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
Where-Object { $_.Subject -eq $subject } |
Select-Object -First 1

if (-not $cert) {
    Write-Host "Creating self-signed code-signing certificate..."
    $cert = New-SelfSignedCertificate `
        -Subject $subject `
        -Type CodeSigningCert `
        -CertStoreLocation Cert:\CurrentUser\My `
        -KeyUsage DigitalSignature `
        -FriendlyName 'TorMeter Self-Signed' `
        -NotAfter (Get-Date).AddYears(5)

    # Trust the cert locally so this machine treats the signature as valid.
    foreach ($storeName in 'Root', 'TrustedPublisher') {
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store($storeName, 'CurrentUser')
        $store.Open('ReadWrite')
        $store.Add($cert)
        $store.Close()
    }
}

$signtool = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
Where-Object { $_.FullName -match '\\x64\\' } |
Sort-Object FullName -Descending |
Select-Object -First 1 -ExpandProperty FullName

if (-not $signtool) {
    throw 'signtool.exe not found. Install the Windows SDK (Windows App Certification/Signing Tools component).'
}

& $signtool sign /sha1 $cert.Thumbprint /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $exePath
if ($LASTEXITCODE -ne 0) {
    throw "signtool failed with exit code $LASTEXITCODE"
}

Write-Host "Signed $exePath with thumbprint $($cert.Thumbprint)"
