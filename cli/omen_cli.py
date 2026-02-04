#!/usr/bin/env python3
"""
OMEN CLI - Command Line Interface for OMEN Signal Intelligence Engine.

Usage:
    omen signals list [--limit=N] [--status=STATUS]
    omen signals get <signal_id>
    omen signals stream [--filter=FILTER]
    omen health [--detailed]
    omen sources list
    omen sources status <source_name>
    omen config show
    omen version

Commands:
    signals     Manage and view signals
    health      Check system health
    sources     View data source status
    config      View configuration
    version     Show version information

Examples:
    omen signals list --limit=10
    omen signals get sig_abc123
    omen health --detailed
    omen sources list
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Any, Optional

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)


# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_API_VERSION = "v1"


class OmenCLI:
    """OMEN Command Line Interface client."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Make HTTP request to OMEN API."""
        url = f"{self.base_url}/api/{DEFAULT_API_VERSION}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = self.client.request(
                method,
                url,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error: HTTP {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"Detail: {error_detail.get('detail', 'Unknown error')}")
            except Exception:
                print(f"Response: {e.response.text}")
            sys.exit(1)
        except httpx.RequestError as e:
            print(f"Error: Could not connect to {url}")
            print(f"Detail: {e}")
            sys.exit(1)

    def get(self, endpoint: str, **kwargs) -> dict[str, Any]:
        """GET request."""
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> dict[str, Any]:
        """POST request."""
        return self._request("POST", endpoint, **kwargs)


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return dt_str


def format_json(data: Any, indent: int = 2) -> str:
    """Format JSON for display."""
    return json.dumps(data, indent=indent, default=str)


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print formatted table."""
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Print header
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for row in rows:
        row_line = " | ".join(
            str(cell).ljust(widths[i]) if i < len(widths) else str(cell)
            for i, cell in enumerate(row)
        )
        print(row_line)


# Command implementations
def cmd_signals_list(cli: OmenCLI, args: argparse.Namespace) -> None:
    """List recent signals."""
    params = {}
    if args.limit:
        params["limit"] = args.limit
    if args.status:
        params["status"] = args.status

    data = cli.get("signals", params=params)
    signals = data.get("signals", data.get("items", []))

    if not signals:
        print("No signals found.")
        return

    headers = ["ID", "Title", "Confidence", "Source", "Created"]
    rows = []
    for sig in signals:
        rows.append([
            sig.get("signal_id", "")[:12],
            (sig.get("title", "")[:40] + "...") if len(sig.get("title", "")) > 40 else sig.get("title", ""),
            f"{sig.get('confidence', 0):.2f}",
            sig.get("source", ""),
            format_datetime(sig.get("created_at", "")),
        ])

    print(f"\nFound {len(signals)} signals:\n")
    print_table(headers, rows)


def cmd_signals_get(cli: OmenCLI, args: argparse.Namespace) -> None:
    """Get signal details."""
    data = cli.get(f"signals/{args.signal_id}")
    print("\nSignal Details:")
    print(format_json(data))


def cmd_health(cli: OmenCLI, args: argparse.Namespace) -> None:
    """Check system health."""
    try:
        data = cli.get("health")
    except SystemExit:
        # Try root health endpoint
        try:
            response = cli.client.get(f"{cli.base_url}/health")
            data = response.json()
        except Exception:
            print("Error: Could not reach health endpoint")
            sys.exit(1)

    status = data.get("status", "unknown")
    status_emoji = "✅" if status == "healthy" else "❌"

    print(f"\n{status_emoji} System Status: {status.upper()}")
    print(f"   Version: {data.get('version', 'unknown')}")
    print(f"   Uptime: {data.get('uptime', 'unknown')}")

    if args.detailed:
        print("\nDetailed Status:")
        
        # Sources
        sources = data.get("sources", {})
        if sources:
            print("\n  Data Sources:")
            for source, status in sources.items():
                emoji = "✅" if status.get("healthy", False) else "❌"
                print(f"    {emoji} {source}: {status.get('status', 'unknown')}")

        # Components
        components = data.get("components", {})
        if components:
            print("\n  Components:")
            for comp, status in components.items():
                emoji = "✅" if status.get("healthy", False) else "❌"
                print(f"    {emoji} {comp}: {status.get('status', 'unknown')}")


def cmd_sources_list(cli: OmenCLI, args: argparse.Namespace) -> None:
    """List data sources."""
    try:
        data = cli.get("health/sources")
    except SystemExit:
        # Fallback to health endpoint
        data = cli.get("health")
        data = {"sources": data.get("sources", {})}

    sources = data.get("sources", {})

    if not sources:
        print("No source information available.")
        return

    headers = ["Source", "Status", "Last Check", "Latency"]
    rows = []
    for name, info in sources.items():
        status = "✅ Healthy" if info.get("healthy", False) else "❌ Unhealthy"
        rows.append([
            name,
            status,
            format_datetime(info.get("last_check", "")),
            f"{info.get('latency_ms', 0):.0f}ms",
        ])

    print("\nData Sources:\n")
    print_table(headers, rows)


def cmd_sources_status(cli: OmenCLI, args: argparse.Namespace) -> None:
    """Get detailed source status."""
    data = cli.get(f"health/sources/{args.source_name}")
    print(f"\nSource: {args.source_name}")
    print(format_json(data))


def cmd_config_show(cli: OmenCLI, args: argparse.Namespace) -> None:
    """Show current configuration."""
    print("\nCLI Configuration:")
    print(f"  Base URL: {cli.base_url}")
    print(f"  API Key: {'*****' if cli.api_key else 'Not set'}")
    print(f"  API Version: {DEFAULT_API_VERSION}")


def cmd_version(cli: OmenCLI, args: argparse.Namespace) -> None:
    """Show version information."""
    print("\nOMEN CLI v1.0.0")
    print("Signal Intelligence Engine Command Line Interface")
    
    # Try to get server version
    try:
        data = cli.get("health")
        print(f"Server Version: {data.get('version', 'unknown')}")
    except Exception:
        print("Server Version: (not connected)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OMEN CLI - Signal Intelligence Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--api-key",
        help="API key for authentication",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Signals commands
    signals_parser = subparsers.add_parser("signals", help="Manage signals")
    signals_sub = signals_parser.add_subparsers(dest="subcommand")

    # signals list
    list_parser = signals_sub.add_parser("list", help="List signals")
    list_parser.add_argument("--limit", type=int, default=20, help="Max signals")
    list_parser.add_argument("--status", help="Filter by status")

    # signals get
    get_parser = signals_sub.add_parser("get", help="Get signal details")
    get_parser.add_argument("signal_id", help="Signal ID")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check system health")
    health_parser.add_argument("--detailed", action="store_true", help="Show details")

    # Sources commands
    sources_parser = subparsers.add_parser("sources", help="Data source info")
    sources_sub = sources_parser.add_subparsers(dest="subcommand")

    sources_sub.add_parser("list", help="List sources")
    
    status_parser = sources_sub.add_parser("status", help="Source status")
    status_parser.add_argument("source_name", help="Source name")

    # Config command
    subparsers.add_parser("config", help="Show configuration")

    # Version command
    subparsers.add_parser("version", help="Show version")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Create CLI client
    cli = OmenCLI(
        base_url=args.base_url,
        api_key=args.api_key,
    )

    # Route to command handler
    if args.command == "signals":
        if args.subcommand == "list":
            cmd_signals_list(cli, args)
        elif args.subcommand == "get":
            cmd_signals_get(cli, args)
        else:
            signals_parser.print_help()
    elif args.command == "health":
        cmd_health(cli, args)
    elif args.command == "sources":
        if args.subcommand == "list":
            cmd_sources_list(cli, args)
        elif args.subcommand == "status":
            cmd_sources_status(cli, args)
        else:
            sources_parser.print_help()
    elif args.command == "config":
        cmd_config_show(cli, args)
    elif args.command == "version":
        cmd_version(cli, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
