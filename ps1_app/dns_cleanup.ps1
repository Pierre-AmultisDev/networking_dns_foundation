Get-DnsClientServerAddress | Where-Object ServerAddresses -contains "192.168.88.1" | Format-Table InterfaceAlias, ServerAddresses

Get-DnsClientServerAddress | Where-Object ServerAddresses -contains "84.241.227.82" | Format-Table InterfaceAlias, ServerAddresses


# Volledige DNS-instellingen van die adapter
Get-DnsClientServerAddress -InterfaceAlias "Ethernet" | Format-List *

# En de algemene IP-configuratie
Get-NetIPConfiguration -InterfaceAlias "Ethernet"

ipconfig /flushdns
ipconfig /release
ipconfig /renew