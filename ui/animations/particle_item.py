"""Universal particle renderer — drives all 6 particle categories."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass

from PyQt5.QtCore import QPointF, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QRadialGradient
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene

from ui.animations.config import ParticlePreset, ParticleMotion, EmissionShape


@dataclass
class Particle:
    """Runtime state of a single particle."""
    x: float
    y: float
    vx: float
    vy: float
    size: float
    life: float           # 0.0 (just born) to 1.0 (about to die)
    max_life_ms: float
    elapsed_ms: float = 0.0
    angle: float = 0.0    # For ORBIT motion


class ParticleItem(QGraphicsItem):
    """
    Universal particle renderer. Drives all 6 categories.

    Usage:
        item = ParticleItem(preset, center_pos)
        scene.addItem(item)
        item.start()          # Begins emission + update timer
        item.stop()           # Stops emission, existing particles fade out
        # For IMPACT: auto-stops after one burst
        # For continuous: call stop() when lifecycle ends
    """

    UPDATE_INTERVAL_MS = 33  # ~30 fps

    def __init__(self, preset: ParticlePreset, center: QPointF = QPointF(0, 0),
                 parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self._preset = preset
        self._center = center
        self._particles: list[Particle] = []
        self._emitting = False
        self._emit_accumulator = 0.0

        self.setPos(center)
        self.setZValue(preset.layer)

        # Bounding rect cache (expanded for glow)
        extent = preset.emission_radius + max(preset.size_start, preset.size_end) * 3
        self._bounds = QRectF(-extent, -extent, extent * 2, extent * 2)

        self._timer = QTimer()
        self._timer.timeout.connect(self._update)

    def start(self):
        """Begin emitting particles."""
        self._emitting = True
        if self._preset.emission_rate == 0:
            # Burst mode: emit all at once
            self._emit_burst(self._preset.count)
            self._emitting = False  # One-shot
        self._timer.start(self.UPDATE_INTERVAL_MS)

    def stop(self):
        """Stop emitting. Existing particles fade out naturally."""
        self._emitting = False

    def is_alive(self) -> bool:
        """True if still emitting or has living particles."""
        return self._emitting or len(self._particles) > 0

    def set_center(self, pos: QPointF):
        """Update emission center (for tracking a moving entity)."""
        self.setPos(pos)

    def _emit_burst(self, count: int):
        """Spawn count particles at once."""
        for _ in range(count):
            self._particles.append(self._spawn_particle())

    def _spawn_particle(self) -> Particle:
        """Create one particle based on preset emission config."""
        p = self._preset
        rng = random.random

        # Position within emission shape
        ox, oy = 0.0, 0.0
        if p.emission_shape == EmissionShape.POINT:
            pass
        elif p.emission_shape == EmissionShape.DISC:
            angle = rng() * math.tau
            r = rng() ** 0.5 * p.emission_radius  # sqrt for uniform distribution
            ox, oy = math.cos(angle) * r, math.sin(angle) * r
        elif p.emission_shape == EmissionShape.RING:
            angle = rng() * math.tau
            ox, oy = math.cos(angle) * p.emission_radius, math.sin(angle) * p.emission_radius
        elif p.emission_shape == EmissionShape.CONE:
            half = math.radians(p.emission_angle / 2)
            base = math.radians(p.direction_deg)
            angle = base + (rng() - 0.5) * 2 * half
            r = rng() * p.emission_radius
            ox, oy = math.cos(angle) * r, math.sin(angle) * r
        elif p.emission_shape == EmissionShape.LINE:
            ox = (rng() - 0.5) * 2 * p.emission_radius
            oy = 0.0

        # Velocity based on motion type
        speed = p.speed + (rng() - 0.5) * 2 * p.speed_variance
        vx, vy = 0.0, 0.0
        if p.motion == ParticleMotion.RISE:
            vx = (rng() - 0.5) * speed * 0.3
            vy = -speed
        elif p.motion == ParticleMotion.FALL:
            vx = (rng() - 0.5) * speed * 0.2
            vy = speed
        elif p.motion == ParticleMotion.EXPLODE:
            angle = rng() * math.tau
            vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
        elif p.motion == ParticleMotion.DRIFT:
            angle = rng() * math.tau
            vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
        elif p.motion in (ParticleMotion.ORBIT, ParticleMotion.FOLLOW, ParticleMotion.STATIC):
            pass  # Handled in update

        max_life = p.lifetime_ms + (rng() - 0.5) * 2 * p.lifetime_variance_ms
        max_life = max(50, max_life)

        return Particle(
            x=ox, y=oy, vx=vx, vy=vy,
            size=p.size_start,
            life=0.0, max_life_ms=max_life,
            angle=rng() * math.tau if p.motion == ParticleMotion.ORBIT else 0.0,
        )

    def _update(self):
        """Advance simulation one frame."""
        dt = self.UPDATE_INTERVAL_MS
        p = self._preset

        # Continuous emission
        if self._emitting and p.emission_rate > 0:
            self._emit_accumulator += p.emission_rate * (dt / 1000.0)
            while self._emit_accumulator >= 1.0 and len(self._particles) < p.count:
                self._particles.append(self._spawn_particle())
                self._emit_accumulator -= 1.0

        # Update particles
        dead = []
        for i, pt in enumerate(self._particles):
            pt.elapsed_ms += dt
            pt.life = min(1.0, pt.elapsed_ms / pt.max_life_ms)

            if pt.life >= 1.0:
                dead.append(i)
                continue

            # Motion
            if p.motion == ParticleMotion.ORBIT:
                pt.angle += p.speed * 0.05
                r = p.emission_radius
                pt.x = math.cos(pt.angle) * r
                pt.y = math.sin(pt.angle) * r
            else:
                pt.vx *= (1.0 - p.drag)
                pt.vy *= (1.0 - p.drag)
                pt.vy += p.gravity
                pt.x += pt.vx
                pt.y += pt.vy

            # Interpolate size
            pt.size = p.size_start + (p.size_end - p.size_start) * pt.life

        # Remove dead
        for i in reversed(dead):
            self._particles.pop(i)

        # Self-destruct if done
        if not self.is_alive():
            self._timer.stop()
            scene = self.scene()
            if scene:
                scene.removeItem(self)
            return

        self.update()  # Trigger repaint

    def boundingRect(self) -> QRectF:
        return self._bounds

    def paint(self, painter: QPainter, option, widget=None):
        """Render all living particles."""
        p = self._preset
        painter.setPen(0)  # No stroke

        c_start = QColor(p.color_start)
        c_end = QColor(p.color_end) if p.color_end else c_start

        for pt in self._particles:
            t = pt.life
            # Interpolate color
            r = c_start.red()   + (c_end.red()   - c_start.red())   * t
            g = c_start.green() + (c_end.green() - c_start.green()) * t
            b = c_start.blue()  + (c_end.blue()  - c_start.blue())  * t

            # Interpolate opacity
            a = p.opacity_start + (p.opacity_end - p.opacity_start) * t

            color = QColor(int(r), int(g), int(b), int(a * 255))

            if p.glow and pt.size > 1.5:
                # Radial gradient for soft glow
                grad = QRadialGradient(pt.x, pt.y, pt.size * 2)
                grad.setColorAt(0, color)
                color_t = QColor(color)
                color_t.setAlpha(0)
                grad.setColorAt(1, color_t)
                painter.setBrush(grad)
                painter.drawEllipse(QPointF(pt.x, pt.y), pt.size * 2, pt.size * 2)
            else:
                painter.setBrush(color)
                painter.drawEllipse(QPointF(pt.x, pt.y), pt.size, pt.size)
