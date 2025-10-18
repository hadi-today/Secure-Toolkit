"""Flask blueprint that powers the keyring manager web panel."""

from __future__ import annotations

import re
from typing import Dict, List

from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    render_template,
    request,
)

from auth_crypto import encrypt_and_save_keyring, load_and_decrypt_keyring

from plugins.web_panel.server.web_auth import token_required


keyring_bp = Blueprint(
    "keyring_manager_panel",
    __name__,
    template_folder="templates",
    static_folder="static",
)


class KeyringLockedError(RuntimeError):
    """Raised when the encrypted keyring cannot be accessed."""


def _get_keyring_key() -> bytes:
    token = getattr(g, "webpanel_token", None)
    sessions = current_app.config.setdefault("KEYRING_SESSIONS", {})

    if token:
        token_context = sessions.get(token)
        if token_context and token_context.get("key"):
            return token_context["key"]

    context = current_app.config.get("KEYRING_CONTEXT")
    if context and context.get("key"):
        normalized_context = {"key": context["key"]}
        if token and token not in sessions:
            sessions[token] = dict(normalized_context)
        current_app.config["KEYRING_CONTEXT"] = normalized_context
        current_app.config["KEYRING_ACTIVE_KEY"] = normalized_context["key"]
        return normalized_context["key"]

    active_key = current_app.config.get("KEYRING_ACTIVE_KEY")
    if isinstance(active_key, (bytes, bytearray)):
        if token and token not in sessions:
            sessions[token] = {"key": active_key}
        current_app.config["KEYRING_CONTEXT"] = {"key": active_key}
        current_app.config["KEYRING_ACTIVE_KEY"] = active_key
        return active_key

    for cached_context in sessions.values():
        key = cached_context.get("key") if isinstance(cached_context, dict) else None
        if key:
            normalized_context = {"key": key}
            if token and token not in sessions:
                sessions[token] = dict(normalized_context)
            current_app.config["KEYRING_CONTEXT"] = normalized_context
            current_app.config["KEYRING_ACTIVE_KEY"] = key
            return key

    raise KeyringLockedError("Keyring is locked. Please log in from the desktop app.")


def _load_keyring() -> Dict[str, List[Dict[str, str]]]:
    keyring = load_and_decrypt_keyring(_get_keyring_key())
    keyring.setdefault("my_key_pairs", [])
    keyring.setdefault("contact_public_keys", [])
    return keyring


def _save_keyring(updated_data: Dict[str, List[Dict[str, str]]]) -> None:
    encrypt_and_save_keyring(_get_keyring_key(), updated_data)


def _build_entries(raw_items: List[Dict[str, str]], prefix: str) -> List[Dict[str, str]]:
    entries = []
    for index, item in enumerate(raw_items):
        name = item.get("name", "Unnamed")
        public_key = item.get("public_key", "")
        if not isinstance(public_key, str):
            public_key = str(public_key)
        entries.append(
            {
                "id": f"{prefix}-{index}",
                "name": name,
                "public_key": public_key,
                "preview": "".join(public_key.splitlines(True)[:4]).strip(),
            }
        )
    return entries


def _parse_key_identifier(key_id: str):
    match = re.fullmatch(r"(my|contact)-(\d+)", key_id)
    if not match:
        return None, None
    category, index_text = match.groups()
    return category, int(index_text)


@keyring_bp.route("/")
@token_required
def keyring_page():
    return render_template("keyring.html")


@keyring_bp.route("/api/summary", methods=["GET"])
@token_required
def keyring_summary():
    try:
        keyring = _load_keyring()
    except KeyringLockedError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:  # pragma: no cover - surfaced to UI
        current_app.logger.error("Failed to load keyring summary: %s", error)
        return jsonify({"error": "Unable to read encrypted keyring."}), 500

    my_count = len(keyring["my_key_pairs"])
    contact_count = len(keyring["contact_public_keys"])
    return jsonify(
        {
            "my_public_keys": my_count,
            "contact_public_keys": contact_count,
            "total_public_keys": my_count + contact_count,
        }
    )


@keyring_bp.route("/api/public-keys", methods=["GET"])
@token_required
def list_public_keys():
    try:
        keyring = _load_keyring()
    except KeyringLockedError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:  # pragma: no cover - surfaced to UI
        current_app.logger.error("Failed to load keyring entries: %s", error)
        return jsonify({"error": "Unable to read encrypted keyring."}), 500

    return jsonify(
        {
            "my_keys": _build_entries(keyring["my_key_pairs"], "my"),
            "contact_keys": _build_entries(keyring["contact_public_keys"], "contact"),
        }
    )


@keyring_bp.route("/api/public-keys", methods=["POST"])
@token_required
def add_public_key():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    public_key = (payload.get("public_key") or "").strip()

    if not name or not public_key:
        return jsonify({"error": "Both name and public key content are required."}), 400

    if not (public_key.startswith("-----BEGIN") or public_key.startswith("ssh-")):
        return jsonify({"error": "The provided key does not look like a valid public key."}), 400

    try:
        keyring = _load_keyring()
    except KeyringLockedError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:  # pragma: no cover - surfaced to UI
        current_app.logger.error("Failed to load keyring for update: %s", error)
        return jsonify({"error": "Unable to read encrypted keyring."}), 500

    keyring["contact_public_keys"].append({"name": name, "public_key": public_key})

    try:
        _save_keyring(keyring)
    except Exception as error:  # pragma: no cover - surfaced to UI
        current_app.logger.error("Failed to save updated keyring: %s", error)
        return jsonify({"error": "Unable to save the new key. Please try again."}), 500

    return jsonify({"message": "Public key added successfully."}), 201


@keyring_bp.route("/api/public-keys/<key_id>/download", methods=["GET"])
@token_required
def download_public_key(key_id: str):
    category, index = _parse_key_identifier(key_id)
    if category is None:
        return jsonify({"error": "Invalid key identifier."}), 400

    try:
        keyring = _load_keyring()
    except KeyringLockedError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:  # pragma: no cover - surfaced to UI
        current_app.logger.error("Failed to load keyring for download: %s", error)
        return jsonify({"error": "Unable to read encrypted keyring."}), 500

    collection_name = "my_key_pairs" if category == "my" else "contact_public_keys"
    items = keyring.get(collection_name, [])

    if index < 0 or index >= len(items):
        return jsonify({"error": "Key not found."}), 404

    entry = items[index]
    public_key = entry.get("public_key", "")
    name = entry.get("name", "exported_key")

    if not isinstance(public_key, str):
        public_key = str(public_key)
    if not isinstance(name, str):
        name = str(name)

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "public_key"
    filename = f"{safe_name}_public.pem"

    response = Response(public_key, mimetype="text/plain; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
