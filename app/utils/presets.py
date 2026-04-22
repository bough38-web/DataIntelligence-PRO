import os
import json
from pathlib import Path
from app.utils.common import JsonStore

class PresetManager:
    def __init__(self, category="default"):
        # Use a hidden directory in the user's home folder for persistent storage
        self.base_dir = Path.home() / ".dataintelligence_pro" / "presets" / category
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.store = JsonStore(self.base_dir / "index.json", default={"presets": {}})

    @property
    def preset_dir(self):
        # Compatibility property
        return self.base_dir

    def save_preset(self, name, data):
        index = self.store.load()
        index["presets"][name] = data
        self.store.save(index)
        
        # Also save as individual file for transparency
        preset_file = self.preset_dir / f"{name}.json"
        with open(preset_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_preset(self, name):
        index = self.store.load()
        return index["presets"].get(name)

    def list_presets(self):
        index = self.store.load()
        return list(index["presets"].keys())

    def delete_preset(self, name):
        index = self.store.load()
        if name in index["presets"]:
            del index["presets"][name]
            self.store.save(index)
            preset_file = self.preset_dir / f"{name}.json"
            if preset_file.exists():
                preset_file.unlink()
