"""
UnoSnake — Pinterest API v5 Client.

Client léger pour l'API Pinterest v5 officielle.
Sandbox par défaut. Aucun scraping. Aucun token dans les logs.

API docs : https://developers.pinterest.com/docs/api/v5/

Permissions requises (après approbation Trial) :
  pins:read, pins:write, boards:read, boards:write
"""

import logging
import requests

logger = logging.getLogger("unosnake")

PINTEREST_API_BASE = "https://api.pinterest.com/v5"
PINTEREST_SANDBOX_BASE = "https://api-sandbox.pinterest.com/v5"


class PinterestClient:
    """Client pour l'API Pinterest v5."""

    def __init__(
        self,
        access_token: str,
        sandbox: bool = True,
        timeout: int = 15,
    ):
        if not access_token:
            raise ValueError("Pinterest access_token is required")

        self._token = access_token
        self._base_url = PINTEREST_SANDBOX_BASE if sandbox else PINTEREST_API_BASE
        self._timeout = timeout

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    @property
    def is_sandbox(self) -> bool:
        return "sandbox" in self._base_url

    def verify_token(self) -> dict:
        """
        Vérifie le token en appelant GET /user_account.

        Returns:
            dict: {"ok": bool, "username": str|None, "error": str|None}
        """
        try:
            resp = requests.get(
                f"{self._base_url}/user_account",
                headers=self._headers,
                timeout=self._timeout,
            )
            if resp.ok:
                data = resp.json()
                return {
                    "ok": True,
                    "username": data.get("username", ""),
                    "account_type": data.get("account_type", ""),
                }
            else:
                return {
                    "ok": False,
                    "status": resp.status_code,
                    "error": resp.text[:200],
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_boards(self) -> list[dict]:
        """
        Liste les boards de l'utilisateur.

        Returns:
            Liste de dicts : {"id": str, "name": str, "url": str}
        """
        resp = requests.get(
            f"{self._base_url}/boards",
            headers=self._headers,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return [
            {
                "id": b.get("id", ""),
                "name": b.get("name", ""),
                "url": b.get("url", ""),
            }
            for b in items
        ]

    def create_pin(self, payload: dict) -> dict:
        """
        Crée un Pin via POST /pins.

        Args:
            payload: dict conforme à l'API Pinterest v5 /pins.

        Returns:
            dict : réponse Pinterest (contient "id" si succès).

        Raises:
            requests.HTTPError si l'API retourne une erreur.
        """
        resp = requests.post(
            f"{self._base_url}/pins",
            headers=self._headers,
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_pin(self, pin_id: str) -> dict:
        """Récupère un Pin par son ID."""
        resp = requests.get(
            f"{self._base_url}/pins/{pin_id}",
            headers=self._headers,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()
