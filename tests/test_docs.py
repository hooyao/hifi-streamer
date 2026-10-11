"""Check maintained bilingual documentation and source-comment language."""
import ast
import io
import re
import tokenize
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAN = re.compile(r'[\u3400-\u9fff]')


class DocumentationTests(unittest.TestCase):
    def documents(self):
        roots = [ROOT / 'docs', ROOT / 'openspec']
        files = [ROOT / name for name in ('README.md', 'README.zh-CN.md', 'CONTRIBUTING.md',
                                          'CONTRIBUTING.zh-CN.md', 'AGENTS.md', 'AGENTS.zh-CN.md')]
        for root in roots:
            files.extend(root.rglob('*.md'))
        return files

    def test_pairs_and_links(self):
        for path in self.documents():
            with self.subTest(document=str(path.relative_to(ROOT))):
                text = path.read_text(encoding='utf-8')
                parts = list(path.relative_to(ROOT).parts)
                if parts[0] != 'openspec':
                    chinese = path.name.endswith('.zh-CN.md')
                    sibling = path.with_name(path.name.replace('.zh-CN.md', '.md') if chinese
                                             else path.stem + '.zh-CN.md')
                    self.assertTrue(sibling.is_file(), f'missing edition: {sibling}')
                    language_links = re.findall(r'\]\(([^)]+)\)', '\n'.join(text.splitlines()[:5]))
                    self.assertTrue(any((path.parent / link).resolve() == sibling.resolve()
                                        for link in language_links), 'missing reciprocal language link')
                for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                    file_target = target.split('#')[0]
                    if not file_target or re.match(r'^[a-z]+:', file_target):
                        continue
                    self.assertTrue((path.parent / file_target).exists(), f'broken link: {target}')

    def test_openspec_is_english_only(self):
        for path in (ROOT / 'openspec').rglob('*'):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn('zh-CN', path.as_posix())
                self.assertNotIn('translations', path.parts)
                if path.is_file():
                    self.assertIsNone(HAN.search(path.read_text(encoding='utf-8')),
                                      'OpenSpec content must be English')

    def test_python_comments_and_docstrings_are_english(self):
        for directory in ('modules', 'deploy', 'images', 'tests'):
            for path in (ROOT / directory).rglob('*.py'):
                with self.subTest(source=str(path.relative_to(ROOT))):
                    source = path.read_text(encoding='utf-8')
                    for token in tokenize.generate_tokens(io.StringIO(source).readline):
                        if token.type == tokenize.COMMENT:
                            self.assertIsNone(HAN.search(token.string), 'non-English comment')
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                            self.assertIsNone(HAN.search(ast.get_docstring(node) or ''), 'non-English docstring')

    def test_script_and_workflow_comments_are_english(self):
        for directory in ('modules', 'deploy', 'images', 'tests', '.github'):
            for path in (ROOT / directory).rglob('*'):
                if not path.is_file() or path.suffix not in ('.sh', '.lua', '.yaml', '.yml', '.html') and path.name != 'Dockerfile':
                    continue
                with self.subTest(source=str(path.relative_to(ROOT))):
                    source = path.read_text(encoding='utf-8')
                    if path.suffix == '.html':
                        comments = re.findall(r'<!--(.*?)-->', source, re.S)
                    else:
                        marker = '--' if path.suffix == '.lua' else '#'
                        comments = [line for line in source.splitlines() if line.lstrip().startswith(marker)]
                    for comment in comments:
                        self.assertIsNone(HAN.search(comment), 'non-English comment')
