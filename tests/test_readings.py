import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from readings import build_readings


class ReadingBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.material = self.root / 'content/example'
        (self.material / 'content').mkdir(parents=True)
        (self.root / 'docs/assets').mkdir(parents=True)
        (self.root / 'src').mkdir()
        source = Path(__file__).resolve().parents[1] / 'src'
        for name in ['reader.html', 'reader.css', 'reader.js', 'theme.css', 'theme.js']:
            shutil.copy2(source / name, self.root / 'src' / name)
        self.catalog = [{'id': 'example', 'url': 'https://example.com/read/example/'}]

    def manifest(self, pages, fmt='interview'):
        (self.material / 'reading.json').write_text(json.dumps({
            'id': 'example', 'title': '读物', 'kind': '文章', 'format': fmt, 'pages': pages}))

    def test_article_is_readable_at_root_and_search_covers_the_ending(self):
        self.manifest([{'id': '001', 'title': '完整访谈', 'markdown': 'content/001.md'}])
        (self.material / 'content/001.md').write_text('# 完整访谈\n\n[TOC]\n\n## 开场\n\n内容。\n\n## 结尾\n\n末尾的独立观点。')
        indexes = build_readings(self.root, self.catalog)
        page = self.root / 'docs/read/example/index.html'
        self.assertTrue(page.is_file())
        self.assertIn('末尾的独立观点', page.read_text())
        self.assertIn('末尾的独立观点', indexes['example'][0]['text'])
        self.assertEqual(indexes['example'][0]['route'], './')
        self.assertIn('data-index="search.json?v=', page.read_text())
        self.assertIn('../../assets/reader.css?', page.read_text())
        self.assertIn('../../assets/theme.js?', page.read_text())
        self.assertIn('class="theme-toggle"', page.read_text())

    def test_multiple_pages_rewrite_markdown_links_images_and_prev_next(self):
        self.manifest([{'id': '001', 'title': '第一节', 'markdown': 'content/001.md'},
                       {'id': '002', 'title': '第二节', 'markdown': 'content/002.md'}], 'book')
        (self.material / 'assets').mkdir()
        (self.material / 'assets/chart.svg').write_text('<svg/>')
        (self.material / 'content/001.md').write_text('# 第一节\n\n![图](../assets/chart.svg)\n\n[下一节](002.md#second)')
        (self.material / 'content/002.md').write_text('# 第二节\n\n<a id="second"></a>\n\n[返回](001.md)')
        build_readings(self.root, self.catalog)
        output = self.root / 'docs/read/example'
        first = (output / 'index.html').read_text()
        second = (output / 'pages/002.html').read_text()
        self.assertTrue((output / 'assets/chart.svg').is_file())
        self.assertIn('src="assets/chart.svg"', first)
        self.assertIn('href="pages/002.html#second"', first)
        self.assertIn('rel="next" href="pages/002.html"', first)
        self.assertIn('rel="prev" href="../index.html"', second)
        self.assertIn('../../../assets/reader.css?', second)


if __name__ == '__main__':
    unittest.main()
