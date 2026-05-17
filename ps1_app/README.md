# DNS Hulpscripts – PowerShell Collectie

> ⚠️ **WORK IN PROGRESS**
>
> Deze scriptcollectie is nog in ontwikkeling en **niet volledig stabiel**.
> Op dit moment werken **alleen** `run_dnslookup_ps1_.cmd` en het bijbehorende `dnslookup.ps1` correct en betrouwbaar.
> De overige scripts (`dns_cleanup.ps1`, `registerkey.ps1`, `reset_registerkey.ps1`) zijn nog experimenteel en kunnen onverwacht gedrag vertonen.

---

## Overzicht van bestanden

| Bestand | Status | Beschrijving |
|---|---|---|
| `run_dnslookup_ps1_.cmd` | ✅ Werkend | Startscript voor `dnslookup.ps1` |
| `dnslookup.ps1` | ✅ Werkend | DNS-records opzoeken voor een domein |
| `dns_cleanup.ps1` | 🚧 Work in Progress | DNS-instellingen inspecteren en netwerk resetten |
| `registerkey.ps1` | 🚧 Work in Progress | DNS-servers uitlezen uit het Windows register |
| `reset_registerkey.ps1` | 🚧 Work in Progress | DNS-serverwaarde resetten in het Windows register |

---

## ✅ `run_dnslookup_ps1_.cmd` + `dnslookup.ps1`

### Beschrijving

`run_dnslookup_ps1_.cmd` is een Windows-batchbestand dat `dnslookup.ps1` aanroept met omzeiling van de standaard PowerShell-uitvoeringsbeveiliging. Het batchbestand fungeert als een eenvoudige startknop zodat de gebruiker geen PowerShell handmatig hoeft te openen.

`dnslookup.ps1` zoekt alle gangbare DNS-recordtypes op voor een opgegeven domeinnaam via `Resolve-DnsName`.

### Ondersteunde DNS-recordtypes

- **A** – IPv4-adres
- **AAAA** – IPv6-adres
- **MX** – Mailserver-records
- **TXT** – Tekstrecords (o.a. SPF, DKIM, DMARC)
- **CNAME** – Canonieke naamverwijzing
- **NS** – Nameserver-records
- **SOA** – Start of Authority
- **SRV** – Servicerecords
- **PTR** – Reverse DNS
- **CAA** – Certificate Authority Authorization

### Gebruik

**Via het `.cmd`-bestand (aanbevolen):**

Dubbelklik op `run_dnslookup_ps1_.cmd`. Het script voert een DNS-lookup uit op `example.com` (dit domein kan aangepast worden in het `.cmd`-bestand).

**Direct via PowerShell:**

```powershell
.\dnslookup.ps1 domein.nl
```

**Vereisten:**
- Windows met PowerShell
- Beide bestanden (`run_dnslookup_ps1_.cmd` en `dnslookup.ps1`) moeten in dezelfde map staan

---

## 🚧 `dns_cleanup.ps1` *(Work in Progress)*

### Beschrijving

Dit script is bedoeld voor het inspecteren en opschonen van DNS-instellingen op een Windows-machine. Het bevat nog hardgecodeerde IP-adressen en interfacenamen die niet op elke omgeving van toepassing zijn.

### Wat het script doet

1. Zoekt netwerkadapters op die een specifiek DNS-serveradres gebruiken (`192.168.88.1` of `84.241.227.82`)
2. Toont de volledige DNS- en IP-configuratie van de `Ethernet`-adapter
3. Voert een DNS-cache flush, IP-release en IP-renew uit

### ⚠️ Let op

- De IP-adressen en de interfacenaam (`Ethernet`) zijn hardgecodeerd en moeten handmatig worden aangepast aan de lokale situatie
- Vereist administratorrechten voor `ipconfig`-commando's

---

## 🚧 `registerkey.ps1` *(Work in Progress)*

### Beschrijving

Dit script leest DNS-serveradressen rechtstreeks uit het Windows-register (registry) via het `HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces`-pad. Handig voor het opsporen van hardgecodeerde of DHCP-toegewezen DNS-servers per netwerkinterface.

### Wat het script doet

- Doorloopt alle netwerkinterfaces in de registry
- Toont voor elke interface de waarden van `NameServer` (statisch) en `DhcpNameServer` (via DHCP)

### ⚠️ Let op

- Vereist administratorrechten
- Leest alleen; schrijft niets naar het register

---

## 🚧 `reset_registerkey.ps1` *(Work in Progress)*

### Beschrijving

Dit script overschrijft de `DhcpNameServer`-waarde van een specifieke netwerkinterface in het Windows-register. Het is bedoeld om een foutief DNS-serveradres te herstellen.

### Wat het script doet

- Stelt de `DhcpNameServer`-waarde in op `192.168.2.254` voor een vaste (hardgecodeerde) interface-GUID

### ⚠️ Let op

- De interface-GUID (`{47241f98-0d63-4b0f-b0fa-690850cc93ac}`) en het DNS-adres (`192.168.2.254`) zijn hardgecodeerd en moeten worden aangepast aan de doelmachine
- Vereist administratorrechten
- Wijzigingen in de registry kunnen systeemgedrag beïnvloeden; gebruik met zorg

---

## Toekomstige verbeteringen (TODO)

- [ ] Parametriseren van hardgecodeerde IP-adressen en interface-namen in `dns_cleanup.ps1`
- [ ] Automatische interfaceselectie in `reset_registerkey.ps1` in plaats van een vaste GUID
- [ ] Foutafhandeling toevoegen aan `dns_cleanup.ps1` en de registry-scripts
- [ ] Gezamenlijk startscript (`.cmd`) voor alle scripts
- [ ] Ondersteuning voor meerdere interfaces in `reset_registerkey.ps1`

---

*Laatste update: mei 2026*
