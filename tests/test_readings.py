import json
import re
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
        self.assertIn('<summary>目录</summary>', page.read_text())

    def test_multiple_pages_rewrite_markdown_links_images_and_prev_next(self):
        self.manifest([{'id': '001', 'title': '第一节', 'markdown': 'content/001.md'},
                       {'id': '002', 'title': '第二节', 'markdown': 'content/002.md'}], 'book')
        (self.material / 'assets').mkdir()
        (self.material / 'assets/chart.svg').write_text('<svg/>')
        (self.material / 'content/001.md').write_text('# 第一节\n\n[![图](../assets/chart.svg)](../assets/chart.svg)\n\n[下一节](002.md#second)')
        (self.material / 'content/002.md').write_text('# 第二节\n\n## 本课重点 {#second}\n\n[返回](001.md)')
        build_readings(self.root, self.catalog)
        output = self.root / 'docs/read/example'
        first = (output / 'index.html').read_text()
        second = (output / 'pages/002.html').read_text()
        self.assertTrue((output / 'assets/chart.svg').is_file())
        self.assertIn('src="assets/chart.svg"', first)
        self.assertIn('href="assets/chart.svg"', first)
        self.assertIn('href="pages/002.html#second"', first)
        self.assertIn('rel="next" href="pages/002.html"', first)
        self.assertIn('rel="prev" href="../index.html"', second)
        self.assertIn('../../../assets/reader.css?', second)
        self.assertIn('href="#second" data-section-id="second">本课重点</a>', second)
        self.assertIn('class="course-outline"', second)
        self.assertNotIn('<summary>目录</summary>', second)
        self.assertIn('<details class="chapter-outline" open>', second)
        self.assertEqual(second.count('href="#second"'), 1)
        self.assertIn('data-section-id="second"', second)
        self.assertIn('href="pages/002.html#second"', first)
        self.assertIn('aria-current="page"', second)

    def test_book_contents_redirects_and_is_skipped_in_navigation_and_search(self):
        self.manifest([{'id': 'ch01', 'title': '第一章', 'markdown': 'content/ch01.md'},
                       {'id': 'contents', 'title': '目录', 'markdown': 'content/contents.md'},
                       {'id': 'ch02', 'title': '第二章', 'markdown': 'content/ch02.md'}], 'book')
        (self.material / 'content/ch01.md').write_text('# 第一章\n\n## 基础 {#basics}\n\n内容')
        (self.material / 'content/contents.md').write_text('# 目录\n\n重复目录条目')
        (self.material / 'content/ch02.md').write_text('# 第二章\n\n## 应用 {#usage}\n\n内容')
        indexes = build_readings(self.root, self.catalog)
        output = self.root / 'docs/read/example'
        first = (output / 'index.html').read_text()
        second = (output / 'pages/ch02.html').read_text()
        legacy = (output / 'pages/contents.html').read_text()
        self.assertIn('http-equiv="refresh" content="0;url=../index.html"', legacy)
        self.assertIn('rel="next" href="pages/ch02.html"', first)
        self.assertIn('rel="prev" href="../index.html"', second)
        self.assertNotIn('contents.html', first)
        self.assertIn('href="../index.html#basics"', second)
        self.assertNotIn('class="chapter-outline" open><summary><a href="../index.html"', second)
        self.assertEqual(len(indexes['example']), 2)

    def test_numbered_steps_keep_their_numbers_across_source_comments(self):
        self.manifest([{'id': '001', 'title': '协议步骤', 'markdown': 'content/001.md'}])
        (self.material / 'content/001.md').write_text(
            '# 协议步骤\n\n1. 发出请求。\n\n<!-- SOURCE page-2 -->\n\n'
            '2. 接收回应。\n\n<!-- SOURCE page-3 -->\n\n3. 提交。')
        build_readings(self.root, self.catalog)
        html = (self.root / 'docs/read/example/index.html').read_text()
        self.assertIn('<ol start="2">', html)
        self.assertIn('<ol start="3">', html)

    def test_course_copy_includes_nested_sections_and_keeps_code_exact(self):
        renamed = self.material.with_name('nju-gense-2026')
        self.material.rename(renamed)
        self.material = renamed
        self.catalog = [{'id': 'nju-gense-2026', 'url': 'https://example.com/read/course/'}]
        self.manifest([{'id': '04', 'title': '课程', 'markdown': 'content/04.md'}], 'course')
        manifest = self.material / 'reading.json'
        data = json.loads(manifest.read_text())
        data['id'] = 'nju-gense-2026'
        manifest.write_text(json.dumps(data))
        (self.material / 'assets').mkdir()
        (self.material / 'assets/figure.svg').write_text('<svg/>')
        (self.material / 'content/04.md').write_text(
            '# 本课\n\n## 会成长的个人助手 {#assistant}\n\n*原片 00:00–06:37*\n{: #time}\n\n'
            '- 第一点\n\n![图](../assets/figure.svg)\n\n### 代码 {#code}\n\n'
            '```html\n## 代码中的标题\n{: #literal}\n<!-- SOURCE literal -->\n</script>\n```\n\n'
            '## 下一节 {#next}\n\n下一节正文。')
        indexes = build_readings(self.root, self.catalog)
        html = (self.root / 'docs/read/nju-gense-2026/index.html').read_text()
        raw = re.search(r'class="section-copy-data">(.*?)</script>', html, re.S)[1]
        payload = json.loads(raw)
        self.assertEqual(set(payload), {'assistant', 'code', 'next'})
        self.assertIn('## 会成长的个人助手\n', payload['assistant'])
        self.assertIn('*原片 00:00–06:37*', payload['assistant'])
        self.assertNotIn('{: #time}', payload['assistant'])
        self.assertIn('https://example.com/read/course/assets/figure.svg', payload['assistant'])
        self.assertIn('### 代码', payload['assistant'])
        self.assertIn('## 代码中的标题\n{: #literal}\n<!-- SOURCE literal -->\n</script>', payload['code'])
        self.assertNotIn('下一节正文', payload['assistant'])
        self.assertNotIn('会成长', payload['code'])
        self.assertNotIn('</script>', raw)
        self.assertEqual(html.count('class="copy-section"'), 3)
        self.assertNotIn('复制本节', indexes['nju-gense-2026'][0]['text'])


if __name__ == '__main__':
    unittest.main()
