import unittest, pathlib

class TestClaudeMD(unittest.TestCase):
    def setUp(self):
        self.path = pathlib.Path(__file__).resolve().parents[1] / 'CLAUDE.md'
        self.content = self.path.read_text(encoding='utf-8')
    def test_essential_commands_section(self):
        self.assertIn('## Essential Commands', self.content)
    def test_exit_code_contract(self):
        self.assertIn('non-zero exit code', self.content)

if __name__ == '__main__':
    unittest.main()
