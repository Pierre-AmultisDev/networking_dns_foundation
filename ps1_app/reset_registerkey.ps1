$key = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{47241f98-0d63-4b0f-b0fa-690850cc93ac}"
Set-ItemProperty -Path $key -Name "DhcpNameServer" -Value "192.168.2.254"
