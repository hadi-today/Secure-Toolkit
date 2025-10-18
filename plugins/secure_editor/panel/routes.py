"""Flask blueprint that powers the Secure Editor web panel."""

from __future__ import annotations

import difflib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, Iterable, List, Optional, Tuple

from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    render_template,
    request,
)

from auth_crypto import load_and_decrypt_keyring
from plugins.secure_editor.editor_modules import config
from plugins.secure_editor.editor_modules.crypto_manager import decrypt_content
from plugins.web_panel.server.web_auth import token_required

from cryptography.hazmat.primitives import serialization


secure_editor_bp = Blueprint(
    "secure_editor_panel",
    __name__,
    template_folder="templates",
    static_folder="static",
)


class KeyringLockedError(RuntimeError):
    """Raised when the encrypted keyring is not available."""


class PrivateKeyUnavailableError(RuntimeError):
    """Raised when a version cannot be decrypted due to missing key material."""

    def __init__(
        self,
        message: str,
        *,
        key_name: Optional[str] = None,
        requires_passphrase: bool = False,
    ) -> None:
        super().__init__(message)
        self.key_name = key_name
        self.requires_passphrase = requires_passphrase


@dataclass
class VersionRecord:
    """Simple container for version metadata and content."""

    id: int
    note_id: int
    timestamp: str
    key_name: str
    html_content: Optional[str] = None


class _HTMLTextExtractor(HTMLParser):
    """Convert rich HTML content into normalized plain text."""

    BLOCK_TAGS = {
        "p",
        "div",
        "br",
        "li",
        "ul",
        "ol",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "table",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        if tag.lower() in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if data.strip():
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag.lower() in self.BLOCK_TAGS:
            self._parts.append("\n")

    def get_text(self) -> str:
        joined = "".join(self._parts)
        lines = [line.strip() for line in joined.splitlines()]
        filtered = [line for line in lines if line]
        return "\n".join(filtered)


def _connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(config.DB_FILE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _get_token_context(create: bool = True) -> Dict[str, object]:
    sessions = current_app.config.setdefault("KEYRING_SESSIONS", {})
    token = getattr(g, "webpanel_token", None)

    if token:
        if create:
            return sessions.setdefault(token, {})
        context = sessions.get(token)
        if isinstance(context, dict):
            return context
        return {}

    if create:
        return current_app.config.setdefault("KEYRING_CONTEXT", {})

    context = current_app.config.get("KEYRING_CONTEXT")
    return context if isinstance(context, dict) else {}


def _remember_key(key: bytes) -> bytes:
    context = _get_token_context()
    context["key"] = key
    current_app.config["KEYRING_CONTEXT"] = {"key": key}
    current_app.config["KEYRING_ACTIVE_KEY"] = key
    return key


def _get_keyring_key() -> bytes:
    context = _get_token_context(create=False)
    key_candidate = context.get("key") if isinstance(context, dict) else None
    if isinstance(key_candidate, (bytes, bytearray)):
        return bytes(key_candidate)

    shared_context = current_app.config.get("KEYRING_CONTEXT")
    if isinstance(shared_context, dict):
        key_candidate = shared_context.get("key")
        if isinstance(key_candidate, (bytes, bytearray)):
            return _remember_key(bytes(key_candidate))

    active_key = current_app.config.get("KEYRING_ACTIVE_KEY")
    if isinstance(active_key, (bytes, bytearray)):
        return _remember_key(bytes(active_key))

    sessions = current_app.config.setdefault("KEYRING_SESSIONS", {})
    for cached in sessions.values():
        key_candidate = cached.get("key") if isinstance(cached, dict) else None
        if isinstance(key_candidate, (bytes, bytearray)):
            return _remember_key(bytes(key_candidate))

    raise KeyringLockedError("Keyring is locked. Please log in from the desktop app.")


def _load_keyring_data() -> Dict[str, object]:
    try:
        key = _get_keyring_key()
        return load_and_decrypt_keyring(key)
    except KeyringLockedError:
        raise
    except Exception as error:  # pragma: no cover - surfaced to API response
        current_app.logger.error("Failed to load keyring data: {0}".format(error))
        raise KeyringLockedError("Unable to unlock encrypted keyring.") from error


def _get_unlocked_passphrase(key_name: str) -> Optional[str]:
    context = _get_token_context(create=False)
    if not isinstance(context, dict):
        return None

    unlocked = context.get("unlocked_keys")
    if isinstance(unlocked, dict) and key_name in unlocked:
        value = unlocked.get(key_name)
        if isinstance(value, str):
            return value
        if value is None:
            return None
    return None


def _set_unlocked_passphrase(key_name: str, passphrase: Optional[str]) -> None:
    context = _get_token_context()
    unlocked = context.setdefault("unlocked_keys", {})
    if not isinstance(unlocked, dict):
        unlocked = {}
        context["unlocked_keys"] = unlocked

    if passphrase is None:
        unlocked.pop(key_name, None)
    else:
        unlocked[key_name] = passphrase


def _get_private_key(key_name: str) -> Tuple[str, Optional[str]]:
    keyring = _load_keyring_data()
    pairs = keyring.get("my_key_pairs") if isinstance(keyring, dict) else None
    if not isinstance(pairs, Iterable):
        raise PrivateKeyUnavailableError(
            "No private keys are available in the keyring.",
            key_name=key_name,
        )

    for entry in pairs:
        if isinstance(entry, dict) and entry.get("name") == key_name:
            private_key = entry.get("private_key")
            if not private_key:
                raise PrivateKeyUnavailableError(
                    f"Key '{key_name}' does not include a private key.",
                    key_name=key_name,
                )
            if "ENCRYPTED" in private_key:
                passphrase = _get_unlocked_passphrase(key_name)
                if passphrase is None:
                    raise PrivateKeyUnavailableError(
                        "This private key is encrypted. Unlock it above to view this version.",
                        key_name=key_name,
                        requires_passphrase=True,
                    )
                return private_key, passphrase
            return private_key, None

    raise PrivateKeyUnavailableError(
        f"Private key '{key_name}' is not available.",
        key_name=key_name,
    )


def _decrypt_version(row: sqlite3.Row) -> VersionRecord:
    private_key_pem, passphrase = _get_private_key(row["encrypting_key_name"])
    bundle = {
        "content_ciphertext": row["content_ciphertext"],
        "wrapped_cek": row["wrapped_cek"],
    }
    plaintext = decrypt_content(bundle, private_key_pem, passphrase)
    html_content = plaintext.decode("utf-8")
    return VersionRecord(
        id=row["id"],
        note_id=row["note_id"],
        timestamp=row["timestamp"],
        key_name=row["encrypting_key_name"],
        html_content=html_content,
    )


def _find_previous_version_id(
    connection: sqlite3.Connection, note_id: int, version_id: int
) -> Optional[int]:
    cursor = connection.execute(
        """
        SELECT id
        FROM versions
        WHERE note_id = ? AND id < ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (note_id, version_id),
    )
    row = cursor.fetchone()
    return int(row[0]) if row else None


def _build_diff_html(current_text: str, previous_text: str) -> str:
    current_lines = current_text.splitlines() or [""]
    previous_lines = previous_text.splitlines() or [""]
    diff = difflib.HtmlDiff(wrapcolumn=88)
    return diff.make_table(
        previous_lines,
        current_lines,
        fromdesc="Previous version",
        todesc="Selected version",
        context=True,
        numlines=4,
    )


def _html_to_text(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def _list_key_pairs() -> List[Dict[str, object]]:
    try:
        keyring = _load_keyring_data()
    except KeyringLockedError:
        raise

    pairs = keyring.get("my_key_pairs") if isinstance(keyring, dict) else None
    if not isinstance(pairs, Iterable):
        return []

    context = _get_token_context(create=False)
    unlocked = {}
    if isinstance(context, dict):
        unlocked_ref = context.get("unlocked_keys")
        if isinstance(unlocked_ref, dict):
            unlocked = unlocked_ref

    key_list: List[Dict[str, object]] = []
    for entry in pairs:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        private_key = entry.get("private_key")
        has_private = bool(private_key)
        is_encrypted = bool(private_key and "ENCRYPTED" in private_key)
        key_list.append(
            {
                "name": name,
                "has_private_key": has_private,
                "is_encrypted": is_encrypted,
                "is_unlocked": (name in unlocked) if is_encrypted else has_private,
            }
        )

    return key_list


@secure_editor_bp.route("/")
@token_required
def panel_home() -> Response:
    return render_template("secure_editor.html")


@secure_editor_bp.route("/api/keys", methods=["GET"])
@token_required
def list_key_pairs() -> Response:
    try:
        keys = _list_key_pairs()
    except KeyringLockedError as error:
        return jsonify({"error": str(error)}), 503

    return jsonify({"keys": keys})


@secure_editor_bp.route("/api/keys/unlock", methods=["POST"])
@token_required
def unlock_key() -> Response:
    payload = request.get_json(silent=True) or {}
    key_name = payload.get("key_name")

    if not isinstance(key_name, str) or not key_name.strip():
        return jsonify({"error": "Key name is required."}), 400

    key_name = key_name.strip()

    try:
        keyring = _load_keyring_data()
    except KeyringLockedError as error:
        return jsonify({"error": str(error)}), 503

    pairs = keyring.get("my_key_pairs") if isinstance(keyring, dict) else None
    target: Optional[Dict[str, object]] = None
    if isinstance(pairs, Iterable):
        for entry in pairs:
            if isinstance(entry, dict) and entry.get("name") == key_name:
                target = entry
                break

    if target is None:
        return jsonify({"error": f"Key '{key_name}' was not found."}), 404

    private_key = target.get("private_key") if isinstance(target, dict) else None
    if not isinstance(private_key, str) or not private_key.strip():
        _set_unlocked_passphrase(key_name, None)
        return jsonify({"error": f"Key '{key_name}' does not include a private key."}), 409

    is_encrypted = "ENCRYPTED" in private_key
    passphrase = payload.get("passphrase") if is_encrypted else None
    if is_encrypted and passphrase is None:
        return jsonify({"error": "Enter the private key passphrase to unlock.", "key_name": key_name}), 400

    if isinstance(passphrase, str):
        password_value = passphrase
    elif passphrase is None:
        password_value = None
    else:
        password_value = str(passphrase)

    password_bytes = (
        password_value.encode("utf-8") if password_value is not None else None
    )

    try:
        serialization.load_pem_private_key(
            private_key.encode("utf-8"),
            password=password_bytes,
        )
    except TypeError:
        return jsonify({"error": "This private key requires a passphrase.", "key_name": key_name}), 400
    except ValueError:
        return jsonify({"error": "Incorrect passphrase. Please try again.", "key_name": key_name}), 401
    except Exception as error:  # pragma: no cover - surfaced to UI
        current_app.logger.error(
            "Unexpected error while unlocking key %s: %s", key_name, error
        )
        return jsonify({"error": "Unable to unlock the selected key."}), 500

    if is_encrypted:
        _set_unlocked_passphrase(key_name, password_value or "")
    else:
        _set_unlocked_passphrase(key_name, None)

    context = _get_token_context()
    context["selected_key"] = key_name

    message = "Key unlocked successfully." if is_encrypted else "Private key is ready to use."
    return jsonify(
        {
            "message": message,
            "key_name": key_name,
            "is_encrypted": is_encrypted,
        }
    )


@secure_editor_bp.route("/api/notes", methods=["GET"])
@token_required
def list_notes() -> Response:
    try:
        with closing(_connect_db()) as connection:
            cursor = connection.execute(
                """
                SELECT
                    notes.id AS id,
                    notes.name AS name,
                    COUNT(versions.id) AS version_count,
                    MAX(versions.timestamp) AS latest_timestamp
                FROM notes
                LEFT JOIN versions ON versions.note_id = notes.id
                GROUP BY notes.id
                ORDER BY notes.name
                """
            )
            notes = []
            for row in cursor.fetchall():
                notes.append(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "version_count": row["version_count"],
                        "latest_timestamp": row["latest_timestamp"],
                    }
                )
    except sqlite3.Error as error:
        current_app.logger.error("Failed to load secure editor notes: %s", error)
        return jsonify({"error": "Unable to read note catalog."}), 500

    return jsonify({"notes": notes})


@secure_editor_bp.route("/api/notes/<int:note_id>/versions", methods=["GET"])
@token_required
def list_versions(note_id: int) -> Response:
    try:
        with closing(_connect_db()) as connection:
            cursor = connection.execute(
                """
                SELECT id, timestamp, encrypting_key_name
                FROM versions
                WHERE note_id = ?
                ORDER BY timestamp DESC
                """,
                (note_id,),
            )
            versions = [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "key_name": row["encrypting_key_name"],
                }
                for row in cursor.fetchall()
            ]
    except sqlite3.Error as error:
        current_app.logger.error("Failed to load secure editor versions: %s", error)
        return jsonify({"error": "Unable to read version history."}), 500

    if not versions:
        return jsonify({"versions": [], "note_id": note_id})

    return jsonify({"versions": versions, "note_id": note_id})


@secure_editor_bp.route(
    "/api/notes/<int:note_id>/versions/<int:version_id>", methods=["GET"]
)
@token_required
def view_version(note_id: int, version_id: int) -> Response:
    compare_to = request.args.get("compare_to", type=int)

    try:
        with closing(_connect_db()) as connection:
            cursor = connection.execute(
                """
                SELECT id, note_id, timestamp, content_ciphertext, wrapped_cek, encrypting_key_name
                FROM versions
                WHERE id = ? AND note_id = ?
                """,
                (version_id, note_id),
            )
            row = cursor.fetchone()
            if row is None:
                return jsonify({"error": "Requested version was not found."}), 404

            record = _decrypt_version(row)
            plain_text = _html_to_text(record.html_content or "")

            if compare_to is None:
                compare_to = _find_previous_version_id(connection, note_id, version_id)

            diff_html = None
            compared_version = None

            if compare_to and compare_to != version_id:
                cursor = connection.execute(
                    """
                    SELECT id, note_id, timestamp, content_ciphertext, wrapped_cek, encrypting_key_name
                    FROM versions
                    WHERE id = ? AND note_id = ?
                    """,
                    (compare_to, note_id),
                )
                other_row = cursor.fetchone()
                if other_row is not None:
                    try:
                        previous_record = _decrypt_version(other_row)
                        previous_text = _html_to_text(previous_record.html_content or "")
                        diff_html = _build_diff_html(plain_text, previous_text)
                        compared_version = {
                            "id": previous_record.id,
                            "timestamp": previous_record.timestamp,
                        }
                    except PrivateKeyUnavailableError as error:
                        diff_html = None
                        current_app.logger.warning(
                            "Unable to decrypt comparison version %s: %s",
                            compare_to,
                            error,
                        )
                    except Exception as error:  # pragma: no cover - surfaced to UI
                        diff_html = None
                        current_app.logger.error(
                            "Unexpected error while building diff: %s",
                            error,
                        )

    except PrivateKeyUnavailableError as error:
        response = {"error": str(error)}
        if getattr(error, "key_name", None):
            response["key_name"] = error.key_name
        if getattr(error, "requires_passphrase", False):
            response["requires_passphrase"] = True
        return jsonify(response), 409
    except KeyringLockedError as error:
        return jsonify({"error": str(error)}), 503
    except sqlite3.Error as error:
        current_app.logger.error("Database error while reading version: %s", error)
        return jsonify({"error": "Unable to read encrypted version."}), 500
    except Exception as error:  # pragma: no cover - surfaced to UI
        current_app.logger.error("Unexpected error while decrypting note: %s", error)
        return jsonify({"error": "Unable to decrypt the requested version."}), 500

    response = {
        "note_id": record.note_id,
        "version": {
            "id": record.id,
            "timestamp": record.timestamp,
            "key_name": record.key_name,
            "content_html": record.html_content,
            "content_text": plain_text,
        },
        "comparison": compared_version,
        "diff_html": diff_html,
    }

    return jsonify(response)
