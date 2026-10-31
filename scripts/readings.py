"""Render local Markdown readings into the shared personal website."""
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
import shutil
from urllib.parse import unquote, urljoin, urlsplit

import markdown


def local_file(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'内容引用超出读物目录：{relative}')
    return path


def relative_url(source, target):
    return posixpath.relpath(str(target), str(Path(source).parent))


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def build_readings(root, catalog):
    root = Path(root).resolve()
    indexes = {}
    asset_version = str(max((root / 'src' / name).stat().st_mtime_ns
                            for name in ['reader.css', 'reader.js', 'theme.css', 'theme.js']))
    template = (root / 'src/reader.html').read_text(encoding='utf-8')
    for item in catalog:
        material = root / 'content' / item['id']
        manifest = material / 'reading.json'
        if not manifest.is_file():
            continue
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if data['id'] != item['id'] or not data['pages']:
            raise ValueError(f'读物身份或目录无效：{item["id"]}')
        pages = data['pages']
        if len({page['id'] for page in pages}) != len(pages):
            raise ValueError(f'页面 ID 重复：{item["id"]}')
        routes = ['index.html'] + [f'pages/{page["id"]}.html' for page in pages[1:]]
        sources = [local_file(material, page['markdown']) for page in pages]
        source_routes = dict(zip(sources, routes))
        output = root / 'docs/read' / item['id']
        output.mkdir(parents=True, exist_ok=True)
        content_version = str(max(path.stat().st_mtime_ns for path in [manifest, *sources]))
        documents = []
        for number, (page, source, route) in enumerate(zip(pages, sources, routes)):
            public_route = './' if number == 0 else route
            prefix = relative_url(route, '.') + '/'
            if prefix == './':
                prefix = ''
            converter = markdown.Markdown(extensions=['extra', 'toc'],
                                         extension_configs={'toc': {'toc_depth': '2-3'}})
            body = converter.convert(source.read_text(encoding='utf-8').replace('[TOC]', ''))

            def reference(match):
                attribute, quote, value = match[1], match[2], html.unescape(match[3])
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith('/'):
                    return match[0]
                target = local_file(material, str(source.parent / unquote(parsed.path)))
                if target in source_routes:
                    destination = source_routes[target]
                elif attribute.strip().startswith('src='):
                    if data.get('format') == 'interview':
                        raise ValueError('访谈正文保持纯文字')
                    destination = target.relative_to(material).as_posix()
                    asset_output = output / destination
                    asset_output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, asset_output)
                else:
                    raise ValueError(f'本地链接没有对应的阅读页：{value}')
                rewritten = relative_url(route, destination)
                if parsed.query:
                    rewritten += '?' + parsed.query
                if parsed.fragment:
                    rewritten += '#' + parsed.fragment
                return attribute + quote + html.escape(rewritten, quote=True) + quote

            if data.get('format') == 'interview' and re.search(r'<img\b', body):
                raise ValueError('访谈正文保持纯文字')
            body = re.sub(r'(\b(?:src|href)=)([\"\'])(.*?)\2', reference, body)
            if not re.search(r'<h1(?:\s|>)', body):
                body = f'<h1>{html.escape(page["title"])}</h1>' + body
            navigation = converter.toc
            if len(pages) > 1:
                navigation = '<ol>' + ''.join(
                    f'<li><a href="{html.escape(relative_url(route, target), quote=True)}"'
                    + (' aria-current="page"' if index == number else '')
                    + f'>{html.escape(row["title"])}</a></li>'
                    for index, (row, target) in enumerate(zip(pages, routes))) + '</ol>'
            prev = (f'<a rel="prev" href="{relative_url(route, routes[number-1])}">'
                    f'← {html.escape(pages[number-1]["title"])}</a>') if number else '<span></span>'
            nxt = (f'<a rel="next" href="{relative_url(route, routes[number+1])}">'
                   f'{html.escape(pages[number+1]["title"])} →</a>') if number + 1 < len(pages) else '<span></span>'
            location = Path('read') / item['id'] / route
            assets_prefix = relative_url(location, 'assets') + '/'
            values = {'TITLE': html.escape(page['title']), 'KIND': html.escape(data['kind']),
                      'HOME': relative_url(location, '.') + '/', 'ASSETS': assets_prefix,
                      'ASSET_VERSION': asset_version, 'CONTENT_VERSION': content_version,
                      'ROOT_PREFIX': prefix, 'NAVIGATION': navigation, 'BODY': body,
                      'PREV': prev, 'NEXT': nxt, 'MATERIAL_ID': html.escape(data['id'], quote=True),
                      'PAGE_ID': html.escape(page['id'], quote=True),
                      'CANONICAL': html.escape(urljoin(item['url'], public_route), quote=True)}
            rendered = template
            for key, value in values.items():
                rendered = rendered.replace('{{' + key + '}}', value)
            destination = output / route
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding='utf-8')
            text = Text()
            text.feed(body)
            documents.append({'route': public_route, 'title': page['title'],
                              'text': ' '.join(text.parts)})
        (output / 'search.json').write_text(json.dumps(documents, ensure_ascii=False), encoding='utf-8')
        indexes[item['id']] = documents
    for name in ['reader.css', 'reader.js', 'theme.css', 'theme.js']:
        shutil.copy2(root / 'src' / name, root / 'docs/assets' / name)
    return indexes
