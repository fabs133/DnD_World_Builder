import pytest
from models.flow.reaction.play_sound import PlaySound


def test_play_sound_init():
    ps = PlaySound(sound_file="media/audio/trap.mp3")
    assert ps.sound_file == "media/audio/trap.mp3"


def test_play_sound_to_dict():
    ps = PlaySound(sound_file="media/audio/ambience.wav")
    d = ps.to_dict()
    assert d == {"type": "PlaySound", "sound_file": "media/audio/ambience.wav"}


def test_play_sound_from_dict():
    data = {"type": "PlaySound", "sound_file": "media/audio/door.ogg"}
    ps = PlaySound.from_dict(data)
    assert ps.sound_file == "media/audio/door.ogg"


def test_play_sound_round_trip():
    original = PlaySound(sound_file="media/audio/fire.mp3")
    d = original.to_dict()
    restored = PlaySound.from_dict(d)
    assert restored.sound_file == original.sound_file


def test_play_sound_registered_in_registry():
    from registries.reaction_registry import reaction_registry
    cls = reaction_registry.get_class("PlaySound")
    assert cls is PlaySound


def test_play_sound_callable(monkeypatch):
    """PlaySound.__call__ should invoke AudioPlayer.play()."""
    played = {}

    class FakeAudioPlayer:
        @classmethod
        def instance(cls):
            return cls()

        def play(self, path):
            played["path"] = path

    import core.audio_player as ap_mod
    monkeypatch.setattr(ap_mod, "AudioPlayer", FakeAudioPlayer)

    ps = PlaySound(sound_file="test.mp3")
    ps({"target": None})
    assert played["path"] == "test.mp3"
