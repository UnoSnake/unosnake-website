"""
UnoSnake — Client Airtable.

CRUD opérations sur la base Airtable Products.
Gère la pagination, les rate limits, et le logging propre.
Ne log JAMAIS le token.
"""

import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger("unosnake")


class AirtableClient:
    """Client pour la table Products Airtable."""

    def __init__(self, base_id: str, table_id: str, token: str, api_url: str = "https://api.airtable.com/v0"):
        if not base_id or not token:
            raise ValueError("Airtable base_id and token are required")
        self.base_id = base_id
        self.table_id = table_id
        self.token = token
        self.api_url = api_url
        self._base_url = f"{api_url}/{base_id}/{table_id}"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def list_records(self, fields: list[str] | None = None, page_size: int = 100) -> list[dict]:
        """
        Récupère tous les records (avec pagination automatique).

        Args:
            fields: Liste de champs à récupérer. None = tous.
            page_size: Taille de page (max 100).

        Returns:
            Liste de records Airtable complets.
        """
        all_records = []
        params = {"pageSize": min(page_size, 100)}

        if fields:
            params["fields[]"] = fields

        offset = None

        while True:
            if offset:
                params["offset"] = offset

            resp = requests.get(
                self._base_url,
                headers=self._headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            records = data.get("records", [])
            all_records.extend(records)

            offset = data.get("offset")
            if not offset:
                break

        logger.info(f"Airtable: fetched {len(all_records)} records")
        return all_records

    def create_record(self, fields: dict) -> str | None:
        """
        Crée un record dans Airtable.

        Args:
            fields: Dict des champs à créer.

        Returns:
            Record ID ou None si erreur.
        """
        resp = requests.post(
            self._base_url,
            headers=self._headers,
            json={"fields": fields},
            timeout=15,
        )
        resp.raise_for_status()

        record_id = resp.json().get("id")
        if record_id:
            logger.info(f"Airtable: created record {record_id}")
        return record_id

    def find_by_formula(self, formula: str, fields: list[str] | None = None) -> list[dict]:
        """
        Cherche des records par formule Airtable.

        Args:
            formula: Formule Airtable (ex: "{Amazon URL}='https://...'").
            fields: Champs à récupérer.

        Returns:
            Liste de records correspondants.
        """
        params = {"filterByFormula": formula, "pageSize": 100}
        if fields:
            params["fields[]"] = fields

        resp = requests.get(
            self._base_url,
            headers=self._headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("records", [])

    def update_record(self, record_id: str, fields: dict) -> bool:
        """
        Met à jour un record existant.

        Args:
            record_id: ID du record Airtable.
            fields: Dict des champs à mettre à jour.

        Returns:
            True si succès.
        """
        resp = requests.patch(
            f"{self._base_url}/{record_id}",
            headers=self._headers,
            json={"fields": fields},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"Airtable: updated record {record_id}")
        return True
