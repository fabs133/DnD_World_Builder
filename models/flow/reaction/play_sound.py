from models.flow.reaction.reactions import Reactions


class PlaySound(Reactions):
    """
    Reaction that plays a sound file when triggered.

    Integrates with the AudioPlayer singleton to play audio effects
    as part of the trigger/reaction system.

    :param sound_file: Path to the sound file to play (relative to workspace).
    :type sound_file: str
    """

    def __init__(self, sound_file: str):
        self.sound_file = sound_file

    def __call__(self, event_data):
        """
        Play the configured sound file.

        :param event_data: Dictionary containing event information.
        :type event_data: dict
        """
        from core.audio_player import AudioPlayer
        AudioPlayer.instance().play(self.sound_file)

    def to_dict(self):
        """
        Serialize the reaction to a dictionary.

        :return: Dictionary representation of the reaction.
        :rtype: dict
        """
        return {
            "type": "PlaySound",
            "sound_file": self.sound_file,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create a PlaySound reaction from a dictionary.

        :param data: Dictionary containing 'sound_file'.
        :type data: dict
        :return: An instance of PlaySound.
        :rtype: PlaySound
        """
        return cls(sound_file=data["sound_file"])
