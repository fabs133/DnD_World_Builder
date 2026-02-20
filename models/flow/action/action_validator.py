from core.logger import app_logger

class ActionValidator:
    @staticmethod
    def validate(action, game_state=None):
        """
        Validate if the action can be performed.
        You could expand this with rulebooks, conditions, or custom logic.

        :param action: Action instance
        :param game_state: Optional context, like current battlefield state
        :return: Boolean
        """
        if not hasattr(action, "validate"):
            raise AttributeError(f"{action} has no validate() method.")

        # The validate method should raise or return False if invalid.
        try:
            return action.validate(game_state)
        except Exception as e:
            app_logger.warning(f"[Validator] Action rejected: {e}")
            return False