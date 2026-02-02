"""
Polymarket network diagnostic script.

Checks DNS, TCP connectivity, and HTTP endpoints for Polymarket APIs.
Reports connect refused (e.g. WinError 10061) and proxy recommendations.

Usage:
  python -m scripts.polymarket_doctor
  python scripts/polymarket_doctor.py

From repo root after: pip install -e ".[dev]"
"""

import os
import socket
import sys
import time
from urllib.parse import urlparse

# Ensure package is on path when run as script
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

# Load .env if present
_env_file = os.path.join(_REPO_ROOT, ".env")
if os.path.isfile(_env_file):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass


def _dns_resolve(host: str) -> tuple[str, str]:
    """Resolve host to IP. Returns ('OK', ip) or ('FAIL', error_msg)."""
    try:
        ip = socket.gethostbyname(host)
        return ("OK", ip)
    except socket.gaierror as e:
        return ("FAIL", str(e))
    except Exception as e:
        return ("FAIL", str(e))


def _tcp_connect(host: str, port: int = 443) -> tuple[str, str]:
    """Try TCP connect to host:port. Returns ('OK', latency_ms) or ('FAIL', error_msg)."""
    start = time.perf_counter()
    try:
        s = socket.create_connection((host, port), timeout=10)
        s.close()
        latency_ms = (time.perf_counter() - start) * 1000
        return ("OK", f"{latency_ms:.0f}ms")
    except TimeoutError:
        return ("FAIL", "timeout")
    except OSError as e:
        err = str(e)
        if "10061" in err or "Connection refused" in err or "actively refused" in err:
            return ("FAIL", "connection refused (blocked/firewall?)")
        if "10060" in err or "timed out" in err:
            return ("FAIL", "timeout")
        return ("FAIL", err)
    except Exception as e:
        return ("FAIL", str(e))


def _http_get(url: str, timeout: float = 15.0) -> tuple[str, str]:
    """GET url. Returns ('OK', latency_ms or status) or ('FAIL', error_msg)."""
    start = time.perf_counter()
    try:
        import httpx
        r = httpx.get(url, timeout=timeout, trust_env=True)
        latency_ms = (time.perf_counter() - start) * 1000
        if r.is_success:
            return ("OK", f"{latency_ms:.0f}ms")
        return ("FAIL", f"HTTP {r.status_code} ({latency_ms:.0f}ms)")
    except httpx.ConnectError as e:
        err = str(e)
        if "10061" in err or "refused" in err.lower():
            return ("FAIL", "connection refused (WinError 10061 / blocked)")
        return ("FAIL", err)
    except httpx.TimeoutException:
        return ("FAIL", "timeout")
    except Exception as e:
        err = str(e)
        if "10061" in err or "refused" in err.lower():
            return ("FAIL", "connection refused (blocked/firewall?)")
        return ("FAIL", err)


def _row(label: str, status: str, detail: str) -> str:
    symbol = "OK" if status == "OK" else "FAIL"
    return f"  {label:<40} {symbol:<6} {detail}"


def main() -> int:
    from omen.polymarket_settings import get_polymarket_settings

    s = get_polymarket_settings()
    gamma_base = s.gamma_api_url.rstrip("/")
    clob_base = s.clob_api_url.rstrip("/")
    legacy_base = s.api_url.rstrip("/")
    ws_url = s.ws_url
    ws_host = urlparse(ws_url).hostname or "ws-subscriptions-clob.polymarket.com"

    hosts = [
        ("gamma-api", urlparse(gamma_base).hostname or "gamma-api.polymarket.com"),
        ("clob", urlparse(clob_base).hostname or "clob.polymarket.com"),
        ("legacy api", urlparse(legacy_base).hostname or "api.polymarket.com"),
        ("ws", ws_host),
    ]
    dns_ok = True
    tcp_ok = True

    print("Polymarket Doctor — network and API checks")
    print("Config (from env / .env):")
    print(f"  GAMMA_API_URL = {gamma_base}")
    print(f"  CLOB_API_URL  = {clob_base}")
    print(f"  WS_URL        = {ws_url}")
    print(f"  trust_env     = {s.httpx_trust_env}")
    print()

    # Proxy recommendation
    has_proxy = bool(os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"))
    if has_proxy and not s.httpx_trust_env:
        print("  [RECOMMENDATION] HTTP_PROXY/HTTPS_PROXY is set but POLYMARKET_HTTPX_TRUST_ENV=false.")
        print("  Set POLYMARKET_HTTPX_TRUST_ENV=true (or unset) so httpx uses the proxy.")
        print()
    elif has_proxy:
        print("  Proxy: HTTP_PROXY/HTTPS_PROXY will be used (trust_env=true).")
        print()

    # DNS
    print("DNS resolution:")
    for label, host in hosts:
        st, detail = _dns_resolve(host)
        if st != "OK":
            dns_ok = False
        print(_row(f"DNS {host}", st, detail))
    print()

    # TCP 443
    print("TCP connect (port 443):")
    for label, host in hosts:
        st, detail = _tcp_connect(host, 443)
        if st != "OK":
            tcp_ok = False
        print(_row(host, st, detail))
    print()

    # HTTP GET
    print("HTTP GET:")
    g1_st, g1_detail = _http_get(f"{gamma_base}/events?limit=1")
    print(_row("GET " + gamma_base + "/events?limit=1", g1_st, g1_detail))
    g2_st, g2_detail = _http_get(f"{gamma_base}/markets?limit=1&active=true")
    print(_row("GET " + gamma_base + "/markets?limit=1&active=true", g2_st, g2_detail))
    # CLOB midpoint often requires a real token_id; use dummy and accept 400/404
    clob_mid = f"{clob_base}/midpoint"
    cm_st, cm_detail = _http_get(f"{clob_base}/midpoint?token_id=dummy")
    if cm_st == "FAIL" and ("400" in cm_detail or "404" in cm_detail or "missing" in cm_detail.lower()):
        print(_row("GET " + clob_mid + "?token_id=<dummy>", "SKIP", "token_id required — use real token_id to test CLOB"))
    else:
        print(_row("GET " + clob_mid + "?token_id=dummy", cm_st, cm_detail))
    print()

    # Summary
    all_ok = dns_ok and tcp_ok
    if not all_ok:
        print("Some checks failed. Typical causes:")
        print("  - Corporate firewall / proxy: set HTTP_PROXY, HTTPS_PROXY, or allowlist domains.")
        print("  - Connection refused (10061): allowlist gamma-api.polymarket.com, clob.polymarket.com,")
        print("    api.polymarket.com, ws-subscriptions-clob.polymarket.com.")
        print("  - Run from home network or cloud VM if office blocks outbound.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
