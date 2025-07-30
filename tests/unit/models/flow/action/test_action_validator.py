import pytest

from models.flow.action.action_validator import ActionValidator

class NoValidateAction:
    pass

class BoolAction:
    def __init__(self, result):
        self._result = result
    def validate(self, game_state=None):
        return self._result

class ExceptionAction:
    def validate(self, game_state=None):
        raise ValueError("invalid action")

def test_missing_validate_method_raises():
    action = NoValidateAction()
    with pytest.raises(AttributeError) as ei:
        ActionValidator.validate(action)
    msg = str(ei.value)
    assert "has no validate() method" in msg
    assert "NoValidateAction" in msg

@pytest.mark.parametrize("result", [True, False])
def test_validate_returns_boolean(result):
    action = BoolAction(result)
    # with and without a game_state argument
    assert ActionValidator.validate(action) is result
    assert ActionValidator.validate(action, game_state={"foo": "bar"}) is result

def test_validate_catches_exception_and_returns_false(capsys):
    action = ExceptionAction()
    outcome = ActionValidator.validate(action)
    assert outcome is False

    # Should print the rejection message
    captured = capsys.readouterr()
    assert "[Validator] Action rejected: invalid action" in captured.out
