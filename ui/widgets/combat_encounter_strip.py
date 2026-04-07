"""Combat Encounter Strip — animated attack sequence between portraits.

Shows attacker portrait -> dice roll -> impact -> defender portrait + result.
Driven by the 'attack_resolved' EventBus event. Purely presentational.
Uses a queue to sequence multiple rapid attacks.
"""

from __future__ import annotations

import math
import random
from collections import deque
from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPixmap, QFont, QPen, QBrush, QPolygonF

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_STRIP_HEIGHT = 110
_PORTRAIT_SIZE = 80


# ─── Dice Animation Widget ──────────────────────────────────────────

class _DiceWidget(QWidget):
    """Animated d20 — QPainter hexagonal die with tumble + bounce."""

    roll_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 90)
        self._value = 0
        self._display_value = 0
        self._rotation = 0.0
        self._scale = 1.0
        self._color = QColor(220, 210, 190)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._ticks = 0
        self._max_ticks = 25

    def roll(self, final_value: int, is_critical: bool = False) -> None:
        self._value = final_value
        self._ticks = 0
        self._scale = 1.0
        self._color = QColor(255, 215, 0) if is_critical else QColor(220, 210, 190)
        self._timer.start()

    def _tick(self) -> None:
        self._ticks += 1
        if self._ticks < self._max_ticks:
            self._display_value = random.randint(1, 20)
            self._rotation = random.uniform(-20, 20)
        else:
            self._display_value = self._value
            self._rotation = 0
            self._scale = 1.15
            self._timer.stop()
            QTimer.singleShot(120, self._bounce_back)
        self.update()

    def _bounce_back(self) -> None:
        self._scale = 1.0
        self.update()
        QTimer.singleShot(150, self.roll_complete.emit)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        painter.translate(cx, cy)
        painter.rotate(self._rotation)
        painter.scale(self._scale, self._scale)

        size = 34
        painter.setPen(QPen(QColor(80, 70, 50), 2))
        painter.setBrush(QBrush(self._color))
        points = [QPointF(size * math.cos(math.radians(60 * i - 30)),
                          size * math.sin(math.radians(60 * i - 30))) for i in range(6)]
        painter.drawPolygon(QPolygonF(points))

        painter.setPen(QPen(QColor(40, 30, 20)))
        painter.setFont(QFont("Georgia", 16, QFont.Bold))
        painter.drawText(QRectF(-22, -10, 44, 20), Qt.AlignCenter,
                         str(self._display_value) if self._display_value else "")
        painter.end()


# ─── Impact Particle Widget ─────────────────────────────────────────

class _ImpactWidget(QWidget):
    """Particle burst based on damage type."""

    impact_complete = pyqtSignal()

    _TYPE_COLORS = {
        "slashing": QColor(200, 200, 220), "piercing": QColor(180, 180, 200),
        "bludgeoning": QColor(160, 140, 120), "fire": QColor(255, 120, 30),
        "cold": QColor(100, 180, 255), "lightning": QColor(255, 255, 100),
        "weapon": QColor(200, 180, 150),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(70, 70)
        self._particles: list[dict] = []
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._ticks = 0

    def play(self, damage_type: str) -> None:
        self._ticks = 0
        color = self._TYPE_COLORS.get(damage_type.lower(), QColor(255, 200, 100))
        cx, cy = 35, 35
        self._particles = []
        for i in range(8):
            angle = math.radians(i * 45 + random.uniform(-20, 20))
            speed = random.uniform(2.5, 5.5)
            self._particles.append({
                "x": cx, "y": cy,
                "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
                "opacity": 1.0, "size": random.uniform(3, 8), "color": color,
            })
        self._timer.start()

    def _tick(self) -> None:
        self._ticks += 1
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["opacity"] = max(0, 1.0 - self._ticks / 15)
        self.update()
        if self._ticks >= 15:
            self._timer.stop()
            self._particles.clear()
            self.update()
            self.impact_complete.emit()

    def paintEvent(self, event):
        if not self._particles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for p in self._particles:
            c = QColor(p["color"])
            c.setAlphaF(max(0, min(1, p["opacity"])))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QRectF(p["x"] - p["size"]/2, p["y"] - p["size"]/2,
                                       p["size"], p["size"]))
        painter.end()


# ─── Main Encounter Strip ───────────────────────────────────────────

class CombatEncounterStrip(QWidget):
    """Horizontal strip showing attack sequences between portraits.

    Subscribes to 'attack_resolved' event. Queues attacks to
    prevent overlap. Auto-hides between attacks.
    """

    encounter_animation_complete = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Fixed height always reserved — content is shown/hidden, not the strip itself
        self.setFixedHeight(_STRIP_HEIGHT)
        self.setStyleSheet(
            "CombatEncounterStrip { background: rgba(20, 18, 15, 220); }")
        self._subscribed = False
        self._animating = False
        self._turn_controller = None  # Set by PlaySessionDialog
        self._queue: deque[dict] = deque()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        # Attacker column
        atk_col = QVBoxLayout()
        atk_col.setSpacing(2)
        self._atk_portrait = QLabel()
        self._atk_portrait.setFixedSize(_PORTRAIT_SIZE, _PORTRAIT_SIZE)
        self._atk_portrait.setAlignment(Qt.AlignCenter)
        self._atk_portrait.setStyleSheet(
            "border: 2px solid #4a90d9; border-radius: 4px; background: #1a1a2a;")
        self._atk_name = QLabel()
        self._atk_name.setStyleSheet("color: #8ac; font-size: 9px; font-weight: bold;")
        self._atk_name.setAlignment(Qt.AlignCenter)
        atk_col.addWidget(self._atk_portrait, alignment=Qt.AlignCenter)
        atk_col.addWidget(self._atk_name)
        layout.addLayout(atk_col)

        # Center: dice + result
        center = QVBoxLayout()
        center.setSpacing(2)

        dice_row = QHBoxLayout()
        dice_row.setSpacing(4)
        self._dice = _DiceWidget()
        self._impact = _ImpactWidget()
        dice_row.addStretch()
        dice_row.addWidget(self._dice)
        dice_row.addWidget(self._impact)
        dice_row.addStretch()
        center.addLayout(dice_row)

        self._result_label = QLabel()
        self._result_label.setAlignment(Qt.AlignCenter)
        self._result_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #ddd;")
        center.addWidget(self._result_label)

        self._damage_label = QLabel()
        self._damage_label.setAlignment(Qt.AlignCenter)
        self._damage_label.setStyleSheet("font-size: 11px; color: #c88;")
        center.addWidget(self._damage_label)

        layout.addLayout(center, stretch=1)

        # Defender column
        def_col = QVBoxLayout()
        def_col.setSpacing(2)
        self._def_portrait = QLabel()
        self._def_portrait.setFixedSize(_PORTRAIT_SIZE, _PORTRAIT_SIZE)
        self._def_portrait.setAlignment(Qt.AlignCenter)
        self._def_portrait.setStyleSheet(
            "border: 2px solid #d94a4a; border-radius: 4px; background: #2a1a1a;")
        self._def_name = QLabel()
        self._def_name.setStyleSheet("color: #c88; font-size: 9px; font-weight: bold;")
        self._def_name.setAlignment(Qt.AlignCenter)
        def_col.addWidget(self._def_portrait, alignment=Qt.AlignCenter)
        def_col.addWidget(self._def_name)
        layout.addLayout(def_col)

        # Start with all content hidden
        self._collapse()

        # Subscribe
        try:
            from core.gameCreation.event_bus import EventBus
            EventBus.subscribe("attack_resolved", self._on_attack_resolved)
            self._subscribed = True
        except Exception:
            pass

        # Single connection for dice completion
        self._dice.roll_complete.connect(self._on_dice_complete)
        self._impact.impact_complete.connect(self._on_impact_complete)
        self._current_data: dict = {}

    # ─── Portrait loading ───────────────────────────────────────

    def _load_portrait(self, entity: Any) -> QPixmap:
        path = getattr(entity, "image_path", None)
        if path:
            p = Path(path)
            if not p.is_absolute():
                p = _PROJECT_ROOT / p
            if p.exists():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    return pm.scaled(_PORTRAIT_SIZE, _PORTRAIT_SIZE,
                                     Qt.KeepAspectRatioByExpanding,
                                     Qt.SmoothTransformation)
        pm = QPixmap(_PORTRAIT_SIZE, _PORTRAIT_SIZE)
        pm.fill(QColor(60, 55, 50))
        painter = QPainter(pm)
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.setFont(QFont("Georgia", 18, QFont.Bold))
        name = getattr(entity, "name", "?")
        initials = "".join(w[0].upper() for w in name.split()[:2])
        painter.drawText(pm.rect(), Qt.AlignCenter, initials)
        painter.end()
        return pm

    # ─── Event handling with queue ──────────────────────────────

    def _on_attack_resolved(self, data: dict) -> None:
        # Only keep the latest attack — discard any queued ones
        self._queue.clear()
        self._queue.append(data)
        if not self._animating:
            self._play_next()

    def _play_next(self) -> None:
        if not self._queue:
            self._animating = False
            self._collapse()
            return

        self._animating = True
        self._current_data = self._queue.popleft()
        data = self._current_data

        attacker = data.get("attacker")
        defender = data.get("defender")
        if not attacker or not defender:
            self._play_next()
            return

        # Load portraits and names
        self._atk_portrait.setPixmap(self._load_portrait(attacker))
        self._def_portrait.setPixmap(self._load_portrait(defender))
        self._atk_name.setText(getattr(attacker, "name", "?"))
        self._def_name.setText(getattr(defender, "name", "?"))
        self._result_label.setText("")
        self._damage_label.setText("")

        # Expand strip
        self._expand()

        # Start dice roll after strip is visible
        QTimer.singleShot(200, self._start_dice_roll)

    def _start_dice_roll(self) -> None:
        data = self._current_data
        is_crit = data.get("is_critical", False)
        self._dice.roll(data.get("attack_roll", 0), is_critical=is_crit)

    def _on_dice_complete(self) -> None:
        """Called when dice animation finishes — show hit/miss result."""
        data = self._current_data
        hit = data.get("hit", False)
        is_crit = data.get("is_critical", False)

        if hit:
            if is_crit:
                self._result_label.setText("CRITICAL HIT!")
                self._result_label.setStyleSheet(
                    "font-size: 15px; font-weight: bold; color: #ffd700;")
            else:
                self._result_label.setText("HIT!")
                self._result_label.setStyleSheet(
                    "font-size: 13px; font-weight: bold; color: #4ad94a;")

            # Damage text
            total = data.get("damage_total", 0)
            individual = data.get("individual_dice", [])
            expr = data.get("damage_expr", "")
            dice_str = "+".join(str(d) for d in individual) if individual else str(total)
            self._damage_label.setText(f"{total} damage ({dice_str})")

            # Play impact animation
            self._impact.play(data.get("damage_type", "weapon"))
        else:
            self._result_label.setText("MISS")
            self._result_label.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #777;")
            self._damage_label.setText("")
            # No impact animation on miss — go straight to hold
            QTimer.singleShot(1200, self._finish_current)

    def _on_impact_complete(self) -> None:
        """Called after impact particles fade — hold result then advance."""
        QTimer.singleShot(1200, self._finish_current)

    def _finish_current(self) -> None:
        """Finish current attack animation — collapse and release the turn gate."""
        self._animating = False
        self._collapse()
        self.encounter_animation_complete.emit()
        # Release the step gate so the turn controller can advance
        if self._turn_controller and hasattr(self._turn_controller, 'release_step'):
            self._turn_controller.release_step()

    # ─── Expand / Collapse ──────────────────────────────────────

    def _expand(self) -> None:
        """Show strip content with dark background."""
        self.setStyleSheet(
            "CombatEncounterStrip { background: rgba(20, 18, 15, 220); }")
        self._atk_portrait.show()
        self._def_portrait.show()
        self._atk_name.show()
        self._def_name.show()
        self._dice.show()
        self._impact.show()
        self._result_label.show()
        self._damage_label.show()

    def _collapse(self) -> None:
        """Hide strip content — transparent background when idle."""
        self.setStyleSheet(
            "CombatEncounterStrip { background: transparent; }")
        self._atk_portrait.hide()
        self._def_portrait.hide()
        self._atk_name.hide()
        self._def_name.hide()
        self._dice.hide()
        self._impact.hide()
        self._result_label.hide()
        self._damage_label.hide()

    # ─── Cleanup ────────────────────────────────────────────────

    def cleanup(self) -> None:
        if self._subscribed:
            try:
                from core.gameCreation.event_bus import EventBus
                EventBus.unsubscribe("attack_resolved", self._on_attack_resolved)
            except Exception:
                pass
