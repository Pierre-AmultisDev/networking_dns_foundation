#!/usr/bin/env python3
"""
# =============================================================================
#
# @package    networking 
# @container  dns_foundation
# @name       dns_diagnose.py
# @version    v0.0.1  2026-05-17
# @author     pierre@amultis.dev
# @copyright  (C) Pierre Veelen
#
# @location  @my_code\_for_python\networking\dns_foundation\code\py_app
# 
# ============================================================================= 

DNS Diagnose Script - Voer dit uit om te zien wat er precies misgaat.
Geeft alle relevante info voor debugging van dns_lookup.py

"""

import sys
import socket

print("=" * 60)
print("DNS DIAGNOSE")
print("=" * 60)

# ── Python & dnspython versie ──
print(f"\nPython versie : {sys.version}")
try:
    import dns
    import dns.resolver
    import dns.exception
    import dns.rdatatype
    v = getattr(dns, 'version', None)
    if v:
        print(f"dnspython     : {v.version}")
    else:
        import importlib.metadata
        print(f"dnspython     : {importlib.metadata.version('dnspython')}")
except Exception as e:
    print(f"dnspython     : FOUT bij importeren: {e}")
    sys.exit(1)

# ── Systeemresolver ──
print(f"\nSystemresolver: {dns.resolver.Resolver().nameservers}")

# ── Socket-test (poort 53) ──
print("\n--- Socket test (UDP poort 53) ---")
for ns in ["8.8.8.8", "1.1.1.1"]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)
        s.connect((ns, 53))
        s.close()
        print(f"  {ns}:53  ✅ bereikbaar")
    except Exception as e:
        print(f"  {ns}:53  ❌ NIET bereikbaar: {e}")

# ── Exception-klassen aanwezig? ──
print("\n--- Exception klassen ---")
for attr in ["NoAnswer", "NXDOMAIN", "NoNameservers", "LifetimeTimeout"]:
    aanwezig = hasattr(dns.resolver, attr)
    print(f"  dns.resolver.{attr:<20} {'✅' if aanwezig else '❌ ontbreekt'}")
print(f"  dns.exception.Timeout            ✅")
aanwezig = hasattr(dns.rdatatype, "UnknownRdatatype")
print(f"  dns.rdatatype.UnknownRdatatype   {'✅' if aanwezig else '❌ ontbreekt'}")

# ── Directe DNS queries met volledige exception-info ──
print("\n--- DNS queries voor wee-play.nl ---")
r = dns.resolver.Resolver()
r.timeout = 5
r.lifetime = 5

for rtype in ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "CAA"]:
    try:
        ans = r.resolve("wee-play.nl", rtype)
        vals = [str(a) for a in ans]
        print(f"  {rtype:<8} ✅  {vals[0][:60]}{'...' if len(vals[0]) > 60 else ''}")
    except Exception as e:
        print(f"  {rtype:<8} ❌  {type(e).__module__}.{type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Kopieer bovenstaande output en deel hem voor verdere hulp.")
print("=" * 60)
