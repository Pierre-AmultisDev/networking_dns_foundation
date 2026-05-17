Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces" | 
    ForEach-Object { 
        $val = Get-ItemProperty $_.PSPath
        if ($val.NameServer -or $val.DhcpNameServer) {
            Write-Host $_.PSPath
            Write-Host "  NameServer     : $($val.NameServer)"
            Write-Host "  DhcpNameServer : $($val.DhcpNameServer)"
        }
    }
