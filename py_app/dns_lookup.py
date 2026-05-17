#!/usr/bin/env python3
"""
# =============================================================================
#
# @package    networking 
# @container  dns_foundation
# @name       dns_lookup.py
# @version    v0.0.1  2026-05-17
# @author     pierre@amultis.dev
# @copyright  (C) Pierre Veelen
#
# @location  @my_code\_for_python\networking\dns_foundation\code\py_app
# 
# ============================================================================= 

DNS Lookup Tool - Haalt alle DNS records op voor een domein,
inclusief subdomain-enumeratie via brute-force wordlist en CT-logs.

"""

import dns.resolver
import dns.zone
import dns.query
import dns.exception
import dns.rdatatype
import requests
import argparse
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# ──────────────────────────────────────────────
# Configuratie
# ──────────────────────────────────────────────

# DKIM en DMARC zijn geen echte recordtypes maar TXT-records met een prefix;
# dnspython gooit UnknownRdatatype als je ze direct opvraagt. Die worden
# apart opgehaald via lookup_dkim_dmarc().
RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA", "SRV", "PTR"]

COMMON_SUBDOMAINS = [
    "www", "mail", "smtp", "pop", "pop3", "imap", "ftp", "sftp",
    "vpn", "remote", "ns1", "ns2", "dns", "dns1", "dns2",
    "api", "dev", "staging", "test", "acc", "acceptatie",
    "portal", "admin", "webmail", "autodiscover", "autoconfig",
    "shop", "store", "blog", "forum", "support", "help", "docs",
    "cloud", "cdn", "static", "assets", "media", "img",
    "app", "apps", "mobile", "m", "wap",
    "secure", "login", "auth", "sso", "oauth",
    "monitor", "status", "health", "metrics",
    "git", "gitlab", "github", "ci", "jenkins", "build",
    "db", "database", "mysql", "postgres", "redis", "mongo",
    "proxy", "gateway", "lb", "loadbalancer",
    "intranet", "internal", "extranet",
    "webdav", "exchange", "owa", "mx", "mx1", "mx2",
    "_dmarc", "_domainkey",
]

# ──────────────────────────────────────────────
# Silent exceptions (versie-onafhankelijk)
# ──────────────────────────────────────────────

def _build_silent_exceptions() -> tuple:
    """Bouw een tuple van exceptions die 'geen resultaat' betekenen."""
    excs = [
        dns.resolver.NoAnswer,
        dns.resolver.NXDOMAIN,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
        dns.rdatatype.UnknownRdatatype,  # bijv. bij DKIM/DMARC als type
    ]
    # LifetimeTimeout bestaat pas in nieuwere dnspython versies
    if hasattr(dns.resolver, "LifetimeTimeout"):
        excs.append(dns.resolver.LifetimeTimeout)
    return tuple(excs)

SILENT_EXCEPTIONS = _build_silent_exceptions()

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

# Publieke DNS-servers als fallback — omzeilt routers die dnspython blokkeren
PUBLIC_NAMESERVERS = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"]

def make_resolver(timeout: float = 8.0, use_public_dns: bool = True) -> dns.resolver.Resolver:
    r = dns.resolver.Resolver()
    if use_public_dns:
        r.nameservers = PUBLIC_NAMESERVERS
    r.timeout = timeout
    r.lifetime = timeout * 2
    return r


def query_record(domain: str, rtype: str, resolver: dns.resolver.Resolver, debug: bool = False) -> list[str]:
    """Vraag één recordtype op; geeft lege lijst bij geen resultaat."""
    try:
        answers = resolver.resolve(domain, rtype)
        results = []
        for rdata in answers:
            if rtype == "MX":
                results.append(f"{rdata.preference} {rdata.exchange}")
            elif rtype == "SOA":
                results.append(
                    f"mname={rdata.mname} rname={rdata.rname} "
                    f"serial={rdata.serial} refresh={rdata.refresh} "
                    f"retry={rdata.retry} expire={rdata.expire} ttl={rdata.minimum}"
                )
            else:
                results.append(str(rdata))
        return results
    except SILENT_EXCEPTIONS:
        return []
    except Exception as e:
        # Onverwachte fout: altijd tonen zodat het niet stil verdwijnt
        print(f"  {'[debug]' if debug else '⚠️ '} {rtype} {domain}: {type(e).__name__}: {e}")
        return []


def lookup_dkim_dmarc(domain: str, resolver: dns.resolver.Resolver, debug: bool = False) -> dict:
    """
    DKIM en DMARC zijn TXT-records op speciale subdomains:
      - DMARC : _dmarc.<domain>
      - DKIM  : <selector>._domainkey.<domain>  (selector is onbekend, we proberen veelgebruikte)
    """
    results = {}

    # DMARC
    dmarc = query_record(f"_dmarc.{domain}", "TXT", resolver, debug)
    if dmarc:
        results["DMARC"] = dmarc

    # DKIM — veelgebruikte selectors
    dkim_selectors = [
        "default", "google", "k1", "k2", "mail", "email",
        "selector1", "selector2", "s1", "s2", "dkim", "smtp",
        "mimecast", "mailjet", "sendgrid", "amazonses",
    ]
    found_dkim = {}
    for sel in dkim_selectors:
        records = query_record(f"{sel}._domainkey.{domain}", "TXT", resolver, debug)
        if records:
            found_dkim[sel] = records
    if found_dkim:
        results["DKIM"] = found_dkim

    return results


def try_zone_transfer(domain: str, resolver: dns.resolver.Resolver) -> list[str]:
    """Probeer een AXFR zone transfer; geeft subdomains terug als het lukt."""
    found = []
    try:
        ns_records = resolver.resolve(domain, "NS")
        for ns in ns_records:
            ns_host = str(ns).rstrip(".")
            try:
                z = dns.zone.from_xfr(dns.query.xfr(ns_host, domain, timeout=5))
                for name in z.nodes.keys():
                    name_str = str(name)
                    if name_str != "@":
                        found.append(f"{name_str}.{domain}")
                print(f"  ✅ Zone transfer gelukt via {ns_host}!")
                return found
            except Exception:
                pass
    except Exception:
        pass
    return found


def fetch_ct_subdomains(domain: str) -> list[str]:
    """Haal subdomains op via crt.sh (Certificate Transparency logs)."""
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    subdomains = set()
    try:
        resp = requests.get(url, timeout=15)
        if resp.ok:
            for entry in resp.json():
                name = entry.get("name_value", "")
                for sub in name.splitlines():
                    sub = sub.strip().lstrip("*.")
                    if sub.endswith(f".{domain}") or sub == domain:
                        subdomains.add(sub)
    except Exception:
        pass
    return sorted(subdomains)


def brute_force_subdomains(domain: str, wordlist: list[str], debug: bool = False) -> list[str]:
    """Brute-force subdomain check via DNS A/AAAA lookup (parallel)."""
    found = []
    resolver = make_resolver()

    def check(sub):
        fqdn = f"{sub}.{domain}"
        a = query_record(fqdn, "A", resolver, debug)
        aaaa = query_record(fqdn, "AAAA", resolver, debug)
        cname = query_record(fqdn, "CNAME", resolver, debug)
        if a or aaaa or cname:
            return fqdn
        return None

    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(check, sub): sub for sub in wordlist}
        for future in as_completed(futures):
            result = future.result()
            if result:
                found.append(result)

    return sorted(found)


def print_section(title: str):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")


def print_records(rtype: str, records):
    if not records:
        return
    if isinstance(records, dict):
        # DKIM heeft sub-dict {selector: [records]}
        print(f"\n  [DKIM]")
        for sel, vals in records.items():
            print(f"    selector={sel}:")
            for v in vals:
                print(f"      {v}")
    else:
        print(f"\n  [{rtype}]")
        for r in records:
            print(f"    {r}")


def lookup_all_records(domain: str, resolver: dns.resolver.Resolver, debug: bool = False) -> dict:
    """Vraag alle standaard recordtypes op voor één domein."""
    results = {}
    for rtype in RECORD_TYPES:
        records = query_record(domain, rtype, resolver, debug)
        if records:
            results[rtype] = records
    # DMARC en DKIM apart opvragen
    extra = lookup_dkim_dmarc(domain, resolver, debug)
    results.update(extra)
    return results


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DNS Lookup Tool – haalt alle DNS records + subdomains op."
    )
    parser.add_argument("domain", help="Het te onderzoeken domein (bijv. example.com)")
    parser.add_argument("--no-ct", action="store_true",
        help="Sla Certificate Transparency (crt.sh) lookup over")
    parser.add_argument("--no-brute", action="store_true",
        help="Sla brute-force subdomain scan over")
    parser.add_argument("--json", metavar="FILE",
        help="Sla resultaten ook op als JSON (bijv. --json output.json)")
    wl_group = parser.add_mutually_exclusive_group()
    wl_group.add_argument("--wordlist", metavar="FILE",
        help="Combineer eigen wordlist met de ingebouwde lijst")
    wl_group.add_argument("--only-wordlist", metavar="FILE",
        help="Gebruik alleen de opgegeven wordlist, sla ingebouwde lijst over")
    parser.add_argument("--debug", action="store_true",
        help="Toon alle DNS-fouten (inclusief onverwachte exceptions)")
    parser.add_argument("--no-public-dns", action="store_true",
        help="Gebruik systeemresolver i.p.v. publieke DNS (8.8.8.8 / 1.1.1.1)")
    parser.add_argument("--timeout", type=float, default=8.0, metavar="SEC",
        help="Timeout per DNS-query in seconden (standaard: 8)")
    parser.add_argument("--no-sublist", action="store_true",
        help="Toon geen overzichtslijst van gevonden subdomains aan het einde")
    args = parser.parse_args()

    domain = args.domain.strip().lower().rstrip(".")
    use_public = not args.no_public_dns
    resolver = make_resolver(timeout=args.timeout, use_public_dns=use_public)
    output = {
        "domain": domain,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "records": {},
        "subdomains": {}
    }

    print(f"\n🔍 DNS Lookup voor: {domain}")
    print(f"   Tijdstip: {output['timestamp']}")
    if args.debug:
        print(f"   [debug modus actief]")
    ns_info = "publiek (8.8.8.8, 1.1.1.1)" if not args.no_public_dns else "systeem"
    print(f"   Nameservers  : {ns_info}")
    print(f"   Timeout      : {args.timeout}s (lifetime: {args.timeout*2}s)")

    # ── 1. Hoofd-domein records ──────────────────
    print_section(f"DNS Records voor {domain}")
    records = lookup_all_records(domain, resolver, args.debug)
    output["records"][domain] = records

    if records:
        for rtype, values in records.items():
            print_records(rtype, values)
    else:
        print("  ⚠️  Geen records gevonden (domein bestaat mogelijk niet).")
        print("  💡 Tip: probeer opnieuw met --debug om de exacte fout te zien.")
        sys.exit(1)

    # ── 2. Zone Transfer ────────────────────────
    print_section("Zone Transfer (AXFR)")
    zt_subs = try_zone_transfer(domain, resolver)
    if zt_subs:
        print(f"  Zone transfer geslaagd! {len(zt_subs)} namen gevonden:")
        for s in zt_subs:
            print(f"    {s}")
    else:
        print("  ℹ️  Zone transfer niet toegestaan (normaal voor publieke domeinen).")

    # ── 3. Certificate Transparency ─────────────
    all_subdomains = set(zt_subs)

    if not args.no_ct:
        print_section("Subdomains via Certificate Transparency (crt.sh)")
        ct_subs = fetch_ct_subdomains(domain)
        if ct_subs:
            print(f"  {len(ct_subs)} subdomain(s) gevonden via CT-logs:")
            for s in ct_subs:
                print(f"    {s}")
            all_subdomains.update(ct_subs)
        else:
            print("  ℹ️  Geen subdomains gevonden via CT-logs.")
    else:
        print("\n  [CT-lookup overgeslagen]")

    # ── 4. Brute-force ──────────────────────────
    if not args.no_brute:
        from pathlib import Path

        def load_wordlist(filename: str) -> list[str] | None:
            """Laad wordlist; zoekt eerst naast het script, dan in de werkmap."""
            script_dir = Path(__file__).parent
            wl_path = Path(filename)
            if not wl_path.is_absolute() and (script_dir / wl_path).exists():
                wl_path = script_dir / wl_path
            try:
                with open(wl_path) as f:
                    entries = [line.strip() for line in f if line.strip()]
                print(f"  Wordlist geladen : {wl_path} ({len(entries)} entries)")
                return entries
            except FileNotFoundError:
                print(f"  ⚠️  Wordlist niet gevonden in:")
                print(f"       - {script_dir / filename}")
                print(f"       - {Path(filename).resolve()}")
                return None

        if args.only_wordlist:
            # Alleen het opgegeven bestand, ingebouwde lijst wordt overgeslagen
            loaded = load_wordlist(args.only_wordlist)
            wordlist = loaded if loaded is not None else []
            label = "alleen wordlist"
        elif args.wordlist:
            # Combineer: ingebouwde lijst + eigen bestand (dedupliceren)
            loaded = load_wordlist(args.wordlist)
            if loaded is not None:
                combined = list(dict.fromkeys(COMMON_SUBDOMAINS + loaded))
                wordlist = combined
                label = f"ingebouwd + wordlist"
            else:
                wordlist = COMMON_SUBDOMAINS
                label = "ingebouwd (wordlist niet gevonden)"
        else:
            wordlist = COMMON_SUBDOMAINS
            label = "ingebouwd"

        if wordlist:
            print_section(f"Brute-force Subdomain Scan ({len(wordlist)} kandidaten — {label})")
            bf_subs = brute_force_subdomains(domain, wordlist, args.debug)
            if bf_subs:
                print(f"  {len(bf_subs)} subdomain(s) gevonden via brute-force:")
                for s in bf_subs:
                    print(f"    {s}")
                all_subdomains.update(bf_subs)
            else:
                print("  ℹ️  Geen extra subdomains gevonden via brute-force.")
        else:
            print("\n  ⚠️  Geen subdomains om te scannen (lege wordlist).")
    else:
        print("\n  [Brute-force scan overgeslagen]")

    # ── 5. Records voor gevonden subdomains ──────
    unique_subs = sorted(all_subdomains - {domain})
    if unique_subs:
        print_section(f"DNS Records voor {len(unique_subs)} Subdomains")
        for sub in unique_subs:
            sub_records = lookup_all_records(sub, resolver, args.debug)
            if sub_records:
                print(f"\n  🌐 {sub}")
                for rtype, values in sub_records.items():
                    print_records(rtype, values)
                output["subdomains"][sub] = sub_records

    # ── 6. JSON export ───────────────────────────
    if args.json:
        try:
            with open(args.json, "w") as f:
                json.dump(output, f, indent=2)
            print(f"\n✅ Resultaten opgeslagen in: {args.json}")
        except Exception as e:
            print(f"\n⚠️  Kon JSON niet opslaan: {e}")

    # ── Subdomainlijst ───────────────────────────
    if not args.no_sublist and unique_subs:
        print_section("Gevonden Subdomains — Overzicht")
        for sub in unique_subs:
            heeft_dns = "✅" if sub in output["subdomains"] else "⚪"
            print(f"  {heeft_dns}  {sub}")
        print()

    # ── Samenvatting ─────────────────────────────
    print_section("Samenvatting")
    print(f"  Domein            : {domain}")
    print(f"  Recordtypes hoofd : {', '.join(output['records'].get(domain, {}).keys()) or 'geen'}")
    print(f"  Subdomains totaal : {len(unique_subs)}")
    print(f"  Subdomains met DNS: {len(output['subdomains'])}")
    if unique_subs and args.no_sublist:
        print(f"  (subdomainlijst uitgeschakeld via --no-sublist)")
    print()


if __name__ == "__main__":
    main()
