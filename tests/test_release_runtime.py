from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_labor_atlas.occupation_context import load_alias_registry
from ai_labor_atlas.resources import resource_path
from ai_labor_atlas.runtime import config_path, data_root


ROOT = Path(__file__).resolve().parents[1]


class ReleaseRuntimeTests(unittest.TestCase):
    def test_packaged_resources_match_source_config(self):
        for name in ("source_registry.json", "occupation_aliases_en.json"):
            self.assertEqual(
                resource_path(name).read_text(encoding="utf-8"),
                (ROOT / "config" / name).read_text(encoding="utf-8"),
            )

    def test_packaged_config_is_available(self):
        registry = json.loads(
            config_path("source_registry.json").read_text(encoding="utf-8")
        )
        self.assertTrue(registry["sources"])
        self.assertTrue(load_alias_registry())

    def test_data_root_defaults_to_current_working_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("AI_LABOR_ATLAS_DATA_DIR", None)
                with patch("pathlib.Path.cwd", return_value=Path(temp)):
                    self.assertEqual(data_root(), Path(temp) / "data")

    def test_data_root_honors_environment_override(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(
                os.environ, {"AI_LABOR_ATLAS_DATA_DIR": temp}, clear=False
            ):
                self.assertEqual(data_root(), Path(temp).resolve())


if __name__ == "__main__":
    unittest.main()
