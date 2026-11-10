"""API generation stays independent of PDF configuration during rebuilds."""

import runpy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs_gen_files.editor import FilesEditor

ROOT = Path(__file__).resolve().parents[3]
GENERATOR = ROOT / "doc/manual/docs/api/generate.py"


class ApiGenerationTest(unittest.TestCase):
    def run_generator(self, environment):
        with TemporaryDirectory() as directory:
            # Rebuilds must work without any PDF hook configuration.
            config = MkDocsConfig()
            # MkDocs' inherited constructor is annotated as the base Config.
            assert isinstance(config, MkDocsConfig)
            config.load_dict(
                {
                    "docs_dir": str(ROOT / "doc/manual/docs"),
                    "site_dir": directory,
                    "use_directory_urls": True,
                    "extra": {},
                }
            )
            module = ROOT / "src/robot/api/__init__.py"
            with (
                FilesEditor(Files([]), config, directory) as editor,
                patch.dict("os.environ", environment, clear=True),
                patch.object(Path, "rglob", return_value=[module]),
            ):
                runpy.run_path(str(GENERATOR))
            return {file.src_uri: file.content_string for file in editor.files}

    def test_rebuild_with_missing_hook_setting_defaults_to_fast_preview(self):
        files = self.run_generator({})
        self.assertEqual(set(files), {"api/index.md", "api/nav.md"})
        self.assertIn("Local preview", files["api/index.md"])
        self.assertIn("`robot.api`", files["api/index.md"])
        self.assertNotIn("[robot.api][]", files["api/index.md"])

    def test_explicit_api_build_works_without_pdf_hook_setting(self):
        files = self.run_generator({"GENERATE_API_DOCS": "1"})
        self.assertIn("api/robot/api/index.md", files)
        self.assertNotIn("api/index.md", files)
        self.assertIn("# ::: robot.api", files["api/robot/api/index.md"])

    def test_legacy_disable_override_also_works_during_rebuild(self):
        files = self.run_generator(
            {"GENERATE_API_DOCS": "1", "DO_NOT_GENERATE_API_DOCS": "1"}
        )
        self.assertNotIn("api/robot/api/index.md", files)
        self.assertIn("Local preview", files["api/index.md"])


if __name__ == "__main__":
    unittest.main()
