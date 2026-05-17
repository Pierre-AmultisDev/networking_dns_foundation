param(
    [string]$Domain
)

if (-not $Domain) {
    Write-Host "Gebruik: .\dnslookup.ps1 domein.nl"
    exit
}

$recordTypes = @(
    "A",
    "AAAA",
    "MX",
    "TXT",
    "CNAME",
    "NS",
    "SOA",
    "SRV",
    "PTR",
    "CAA"
)

Write-Host "DNS records voor $Domain"
Write-Host "===================================="

foreach ($type in $recordTypes) {

    Write-Host ""
    Write-Host "=== $type records ==="

    try {
        Resolve-DnsName -Name $Domain -Type $type -ErrorAction Stop
    }
    catch {
        Write-Host "Geen records gevonden."
    }
}
