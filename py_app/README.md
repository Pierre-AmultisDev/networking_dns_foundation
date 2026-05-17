# DNS Lookup Tools

Twee Python-scripts voor het opvragen van DNS-records en het enumereren van subdomains.

## Vereisten

Python 3.10 of hoger en de volgende packages:

```bash
pip install dnspython requests
```

---

## dns_lookup.py

Haalt alle DNS-records op voor een domein en probeert via drie methoden subdomains te ontdekken:

1. **Zone Transfer (AXFR)** — vraagt de nameserver om alle records in één keer. Zelden toegestaan, maar zeer volledig als het lukt.
2. **Certificate Transparency (crt.sh)** — raadpleegt publieke SSL-certificaatlogboeken. Elk certificaat dat ooit is aangevraagd voor een subdomein is hier terug te vinden.
3. **Brute-force** — controleert een lijst van veelgebruikte subdomainnamen via DNS-lookup.

### Gebruik

```bash
python dns_lookup.py <domein> [opties]
```

### Voorbeelden

```bash
# Basis lookup met alle methoden
python dns_lookup.py example.com

# Alleen DNS-records, geen subdomain scan
python dns_lookup.py example.com --no-ct --no-brute

# Zonder brute-force (sneller)
python dns_lookup.py example.com --no-brute

# Eigen wordlist combineren met de ingebouwde lijst
python dns_lookup.py example.com --wordlist mijn_lijst.txt

# Alleen de eigen wordlist gebruiken (ingebouwde lijst overgeslagen)
python dns_lookup.py example.com --only-wordlist mijn_lijst.txt

# Resultaten opslaan als JSON
python dns_lookup.py example.com --json resultaten.json

# Problemen oplossen
python dns_lookup.py example.com --debug
```

### Argumenten

| Argument | Beschrijving |
|---|---|
| `domein` | Het te onderzoeken domein, bijv. `example.com` |
| `--no-ct` | Sla de Certificate Transparency lookup (crt.sh) over |
| `--no-brute` | Sla de brute-force subdomain scan over |
| `--wordlist FILE` | Voeg een eigen wordlist toe; wordt gecombineerd met de ingebouwde lijst. Duplicaten worden automatisch verwijderd. Kan niet samen met `--only-wordlist` gebruikt worden. |
| `--only-wordlist FILE` | Gebruik uitsluitend de opgegeven wordlist; ingebouwde lijst wordt overgeslagen. Kan niet samen met `--wordlist` gebruikt worden. |
| `--json FILE` | Sla alle resultaten op als JSON-bestand |
| `--no-sublist` | Toon geen overzichtslijst van gevonden subdomains aan het einde |
| `--no-public-dns` | Gebruik de systeemresolver in plaats van publieke DNS (8.8.8.8 / 1.1.1.1) |
| `--timeout SEC` | Timeout per DNS-query in seconden (standaard: 8) |
| `--debug` | Toon alle DNS-fouten inclusief onverwachte exceptions |

### Opgehaalde recordtypes

Voor zowel het hoofddomein als elk gevonden subdomein worden de volgende recordtypes opgevraagd:

| Type | Beschrijving |
|---|---|
| `A` | IPv4-adres |
| `AAAA` | IPv6-adres |
| `MX` | Mailserver(s) |
| `NS` | Nameserver(s) |
| `TXT` | Tekstvelden (SPF, DKIM, verificaties, etc.) |
| `CNAME` | Alias naar een ander domein |
| `SOA` | Start of Authority — beheersinfo van de DNS-zone |
| `CAA` | Certificate Authority Authorization |
| `SRV` | Servicerecords (bijv. SIP, XMPP) |
| `PTR` | Reverse DNS |
| `DMARC` | E-mailbeveiligingsbeleid (via `_dmarc.<domein>`) |
| `DKIM` | E-mailhandtekening (via veelgebruikte selectors op `<selector>._domainkey.<domein>`) |

### Wordlist

De ingebouwde lijst bevat ~80 veelgebruikte subdomainnamen zoals `www`, `mail`, `api`, `dev`, `staging`, `admin`, etc.

Een eigen wordlist is een tekstbestand met één subdomainnaam per regel:

```
webshop
crm
erp
intranet
mijn-app
```

Het script zoekt het bestand eerst in de map waar `dns_lookup.py` staat, daarna in de map van waaruit je de terminal hebt gestart.

### Overzichtslijst subdomains

Aan het einde van elke run wordt een overzicht getoond van alle gevonden subdomains:

```
════════════════════════════════════════════════════════════
  Gevonden Subdomains — Overzicht
════════════════════════════════════════════════════════════
  ✅  mail.example.com
  ✅  www.example.com
  ⚪  legacy.example.com
```

- **✅** Subdomein gevonden én DNS-records opgehaald
- **⚪** Subdomein gevonden via CT-logs maar geen actieve DNS-records

Gebruik `--no-sublist` om deze lijst te verbergen.

---

## dns_diagnose.py

Diagnosescript om te controleren of DNS-lookups correct werken op jouw machine. Handig als `dns_lookup.py` geen resultaten teruggeeft of onverwachte fouten geeft.

### Gebruik

```bash
python dns_diagnose.py
```

Geen argumenten nodig. Het script test altijd `wee-play.nl` als testdomein.

### Output en interpretatie

Het script doorloopt vijf onderdelen:

#### 1. Versie-informatie

```
Python versie : 3.13.7 ...
dnspython     : 2.8.0
```

Controleer of `dnspython` correct geïnstalleerd is. Als dit ontbreekt, installeer het met `pip install dnspython`.

#### 2. Systeemresolver

```
Systemresolver: ['192.168.2.254']
```

Dit zijn de DNS-servers die jouw systeem gebruikt. Meerdere adressen zijn normaal. Let op **onbereikbare of verouderde adressen**, zoals het IP van een router die niet meer in gebruik is. Die veroorzaken timeouts omdat Windows altijd de eerste server probeert voor hij naar de volgende overschakelt.

#### 3. Socket test

```
  8.8.8.8:53  ✅ bereikbaar
  1.1.1.1:53  ✅ bereikbaar
```

Controleert of UDP-poort 53 (DNS) bereikbaar is naar publieke servers. Een ❌ hier betekent dat een firewall of router DNS-verkeer blokkeert, waardoor `dns_lookup.py` niet kan werken — ook niet met `--no-public-dns`.

#### 4. Exception klassen

```
  dns.resolver.NoAnswer             ✅
  dns.resolver.NXDOMAIN             ✅
  dns.resolver.LifetimeTimeout      ✅
  ...
```

Controleert welke foutklassen beschikbaar zijn in de geïnstalleerde versie van dnspython. Alle items zouden ✅ moeten tonen. Een ❌ wijst op een verouderde of beschadigde installatie van dnspython.

#### 5. DNS queries

```
  A        ✅  217.160.0.85
  AAAA     ✅  2001:8d8:100f:f000::200
  MX       ✅  10 weeplay-nl0i.mail.protection.outlook.com.
  CNAME    ❌  dns.resolver.NoAnswer: ...
  CAA      ❌  dns.resolver.NoAnswer: ...
```

Hier zie je per recordtype of de lookup slaagt. Let op het verschil:

| Uitkomst | Betekenis |
|---|---|
| ✅ met waarde | Record bestaat en is opgehaald |
| ❌ `NoAnswer` | Record bestaat niet voor dit domein — geen probleem |
| ❌ `LifetimeTimeout` | DNS-server reageert niet — controleer de systeemresolver |
| ❌ `NoNameservers` | Geen nameserver bereikbaar — netwerk- of firewallprobleem |
| ❌ `NXDOMAIN` | Domein bestaat niet (onverwacht voor een testdomein) |

`NoAnswer` voor `CNAME` en `CAA` is normaal — niet elk domein heeft deze records geconfigureerd. Timeouts zijn het enige echte probleem en wijzen altijd op een onbereikbare DNS-server in de systeemresolver.

### Veelvoorkomend probleem: verouderd DNS-adres in Windows

Als je timeouts ziet terwijl je internet gewoon werkt, heeft Windows waarschijnlijk een oud DNS-adres opgeslagen van een router of apparaat dat niet meer in gebruik is. Controleer dit met:

```powershell
Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces" |
    ForEach-Object {
        $val = Get-ItemProperty $_.PSPath
        if ($val.NameServer -or $val.DhcpNameServer) {
            Write-Host $_.PSPath
            Write-Host "  NameServer     : $($val.NameServer)"
            Write-Host "  DhcpNameServer : $($val.DhcpNameServer)"
        }
    }
```

Vervang het foute adres in de betreffende registersleutel door het juiste DNS-adres van je router, gevolgd door `ipconfig /flushdns`.
