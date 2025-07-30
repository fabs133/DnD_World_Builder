import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime


class ExportManager:
    """
    Manages the export of map bundles, including associated profiles and media, into a zip archive.
    :param export_dir: Directory where exported bundles will be saved. Defaults to "exports".
    :type export_dir: str
    """
    def __init__(self, export_dir="exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)

    def export_bundle(self, map_path: Path, profile_dir: Path = None, media_dir: Path = None):
        # Load map to extract metadata
        with open(map_path, "r", encoding="utf-8") as f:
            map_data = json.load(f)

        meta = map_data.get("meta", {})
        map_name = meta.get("map_name", map_path.stem)
        author = meta.get("author", "Unknown")

        export_time = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        bundle_name = f"{map_name}_{export_time}.zip"
        bundle_path = self.export_dir / bundle_name

        manifest = {
            "bundle_version": "1.0",
            "map_name": map_name,
            "author": author,
            "exported": export_time,
            "files": ["map.json"]
        }

        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Include map
            zf.write(map_path, arcname="map.json")

            # Include profiles
            if profile_dir and profile_dir.exists():
                for file in profile_dir.glob("**/*"):
                    if file.is_file():
                        zf.write(file, arcname=f"profiles/{file.relative_to(profile_dir)}")
                manifest["files"].append("profiles/")

            # Include media
            if media_dir and media_dir.exists():
                for file in media_dir.glob("**/*"):
                    if file.is_file():
                        zf.write(file, arcname=f"media/{file.relative_to(media_dir)}")
                manifest["files"].append("media/")

            # Add manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        return bundle_path
