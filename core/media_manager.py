import shutil
import uuid
from pathlib import Path


class MediaManager:
    """
    Manages media files (images, audio) within a scenario workspace.

    Handles copying source files into the workspace's media directory and
    resolving relative media paths to absolute paths.

    :param workspace_path: Root path of the scenario workspace.
    :type workspace_path: str or Path
    """

    def __init__(self, workspace_path):
        self.workspace = Path(workspace_path)
        self.images_dir = self.workspace / "media" / "images"
        self.audio_dir = self.workspace / "media" / "audio"

    def import_image(self, source_path):
        """
        Copy an image file into the workspace's media/images directory.

        If a file with the same name already exists, a unique suffix is added.

        :param source_path: Path to the source image file.
        :type source_path: str or Path
        :return: Relative path from the workspace root (e.g. ``media/images/goblin.png``).
        :rtype: str
        """
        return self._import_file(source_path, self.images_dir)

    def import_audio(self, source_path):
        """
        Copy an audio file into the workspace's media/audio directory.

        If a file with the same name already exists, a unique suffix is added.

        :param source_path: Path to the source audio file.
        :type source_path: str or Path
        :return: Relative path from the workspace root (e.g. ``media/audio/ambience.mp3``).
        :rtype: str
        """
        return self._import_file(source_path, self.audio_dir)

    def resolve_path(self, relative_path):
        """
        Resolve a relative media path to an absolute path within the workspace.

        :param relative_path: Relative path as stored in model data.
        :type relative_path: str or Path
        :return: Absolute path to the media file.
        :rtype: Path
        """
        return self.workspace / relative_path

    def _import_file(self, source_path, target_dir):
        """
        Copy a file into *target_dir*, creating the directory if needed.

        :param source_path: Path to the source file.
        :type source_path: str or Path
        :param target_dir: Destination directory within the workspace.
        :type target_dir: Path
        :return: Relative path from the workspace root.
        :rtype: str
        """
        source = Path(source_path)
        target_dir.mkdir(parents=True, exist_ok=True)

        dest = target_dir / source.name
        if dest.exists() and not self._files_identical(source, dest):
            # Add a unique suffix to avoid collisions
            unique = uuid.uuid4().hex[:8]
            dest = target_dir / f"{source.stem}_{unique}{source.suffix}"

        if not dest.exists():
            shutil.copy2(source, dest)

        return str(dest.relative_to(self.workspace))

    @staticmethod
    def _files_identical(a, b):
        """
        Check whether two files have the same content by comparing size and bytes.

        :param a: First file path.
        :type a: Path
        :param b: Second file path.
        :type b: Path
        :return: True if the files are identical, False otherwise.
        :rtype: bool
        """
        if a.stat().st_size != b.stat().st_size:
            return False
        return a.read_bytes() == b.read_bytes()
