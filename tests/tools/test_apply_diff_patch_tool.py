import asyncio
import os
import unittest
from tempfile import NamedTemporaryFile

from vibecoder.tools.apply_diff_patch import ApplyDiffPatchTool


class TestApplyDiffPatchTool(unittest.TestCase):
    def setUp(self):
        self.tool = ApplyDiffPatchTool()
        self.target_file = NamedTemporaryFile(delete=False, mode="w+")
        self.target_file.write("Original content.\n")
        self.target_file.close()

    def tearDown(self):
        os.remove(self.target_file.name)

    def test_apply_patch_success(self):
        patch = (
            f"--- {self.target_file.name}\n"
            f"+++ {self.target_file.name}\n"
            "@@ -1 +1 @@\n"
            "-Original content.\n"
            "+Patched content.\n"
        )
        args = {"patch_text": patch}
        # Run the async tool
        result = asyncio.run(self.tool.run(args))
        # Confirm patch output indicates success
        self.assertIn("patching file", result)
        # Verify file was modified
        with open(self.target_file.name, "r") as f:
            content = f.read()
            self.assertEqual(content.strip(), "Patched content.")

    def test_apply_patch_failure(self):
        patch = "invalid patch format"
        args = {"patch_text": patch}
        # Run the async tool
        result = asyncio.run(self.tool.run(args))
        # Expect failure indication from patch command
        self.assertIn("[Patch application failed]", result)


if __name__ == "__main__":
    unittest.main()
