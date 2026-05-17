import yaml
import os
from pathlib import Path

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Get folder paths from config
folders_to_clear = [
    config['lookups_folder'],
    config['games_folder'],
    config['multiplayer_modes_folder'],
    config['junctions_folder'],
    config['covers_folder'],
    'logging'
]

# Clear all files in specified folders
for folder in folders_to_clear:
    folder_path = Path(folder)
    if folder_path.exists():
        for file in folder_path.glob('*'):
            if file.is_file():
                file.unlink()
                print(f"Deleted: {file}")
    else:
        print(f"Folder not found: {folder}")

