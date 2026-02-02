#!/usr/bin/env python3
"""
Generate OpenAPI specification from OMEN FastAPI app.

This script exports the OpenAPI schema to JSON and YAML files for:
- Documentation hosting
- SDK generation
- API contract versioning

Usage:
    python scripts/generate_openapi.py
    python scripts/generate_openapi.py --output docs/api/openapi.json
    python scripts/generate_openapi.py --yaml  # Also generate YAML
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def generate_openapi_spec(output_path: str = "docs/openapi.json") -> None:
    """
    Generate OpenAPI spec from FastAPI app.
    
    Args:
        output_path: Path to write the spec file
    """
    from omen.main import app
    
    # Get OpenAPI schema
    spec = app.openapi()
    
    # Enhance spec with additional metadata
    spec["info"]["x-logo"] = {
        "url": "https://omen.io/logo.png",
        "altText": "OMEN Logo",
    }
    
    spec["info"]["contact"] = {
        "name": "OMEN API Support",
        "url": "https://github.com/omen/omen",
        "email": "support@omen.io",
    }
    
    spec["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
    
    # Add server information
    spec["servers"] = [
        {
            "url": "https://api.omen.io",
            "description": "Production server",
        },
        {
            "url": "https://staging-api.omen.io",
            "description": "Staging server",
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development",
        },
    ]
    
    # Add security schemes
    spec["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token (optional, if enabled)",
        },
    }
    
    # Add global security requirement
    spec["security"] = [{"ApiKeyAuth": []}]
    
    # Add tags descriptions
    spec["tags"] = [
        {
            "name": "Health",
            "description": "Health check endpoints (public)",
        },
        {
            "name": "Signals",
            "description": "Core signal intelligence API",
        },
        {
            "name": "Partner Signals",
            "description": "Partner financial signals (metrics only, no risk verdicts)",
        },
        {
            "name": "Partner Risk (DEPRECATED)",
            "description": "⚠️ DEPRECATED - Use Partner Signals instead",
        },
        {
            "name": "Multi-Source Intelligence",
            "description": "Aggregated signals from multiple sources",
        },
        {
            "name": "Explanations",
            "description": "Signal explanation and audit trails",
        },
        {
            "name": "Methodology",
            "description": "OMEN methodology documentation",
        },
        {
            "name": "Statistics",
            "description": "Pipeline statistics and metrics",
        },
        {
            "name": "Storage",
            "description": "Ledger storage management",
        },
        {
            "name": "Realtime",
            "description": "Real-time price streaming (SSE)",
        },
        {
            "name": "Activity",
            "description": "Activity feed and audit log",
        },
    ]
    
    # Add examples to partner signals endpoints
    spec = add_examples(spec)
    
    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON spec
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    
    print(f"✅ OpenAPI spec generated: {output_path}")
    print(f"   Version: {spec['info']['version']}")
    print(f"   Paths: {len(spec.get('paths', {}))}")
    print(f"   Schemas: {len(spec.get('components', {}).get('schemas', {}))}")
    
    # Also generate YAML if available
    if YAML_AVAILABLE:
        yaml_path = output_file.with_suffix(".yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"✅ OpenAPI YAML generated: {yaml_path}")


def add_examples(spec: dict) -> dict:
    """Add examples to OpenAPI schemas for better documentation."""
    
    # Example partner signal response
    partner_signal_example = {
        "symbol": "GMD",
        "company_name": "Gemadept Corporation",
        "signals": {
            "price_current": 68.5,
            "price_previous_close": 67.9,
            "price_change_percent": 0.88,
            "volume": 1901300,
            "volume_avg_20d": 1500000,
            "volatility_20d": 0.023,
            "liquidity_score": 0.85,
            "trend_20d": 3.2,
            "zscore_price": 0.45,
        },
        "confidence": {
            "overall_confidence": 0.91,
            "data_completeness": 0.95,
            "data_freshness_seconds": 120,
            "price_data_confidence": 1.0,
            "fundamental_data_confidence": 0.0,
            "volume_data_confidence": 1.0,
            "missing_fields": [],
            "data_source": "vnstock",
            "data_source_reliability": 0.95,
            "confidence_interval": {
                "point_estimate": 0.91,
                "lower_bound": 0.85,
                "upper_bound": 0.97,
                "confidence_level": 0.95,
                "method": "weighted_bayesian",
            },
        },
        "evidence": [
            {
                "evidence_id": "GMD-PRICE-20260201100000",
                "evidence_type": "PRICE_CHANGE",
                "title": "GMD price increased 0.88%",
                "raw_value": 0.88,
                "normalized_value": 0.088,
                "source": "vnstock",
                "timestamp": "2026-02-01T10:00:00Z",
            }
        ],
        "timestamp": "2026-02-01T10:00:00Z",
    }
    
    # Example signal response
    signal_example = {
        "signal_id": "sig-poly-12345",
        "signal_type": "MARKET_MOVEMENT",
        "title": "Polymarket: US Election probability shift",
        "description": "Significant movement in election prediction markets",
        "probability": 0.65,
        "confidence": 0.88,
        "keywords": ["election", "politics", "prediction"],
        "source": "polymarket",
        "timestamp": "2026-02-01T10:00:00Z",
    }
    
    # Add examples to paths
    if "paths" in spec:
        for path, methods in spec["paths"].items():
            if "/partner-signals" in path and "/{" not in path:
                for method, details in methods.items():
                    if "responses" in details and "200" in details["responses"]:
                        if "content" in details["responses"]["200"]:
                            for content_type, content in details["responses"]["200"]["content"].items():
                                if content_type == "application/json":
                                    content["example"] = {
                                        "timestamp": "2026-02-01T10:00:00Z",
                                        "total_partners": 1,
                                        "partners": [partner_signal_example],
                                    }
            
            elif "/partner-signals/" in path and "{" in path:
                for method, details in methods.items():
                    if "responses" in details and "200" in details["responses"]:
                        if "content" in details["responses"]["200"]:
                            for content_type, content in details["responses"]["200"]["content"].items():
                                if content_type == "application/json":
                                    content["example"] = partner_signal_example
            
            elif "/signals" in path and "/partner" not in path and "{" not in path:
                for method, details in methods.items():
                    if method == "get" and "responses" in details and "200" in details["responses"]:
                        if "content" in details["responses"]["200"]:
                            for content_type, content in details["responses"]["200"]["content"].items():
                                if content_type == "application/json":
                                    content["example"] = {
                                        "items": [signal_example],
                                        "has_more": False,
                                        "cursor": None,
                                    }
    
    return spec


def generate_markdown_docs(spec_path: str, output_path: str = "docs/API_REFERENCE.md") -> None:
    """
    Generate markdown documentation from OpenAPI spec.
    """
    with open(spec_path, "r") as f:
        spec = json.load(f)
    
    lines = [
        f"# {spec['info']['title']}",
        "",
        f"Version: {spec['info']['version']}",
        "",
        spec['info'].get('description', ''),
        "",
        "## Authentication",
        "",
        "All API endpoints require authentication via API key.",
        "Include the `X-API-Key` header in all requests:",
        "",
        "```bash",
        "curl -H 'X-API-Key: your-api-key' https://api.omen.io/api/v1/signals",
        "```",
        "",
        "## Endpoints",
        "",
    ]
    
    # Group by tags
    for path, methods in spec.get('paths', {}).items():
        for method, details in methods.items():
            if method in ('get', 'post', 'put', 'delete', 'patch'):
                summary = details.get('summary', 'No summary')
                lines.append(f"### `{method.upper()} {path}`")
                lines.append("")
                lines.append(summary)
                lines.append("")
                
                if details.get('description'):
                    lines.append(details['description'])
                    lines.append("")
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"✅ API reference generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate OpenAPI specification")
    parser.add_argument(
        "--output", "-o",
        default="docs/openapi.json",
        help="Output path for OpenAPI JSON file",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Also generate markdown documentation",
    )
    
    args = parser.parse_args()
    
    try:
        generate_openapi_spec(args.output)
        
        if args.markdown:
            md_path = args.output.replace(".json", ".md").replace("openapi", "API_REFERENCE")
            generate_markdown_docs(args.output, md_path)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
