"""Validation module for post-run game session result checking."""

from core.testing.validation.validators import (
    ValidationResult,
    validate_no_negative_hp,
    validate_dead_entities_dont_act,
    validate_initiative_order_respected,
    validate_attacks_target_alive_entities,
    validate_damage_consistency,
    validate_session,
)

__all__ = [
    "ValidationResult",
    "validate_no_negative_hp",
    "validate_dead_entities_dont_act",
    "validate_initiative_order_respected",
    "validate_attacks_target_alive_entities",
    "validate_damage_consistency",
    "validate_session",
]
