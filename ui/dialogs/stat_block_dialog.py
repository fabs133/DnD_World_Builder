from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser
from PyQt5.QtCore import Qt


class StatBlockDialog(QDialog):
    """
    A read-only dialog that renders a GameEntity (or subclass) as a
    classic D&D 5e-style stat block using HTML/CSS.

    Adapts to the data available:
    - Full subclass instances (Enemy, Character, NamedEnemy) show all fields.
    - Plain GameEntity instances show name, type, stats dict, and inventory.

    :param entity: The entity to display.
    :type entity: GameEntity
    :param parent: Parent widget.
    :type parent: QWidget, optional
    """

    def __init__(self, entity, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.setWindowTitle(f"Stat Block — {entity.name}")
        self.setMinimumSize(420, 500)
        self.resize(440, 650)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setHtml(self._build_html())
        layout.addWidget(self.browser)

    # ------------------------------------------------------------------
    # HTML generation
    # ------------------------------------------------------------------

    def _build_html(self):
        e = self.entity
        parts = [self._css(), '<div class="stat-block">']

        # Portrait image (Phase 2 integration)
        image_path = getattr(e, "image_path", None)
        if image_path:
            parts.append(f'<img src="{image_path}" class="portrait" />')

        # Header
        parts.append(self._header_section(e))

        # Core stats bar (AC / HP / Speed)
        parts.append(self._core_stats_section(e))

        # Ability scores
        parts.append(self._ability_scores_section(e))

        # Properties (saving throws, skills, resistances, etc.)
        parts.append(self._properties_section(e))

        # Actions
        parts.append(self._actions_section(e))

        # Spells
        parts.append(self._spells_section(e))

        # NamedEnemy extras
        parts.append(self._named_enemy_section(e))

        # Inventory / equipment
        parts.append(self._inventory_section(e))

        parts.append("</div>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _header_section(self, e):
        entity_type = getattr(e, "entity_type", "unknown")
        return (
            '<div class="header">'
            f'<h1>{e.name}</h1>'
            f'<p class="subheader">{entity_type}</p>'
            "</div>"
            '<div class="separator"></div>'
        )

    def _core_stats_section(self, e):
        lines = []
        ac = self._get_field(e, "armor_class", "ac")
        hp = self._get_field(e, "hp")
        speed = self._get_field(e, "speed")

        if ac is not None:
            lines.append(f"<b>Armor Class</b> {ac}")
        if hp is not None:
            lines.append(f"<b>Hit Points</b> {hp}")
        if speed is not None:
            lines.append(f"<b>Speed</b> {speed} ft.")

        if not lines:
            return ""
        return '<div class="property-block">' + "<br>".join(lines) + '</div><div class="separator"></div>'

    def _ability_scores_section(self, e):
        ability_names = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        full_names = {
            "STR": "Strength", "DEX": "Dexterity", "CON": "Constitution",
            "INT": "Intelligence", "WIS": "Wisdom", "CHA": "Charisma",
        }

        scores = {}
        stats = getattr(e, "stats", {})
        for abbr in ability_names:
            val = stats.get(abbr) or stats.get(full_names[abbr]) or stats.get(abbr.lower()) or stats.get(full_names[abbr].lower())
            if val is not None:
                scores[abbr] = val

        if not scores:
            return ""

        header_cells = "".join(f"<th>{a}</th>" for a in ability_names if a in scores)
        value_cells = ""
        for a in ability_names:
            if a in scores:
                v = scores[a]
                mod = self._modifier(v)
                value_cells += f"<td>{v} ({mod})</td>"

        return (
            '<div class="abilities">'
            f"<table><tr>{header_cells}</tr>"
            f"<tr>{value_cells}</tr></table>"
            '</div><div class="separator"></div>'
        )

    def _properties_section(self, e):
        lines = []

        saving_throws = getattr(e, "saving_throws", None)
        if saving_throws and isinstance(saving_throws, dict):
            parts = [f"{k} {v:+d}" if isinstance(v, int) else f"{k} {v}" for k, v in saving_throws.items()]
            lines.append(f"<b>Saving Throws</b> {', '.join(parts)}")

        skills = getattr(e, "skills", None)
        if skills and isinstance(skills, dict):
            parts = [f"{k} {v:+d}" if isinstance(v, int) else f"{k} {v}" for k, v in skills.items()]
            lines.append(f"<b>Skills</b> {', '.join(parts)}")

        for label, attr in [
            ("Damage Resistances", "resistances"),
            ("Damage Immunities", "immunities"),
            ("Damage Vulnerabilities", "vulnerabilities"),
            ("Condition Immunities", "condition_immunities"),
        ]:
            val = getattr(e, attr, None)
            if val:
                if isinstance(val, list):
                    lines.append(f"<b>{label}</b> {', '.join(str(v) for v in val)}")
                else:
                    lines.append(f"<b>{label}</b> {val}")

        cr = getattr(e, "challenge_rating", None)
        xp = getattr(e, "xp", None)
        if cr is not None:
            cr_text = f"<b>Challenge</b> {cr}"
            if xp is not None:
                cr_text += f" ({xp:,} XP)"
            lines.append(cr_text)

        if not lines:
            return ""
        return '<div class="property-block">' + "<br>".join(lines) + '</div><div class="separator"></div>'

    def _actions_section(self, e):
        attacks = getattr(e, "attacks", None)
        if not attacks:
            return ""

        lines = ['<div class="section-header">Actions</div>']
        for atk in attacks:
            if isinstance(atk, dict):
                name = atk.get("name", "Attack")
                to_hit = atk.get("to_hit", "")
                damage = atk.get("damage", "")
                hit_str = f"+{to_hit} to hit, " if to_hit else ""
                lines.append(
                    f'<div class="action"><b><i>{name}.</i></b> {hit_str}{damage}</div>'
                )
            else:
                lines.append(f'<div class="action">{atk}</div>')

        return '<div class="actions">' + "\n".join(lines) + "</div>"

    def _spells_section(self, e):
        spells = getattr(e, "spells", None)
        if not spells:
            return ""

        ability = getattr(e, "spellcasting_ability", None)
        lines = ['<div class="section-header">Spellcasting</div>']
        if ability:
            lines.append(f'<div class="property-line"><b>Spellcasting Ability</b> {ability}</div>')

        for spell in spells:
            if isinstance(spell, dict):
                lines.append(f'<div class="action">{spell.get("name", str(spell))}</div>')
            else:
                lines.append(f'<div class="action">{spell}</div>')

        return '<div class="spells">' + "\n".join(lines) + "</div>"

    def _named_enemy_section(self, e):
        from models.entities.named_enemy import NamedEnemy
        if not isinstance(e, NamedEnemy):
            return ""

        parts = []

        if e.backstory:
            parts.append(
                '<div class="section-header">Lore</div>'
                f'<div class="lore">{e.backstory}</div>'
            )

        if e.legendary_actions:
            parts.append('<div class="section-header">Legendary Actions</div>')
            for la in e.legendary_actions:
                if isinstance(la, dict):
                    parts.append(f'<div class="action"><b><i>{la.get("name", "")}.</i></b> {la.get("description", "")}</div>')
                else:
                    parts.append(f'<div class="action">{la}</div>')

        if e.lair_actions:
            parts.append('<div class="section-header">Lair Actions</div>')
            for la in e.lair_actions:
                if isinstance(la, dict):
                    parts.append(f'<div class="action">{la.get("description", str(la))}</div>')
                else:
                    parts.append(f'<div class="action">{la}</div>')

        if e.regional_effects:
            parts.append('<div class="section-header">Regional Effects</div>')
            for re_ in e.regional_effects:
                if isinstance(re_, dict):
                    parts.append(f'<div class="action">{re_.get("description", str(re_))}</div>')
                else:
                    parts.append(f'<div class="action">{re_}</div>')

        return "\n".join(parts)

    def _inventory_section(self, e):
        inventory = getattr(e, "inventory", [])
        if not inventory:
            return ""

        lines = ['<div class="section-header">Inventory</div>']
        for item in inventory:
            lines.append(f"<div class=\"action\">{item}</div>")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_field(self, entity, *attr_names):
        """Try to get a field from the entity or from its stats dict."""
        for name in attr_names:
            val = getattr(entity, name, None)
            if val is not None:
                return val
        stats = getattr(entity, "stats", {})
        for name in attr_names:
            val = stats.get(name) or stats.get(name.lower())
            if val is not None:
                return val
        return None

    @staticmethod
    def _modifier(score):
        """Calculate ability modifier string from a score."""
        try:
            mod = (int(score) - 10) // 2
            return f"+{mod}" if mod >= 0 else str(mod)
        except (ValueError, TypeError):
            return "+0"

    # ------------------------------------------------------------------
    # CSS
    # ------------------------------------------------------------------

    @staticmethod
    def _css():
        return """
        <style>
            .stat-block {
                font-family: 'Segoe UI', 'Noto Sans', sans-serif;
                font-size: 13px;
                color: #1a1a1a;
                background-color: #fdf1dc;
                padding: 14px;
                border: 2px solid #7a200d;
            }
            .portrait {
                max-width: 100%;
                max-height: 200px;
                display: block;
                margin: 0 auto 10px auto;
                border: 1px solid #7a200d;
            }
            .header h1 {
                margin: 0;
                font-size: 22px;
                color: #7a200d;
                font-variant: small-caps;
            }
            .subheader {
                margin: 0 0 4px 0;
                font-style: italic;
                font-size: 12px;
                color: #333;
            }
            .separator {
                height: 2px;
                background: linear-gradient(to right, #7a200d, #e0c8a8, #7a200d);
                margin: 6px 0;
            }
            .property-block {
                line-height: 1.6;
                font-size: 12px;
            }
            .abilities table {
                width: 100%;
                text-align: center;
                border-collapse: collapse;
                font-size: 12px;
            }
            .abilities th {
                color: #7a200d;
                font-weight: bold;
                padding: 2px 8px;
            }
            .abilities td {
                padding: 2px 8px;
            }
            .section-header {
                font-size: 16px;
                color: #7a200d;
                font-variant: small-caps;
                border-bottom: 1px solid #7a200d;
                margin-top: 8px;
                margin-bottom: 4px;
                font-weight: bold;
            }
            .action {
                font-size: 12px;
                margin-bottom: 4px;
                line-height: 1.4;
            }
            .lore {
                font-size: 11px;
                font-style: italic;
                color: #444;
                margin-bottom: 6px;
            }
            .property-line {
                font-size: 12px;
                margin-bottom: 4px;
            }
        </style>
        """
