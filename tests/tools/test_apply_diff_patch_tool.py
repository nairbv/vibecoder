import unittest
from vibecoder.tools.apply_diff_patch import ApplyDiffPatchTool
import os
from tempfile import NamedTemporaryFile

class TestApplyDiffPatchTool(unittest.TestCase):
    def setUp(self):
        self.tool = ApplyDiffPatchTool()
        self.target_file = NamedTemporaryFile(delete=False, mode='w+')
        self.target_file.write('Original content.\n')
        self.target_file.close()

    def tearDown(self):
        os.remove(self.target_file.name)

    def test_apply_patch_success(self):
        patch = f'--- {self.target_file.name}\n+++ {self.target_file.name}\n@@ -1 +1 @@\n-Original content.\n+Patched content.\n'
        args = {'patch_text': patch}
        result = self.tool.run(args)
        self.assertIn('patching file', result)
        with open(self.target_file.name, 'r') as f:
            content = f.read()
            self.assertEqual(content.strip(), 'Patched content.')

    def test_apply_patch_failure(self):
        patch = 'invalid patch format'
        args = {'patch_text': patch}
        assert "I can't seem to find a patch in there anywhere" in self.tool.run(args)

if __name__ == '__main__':
    unittest.main()
