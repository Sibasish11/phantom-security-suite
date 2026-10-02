#!/usr/bin/env python3
"""Harmless local-only recon simulation; no SQL endpoint or arbitrary payload exists."""
from __future__ import annotations

import http.cookiejar
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener


BASE_URL = os.environ.get("PHANTOMBANK_URL", "http://127.0.0.1:8001").rstrip("/")
parsed = urlparse(BASE_URL)
if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("Refusing to run: PHANTOMBANK_URL must point to localhost/loopback.")


def env_file_values() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def main() -> int:
    values = env_file_values()
    evidence_token = os.environ.get("DEFENDER_EVIDENCE_TOKEN", values.get("DEFENDER_EVIDENCE_TOKEN", ""))
    opener = build_opener(
        HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    origin = "http://localhost:3001"

    def call(path: str, method: str = "GET", body: dict | None = None):
        request = Request(
            BASE_URL + path,
            method=method,
            headers={
                "Origin": origin,
                "Content-Type": "application/json",
            },
            data=json.dumps(body).encode() if body is not None else None,
        )
        with opener.open(request, timeout=5) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}

    print("PhantomBank local safe attack simulation")
    print(f"Target: {BASE_URL} (loopback confirmed)")
    try:
        status, _ = call("/api/auth/login", "POST", {
            "email": "maya.bennett@northstar.test",
            "password": "DemoMaya!2025",
        })
        print(f"Synthetic login: HTTP {status}")
        if status != 200:
            return 1
        for path in ("/api/security/list-tables", "/api/security/enumerate-api", "/api/security/customers"):
            status, body = call(path)
            result = body.get("result", [])
            count = result.get("count", 0) if isinstance(result, dict) else len(result)
            print(f"Safe recon {path}: HTTP {status}, response items {count}")

        if not evidence_token:
            print("Defender evidence: unavailable (DEFENDER_EVIDENCE_TOKEN is not set)")
            return 0
        request = Request(
            BASE_URL + "/internal/defender-evidence?limit=20",
            headers={"X-Demo-Runner": evidence_token},
        )
        with opener.open(request, timeout=5) as response:
            evidence = json.loads(response.read().decode()).get("evidence", [])
        print("\nDefender evidence (separate local view; destination is intentionally visible here):")
        for item in evidence:
            print(json.dumps({
                "operation": item.get("operation"),
                "destination": item.get("destination"),
                "decision_id": item.get("decision_id"),
                "risk_score": item.get("risk_score"),
                "success": item.get("success"),
                "response_count": item.get("response_count"),
            }, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"Simulation could not complete: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
