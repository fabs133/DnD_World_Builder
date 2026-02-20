import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.logger import app_logger


class APIError(Exception):
    """Custom exception for local SRD API-related errors."""
    pass


class LocalAPIHandler:
    """
    Loads 5e SRD JSON files from disk and provides a local API-like interface.

    Automatically maps file names like '5e-SRD-Classes.json' to categories such as 'classes'.

    :param base_path: Path to the directory containing 5e-SRD JSON files.
    :type base_path: str
    """

    def __init__(self, base_path: str = "core/data_/rulebook_json"):
        self.base_path = Path(base_path).resolve()
        app_logger.debug(f"[LocalAPI] Base path: {self.base_path}")

        self.cache: Dict[str, Any] = {}
        self.filenames: Dict[str, str] = {}

        # More robust matching
        for file in self.base_path.iterdir():
            if file.is_file() and file.name.lower().startswith("5e-srd-") and file.suffix.lower() == ".json":
                match = re.match(r"5e-srd-(.+)\.json", file.name.lower())
                if match:
                    category = match.group(1).replace("-", "_")
                    app_logger.debug(f"[LocalAPI] Mapped '{file.name}' -> '{category}'")
                    self.filenames[category] = file.name
                else:
                    app_logger.warning(f"[LocalAPI] Skipped file not matching pattern: {file.name}")

        if not self.filenames:
            app_logger.error(f"[LocalAPI] No valid SRD files detected in {self.base_path}")

    def _load_file(self, category: str) -> Any:
        if category not in self.cache:
            filename = self.filenames.get(category)
            if not filename:
                raise APIError(f"[LocalAPI] Unknown category: '{category}', filename : '{filename}'")
            path = self.base_path / filename
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.cache[category] = json.load(f)
            except FileNotFoundError:
                raise APIError(f"[LocalAPI] File not found: {path}")
            except json.JSONDecodeError as e:
                raise APIError(f"[LocalAPI] JSON decode error in {filename}: {e}")
        return self.cache[category]

    def get(self, category: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._load_file(category)

    def get_raw(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        parts = endpoint.strip("/").split("/")
        if len(parts) < 3:
            raise APIError(f"[LocalAPI] Invalid endpoint path: {endpoint}")
        category, slug = parts[-2], parts[-1]
        items = self._load_file(category)
        for entry in items:
            if entry.get("index") == slug:
                return entry
        return None

    def get_monster(self, name: str) -> Optional[Dict[str, Any]]:
        slug = name.lower().replace(" ", "-")
        return self.get_raw(f"/api/monsters/{slug}")

    def get_spell(self, name: str) -> Optional[Dict[str, Any]]:
        slug = name.lower().replace(" ", "-")
        return self.get_raw(f"/api/spells/{slug}")

    def list_available(self, category: str) -> Any:
        return self._load_file(category)

    def list_categories(self) -> List[str]:
        return list(self.filenames.keys())
