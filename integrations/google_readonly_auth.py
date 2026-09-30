"""OAuth setup utility for Jarvis's read-only personal Google connector."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google_auth_oauthlib.flow import Flow

try:
    from .google_readonly import (
        READONLY_SCOPES,
        client_secret_path,
        connection_status,
        credential_directory,
        token_path,
    )
except ImportError:  # Support direct execution from the command line.
    from google_readonly import (
        READONLY_SCOPES,
        client_secret_path,
        connection_status,
        credential_directory,
        token_path,
    )


REDIRECT_URI = "http://localhost:1"


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, path)
    os.chmod(path, 0o600)


def store_client_secret(source: str) -> None:
    source_path = Path(source).expanduser().resolve()
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not read the OAuth client JSON: {error}") from error
    if not isinstance(payload, dict) or "installed" not in payload:
        raise SystemExit("Use a Google OAuth Desktop app client-secret JSON file.")
    destination = client_secret_path()
    _write_private(destination, json.dumps(payload, indent=2) + "\n")
    print(f"Stored OAuth desktop client at {destination}")


def create_auth_url() -> None:
    secret = client_secret_path()
    if not secret.is_file():
        raise SystemExit("Store a Desktop OAuth client first with --client-secret PATH.")
    flow = Flow.from_client_secrets_file(
        str(secret),
        scopes=list(READONLY_SCOPES),
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=True,
    )
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",
        prompt="consent",
    )
    pending = {
        "state": state,
        "code_verifier": flow.code_verifier,
        "redirect_uri": REDIRECT_URI,
        "scopes": list(READONLY_SCOPES),
    }
    _write_private(
        credential_directory() / "pending.json",
        json.dumps(pending, indent=2) + "\n",
    )
    print(url)


def exchange_code(value: str) -> None:
    pending_path = credential_directory() / "pending.json"
    if not pending_path.is_file():
        raise SystemExit("Start with --auth-url before exchanging a code.")
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    redirect_url = value.strip()
    if not redirect_url.startswith(("http://", "https://")):
        raise SystemExit("Paste the complete OAuth redirect URL, including state.")
    query = parse_qs(urlparse(redirect_url).query)
    code = (query.get("code") or [""])[0]
    state = (query.get("state") or [None])[0]
    if not code:
        raise SystemExit("The redirect URL did not contain an OAuth code.")
    if state != pending.get("state"):
        raise SystemExit("OAuth state mismatch; start a fresh authorization flow.")

    flow = Flow.from_client_secrets_file(
        str(client_secret_path()),
        scopes=list(READONLY_SCOPES),
        redirect_uri=pending["redirect_uri"],
        state=pending["state"],
        code_verifier=pending.get("code_verifier"),
    )
    flow.fetch_token(code=code)
    payload = json.loads(flow.credentials.to_json())
    payload["scopes"] = list(READONLY_SCOPES)
    _write_private(token_path(), json.dumps(payload, indent=2) + "\n")
    pending_path.unlink(missing_ok=True)
    print("Read-only personal Gmail and Calendar OAuth is ready.")


def revoke_local() -> None:
    for name in ("token.json", "pending.json"):
        (credential_directory() / name).unlink(missing_ok=True)
    print("Removed local personal Google authorization files.")


def main() -> None:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--status", action="store_true")
    actions.add_argument("--client-secret")
    actions.add_argument("--auth-url", action="store_true")
    actions.add_argument("--auth-code")
    actions.add_argument("--revoke-local", action="store_true")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(connection_status(), indent=2))
    elif args.client_secret:
        store_client_secret(args.client_secret)
    elif args.auth_url:
        create_auth_url()
    elif args.auth_code:
        exchange_code(args.auth_code)
    elif args.revoke_local:
        revoke_local()


if __name__ == "__main__":
    main()
