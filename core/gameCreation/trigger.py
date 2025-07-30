# core/gameCreation/trigger.py
import traceback
import warnings
from models.flow.skill_check import SkillCheck
from models.flow.reaction.reactions_list import ApplyDamage
from registries.trigger_registry import global_trigger_registry
from registries.condition_registry import condition_registry
from registries.reaction_registry import reaction_registry

class Trigger:
    """
    Represents a trigger that listens for an event, checks a condition, and fires a reaction.

    :param event_type: The type of event this trigger listens for.
    :type event_type: str
    :param condition: The condition to check before firing the reaction. Can be a callable or SkillCheck.
    :type condition: callable or SkillCheck
    :param reaction: The reaction to execute if the condition passes.
    :type reaction: callable or object with an execute() method
    :param label: Optional label for the trigger.
    :type label: str, optional
    :param source: Optional source identifier for the trigger.
    :type source: str, optional
    :param flags: Optional dictionary of flags for the trigger.
    :type flags: dict, optional
    :param next_trigger: Optional next trigger to chain after this one.
    :type next_trigger: Trigger, optional
    :param cooldown: Optional cooldown in turns before this trigger can fire again.
    :type cooldown: int, optional
    :param last_fired_turn: Internal use for cooldown tracking.
    :type last_fired_turn: int, optional
    """
    def __init__(self, event_type, condition, reaction, label=None, source=None, flags=None, next_trigger=None, cooldown=None, last_fired_turn=None):
        self.event_type = event_type
        self.condition = condition
        self.reaction = reaction
        self._label = label or f"{event_type}:{reaction.__class__.__name__}"
        self.source = source
        self.flags = flags or {}
        self.next_trigger = next_trigger
        self.cooldown = cooldown
        self._last_fired_turn = None

    @property
    def label(self):
        """
        The label for this trigger.

        :return: The label string.
        :rtype: str
        """
        return self._label

    @label.setter
    def label(self, value):
        """
        Sets the label for this trigger and prints a stack trace if changed.

        :param value: The new label.
        :type value: str
        """
        if value != self._label:
            print(f"\n[⚠️ TRIGGER LABEL CHANGED] {self._label} ➜ {value}")
            print("[Trace] Trigger label modified here:")
            traceback.print_stack(limit=5)
        self._label = value

    def check_and_react(self, event_data):
        """
        Checks the trigger's condition and fires the reaction if appropriate.

        :param event_data: Data about the event that occurred.
        :type event_data: dict
        """
        # 1) Grab turn counter if we have one
        world = event_data.get("world", None)
        ct = None
        if world and hasattr(world, "turn_manager"):
            ct = world.turn_manager.current_turn

        # 2) Cooldown check (only if we have both a cooldown *and* a turn count)
        if self.cooldown and ct is not None and self._last_fired_turn is not None:
            if (ct - self._last_fired_turn) < self.cooldown:
                print(f"[Trigger] {self.label} is on cooldown — skipped.")
                return

        # 3) Figure out success for SkillCheck vs. plain callables
        is_skill = isinstance(self.condition, SkillCheck)
        if is_skill:
            stats = event_data.get("character_stats", {})
            passed = self.condition.attempt(stats)
            # damage reactions invert on a pass
            success = not passed if isinstance(self.reaction, ApplyDamage) else passed
        else:
            success = bool(self.condition(event_data))

        if not success:
            print(f"[Trigger] {self.label} condition not met — skipped.")
            return

        # 4) Fire!
        print(f"[Trigger] {self.label} from {self.source or 'unknown'} activated.")
        self._react(event_data)

        # 5) Record for cooldown (if applicable)
        if ct is not None:
            self._last_fired_turn = ct

        # 6) Chain to next trigger
        if self.next_trigger:
            print(f"[Trigger] Chaining to: {self.next_trigger.label}")
            self.next_trigger.check_and_react(event_data)

    def _react(self, event_data):
        """
        Executes the reaction for this trigger.

        :param event_data: Data about the event that occurred.
        :type event_data: dict
        """
        if callable(self.reaction):
            self.reaction(event_data)
        elif hasattr(self.reaction, 'execute'):
            self.reaction.execute(event_data)

    def to_dict(self):
        """
        Serializes this trigger to a dictionary.

        :return: A dictionary representation of the trigger.
        :rtype: dict
        """
        return {
            "event_type": self.event_type,
            "label": self.label,
            "next_trigger": self.next_trigger.to_dict() if self.next_trigger else None,
            "condition": self._serialize_component(self.condition),
            "reaction": self._serialize_component(self.reaction)
        }

    @classmethod
    def from_dict(cls, data):
        """
        Deserializes a trigger from a dictionary.

        :param data: The dictionary to deserialize from.
        :type data: dict
        :return: The deserialized Trigger instance.
        :rtype: Trigger
        """
        cond = cls._deserialize_component(data["condition"], condition_registry)
        react = cls._deserialize_component(data["reaction"], reaction_registry)
        next_trigger = cls.from_dict(data["next_trigger"]) if data.get("next_trigger") else None
        return cls(
            event_type=data["event_type"],
            condition=cond,
            reaction=react,
            label=data.get("label"),
            next_trigger=next_trigger
        )

    @staticmethod
    def _serialize_component(component):
        """
        Serializes a component (condition or reaction) for storage.

        :param component: The component to serialize.
        :type component: object
        :return: A dictionary representation of the component.
        :rtype: dict
        :raises ValueError: If the component type is unsupported.
        """
        if isinstance(component, SkillCheck):
            return {"type": "SkillCheck", "skill": component.skill_name, "dc": component.dc}
        elif callable(component):
            # Distinguish between plain functions and callable objects
            if hasattr(component, "__name__"):
                return {"type": "function", "name": component.__name__}
            else:
                component_type = component.__class__.__name__
                if hasattr(component, "to_dict"):
                    return {"type": component_type, "args": component.to_dict()}
                else:
                    if not hasattr(component, "args"):
                        warnings.warn(
                            f"[Trigger] Callable component {component_type} missing .to_dict() and .args — using empty args."
                        )
                    return {"type": component_type, "args": getattr(component, "args", {})}
        elif hasattr(component, "__class__") and hasattr(component.__class__, "__name__"):
            component_type = component.__class__.__name__
            if hasattr(component, "to_dict"):
                return {"type": component_type, "args": component.to_dict()}
            else:
                if not hasattr(component, "args"):
                    warnings.warn(
                        f"[Trigger] Component {component_type} missing .to_dict() and .args — using empty args."
                    )
                return {"type": component_type, "args": getattr(component, "args", {})}
        raise ValueError("Unsupported component type for serialization")

    @staticmethod
    def _deserialize_component(data, registry):
        """
        Deserializes a component (condition or reaction) from a dictionary.

        :param data: The dictionary to deserialize from.
        :type data: dict
        :param registry: The registry to use for class lookup.
        :type registry: object
        :return: The deserialized component.
        :rtype: object
        :raises ValueError: If the component type is unknown.
        """
        if data["type"] == "function":
            return global_trigger_registry.get_function(data["name"])
        elif data["type"] == "SkillCheck":
            return SkillCheck(skill_name=data["skill"], dc=data["dc"])
        else:
            cls_ = registry.get_class(data["type"])
            if not cls_:
                raise ValueError(f"[Trigger] Unknown component type: {data['type']}")
            if hasattr(cls_, "from_dict"):
                return cls_.from_dict(data.get("args", {}))
            return cls_(**data.get("args", {}))