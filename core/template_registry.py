import json
from pathlib import Path
from models.templates.entity_template import EntityTemplate
from models.templates.zone_template import ZoneTemplate

class TemplateRegistry:
    def __init__(self):
        self._entity_templates: list[EntityTemplate] = []
        self._zone_templates: list[ZoneTemplate] = []

    def load_builtins(self) -> None:
        base = Path(__file__).resolve().parent / "data_" / "templates"
        self._load_entity_templates(base / "entities", is_builtin=True)
        self._load_zone_templates(base / "zones", is_builtin=True)

    def load_user_templates(self, workspace_path) -> None:
        user_dir = Path(workspace_path) / "_templates"
        self._load_entity_templates(user_dir / "entities", is_builtin=False)
        self._load_zone_templates(user_dir / "zones", is_builtin=False)

    def save_user_template(self, template, workspace_path) -> None:
        user_dir = Path(workspace_path) / "_templates"
        if isinstance(template, EntityTemplate):
            out_dir = user_dir / "entities"
        elif isinstance(template, ZoneTemplate):
            out_dir = user_dir / "zones"
        else:
            raise TypeError(f"Unknown template type: {type(template)}")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{template.template_id}.json"
        path.write_text(json.dumps(template.to_dict(), indent=2), encoding="utf-8")
        # Add to in-memory list if not already there
        if isinstance(template, EntityTemplate):
            self._entity_templates = [t for t in self._entity_templates if t.template_id != template.template_id]
            self._entity_templates.append(template)
        else:
            self._zone_templates = [t for t in self._zone_templates if t.template_id != template.template_id]
            self._zone_templates.append(template)

    def delete_user_template(self, template_id: str, workspace_path) -> None:
        user_dir = Path(workspace_path) / "_templates"
        for sub in ("entities", "zones"):
            path = user_dir / sub / f"{template_id}.json"
            if path.exists():
                path.unlink()
        self._entity_templates = [t for t in self._entity_templates if t.template_id != template_id or t.is_builtin]
        self._zone_templates = [t for t in self._zone_templates if t.template_id != template_id or t.is_builtin]

    def get_entity_templates(self, category=None, tags=None) -> list[EntityTemplate]:
        result = self._entity_templates
        if category:
            result = [t for t in result if t.category == category]
        if tags:
            result = [t for t in result if any(tag in t.tags for tag in tags)]
        return result

    def get_zone_templates(self, tags=None) -> list[ZoneTemplate]:
        result = self._zone_templates
        if tags:
            result = [t for t in result if any(tag in t.tags for tag in tags)]
        return result

    def search(self, query: str) -> dict:
        q = query.lower()
        return {
            "entities": [t for t in self._entity_templates
                         if q in t.name.lower() or q in t.description.lower() or any(q in tag for tag in t.tags)],
            "zones": [t for t in self._zone_templates
                      if q in t.name.lower() or q in t.description.lower() or any(q in tag for tag in t.tags)],
        }

    def _load_entity_templates(self, directory: Path, is_builtin: bool) -> None:
        if not directory.is_dir():
            return
        for f in sorted(directory.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                tmpl = EntityTemplate.from_dict(data)
                tmpl.is_builtin = is_builtin
                self._entity_templates.append(tmpl)
            except Exception:
                pass

    def _load_zone_templates(self, directory: Path, is_builtin: bool) -> None:
        if not directory.is_dir():
            return
        for f in sorted(directory.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                tmpl = ZoneTemplate.from_dict(data)
                tmpl.is_builtin = is_builtin
                self._zone_templates.append(tmpl)
            except Exception:
                pass
