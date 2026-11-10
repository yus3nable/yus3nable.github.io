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


def section_tree(tokens, route, target, current):
    if not tokens:
        return ''
    rows = []
    for token in tokens:
        text = Text()
        text.feed(token['name'])
        anchor = token['id']
        href = ('#' + anchor) if current else relative_url(route, target) + '#' + anchor
        marker = f' data-section-id="{html.escape(anchor, quote=True)}"' if current else ''
        rows.append(f'<li><a href="{html.escape(href, quote=True)}"{marker}>'
                    + html.escape(''.join(text.parts)) + '</a>'
                    + section_tree(token['children'], route, target, current) + '</li>')
    return '<ul class="chapter-sections">' + ''.join(rows) + '</ul>'


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def copy_sections(source_text, rendered_body, material, source, source_routes, base_url):
    """Prepare full Markdown sections, using the same heading IDs as the reader."""
    lines = source_text.splitlines(keepends=True)
    headings = []
    fence = None
    for index, line in enumerate(lines):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            value = marker[1]
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence) and not line[marker.end():].strip():
                fence = None
            continue
        heading = re.match(r'^ {0,3}(#{1,6})\s+', line)
        if heading and fence is None:
            headings.append((index, len(heading[1])))
    rendered = list(re.finditer(r'<h([2-6])\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h\1>', rendered_body, re.S))
    sections = [(position, level) for position, level in headings if level >= 2]
    if len(sections) != len(rendered):
        raise ValueError(f'小节来源与页面标题不一致：{source}')

    def absolute_link(match):
        value = match[2]
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith('/'):
            return match[0]
        target = local_file(material, str(source.parent / unquote(parsed.path)))
        path = source_routes.get(target, target.relative_to(material).as_posix())
        url = urljoin(base_url, path)
        if parsed.query:
            url += '?' + parsed.query
        if parsed.fragment:
            url += '#' + parsed.fragment
        return match[1] + url + match[3]

    payload = {}
    for (start, level), heading in zip(sections, rendered):
        end = next((position for position, next_level in headings if position > start and next_level <= level), len(lines))
        selected = []
        in_code = None
        for line in lines[start:end]:
            marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
            if marker:
                value = marker[1]
                if in_code is None:
                    in_code = value
                elif value[0] == in_code[0] and len(value) >= len(in_code) and not line[marker.end():].strip():
                    in_code = None
                selected.append(line)
            elif in_code:
                selected.append(line)
            elif not re.match(r'^\s*\{:\s.*\}\s*$', line):
                line = re.sub(r'\s*\{#[^}]+\}(?=\s*$)', '', line).rstrip('\n') + '\n'
                line = re.sub(r'<!-- SOURCE .*? -->\s*', '', line)
                line = re.sub(r'(\]\()([^\s)]+)(\))', absolute_link, line)
                selected.append(line)
        text = ''.join(selected).strip()
        payload[html.unescape(heading[2])] = text

    def button(match):
        title = Text()
        title.feed(match[3])
        label = html.escape('复制“' + ''.join(title.parts) + '”小节', quote=True)
        return match[0].replace('</h' + match[1] + '>',
            f'<button type="button" class="copy-section" data-copy-section="{match[2]}" aria-label="{label}">复制本节</button></h{match[1]}>')

    body = re.sub(r'<h([2-6])\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h\1>', button, rendered_body, flags=re.S)
    data = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return body + '<p class="copy-status" role="status" aria-live="polite"></p><script type="application/json" class="section-copy-data">' + data + '</script>'


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
        contents_ids = {'toc', 'contents'} if data.get('format') == 'book' else set()
        reading_order = [i for i, page in enumerate(pages) if page['id'] not in contents_ids]
        first_chapter = next((i for i in reading_order if re.fullmatch(r'ch\d+', pages[i]['id'])), reading_order[0])
        rendered_pages = []
        for source in sources:
            converter = markdown.Markdown(extensions=['extra', 'toc', 'sane_lists'],
                                         extension_configs={'toc': {'toc_depth': '2-3'}})
            body = converter.convert(source.read_text(encoding='utf-8').replace('[TOC]', ''))
            rendered_pages.append((body, converter.toc, converter.toc_tokens))
        output = root / 'docs/read' / item['id']
        output.mkdir(parents=True, exist_ok=True)
        content_version = str(max(path.stat().st_mtime_ns for path in [manifest, *sources]))
        documents = []
        for number, (page, source, route) in enumerate(zip(pages, sources, routes)):
            if page['id'] in contents_ids:
                target = html.escape(relative_url(route, routes[first_chapter]), quote=True)
                destination = output / route
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
                                       + f'<meta http-equiv="refresh" content="0;url={target}">'
                                       + f'<title>{html.escape(data["title"])}</title>'
                                       + f'<a href="{target}">开始阅读</a></html>', encoding='utf-8')
                continue
            public_route = './' if number == 0 else route
            prefix = relative_url(route, '.') + '/'
            if prefix == './':
                prefix = ''
            body, page_toc, _ = rendered_pages[number]

            def reference(match):
                attribute, quote, value = match[1], match[2], html.unescape(match[3])
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith('/'):
                    return match[0]
                target = local_file(material, str(source.parent / unquote(parsed.path)))
                if target in source_routes:
                    destination = source_routes[target]
                elif (attribute.strip().startswith('src=')
                      or target.is_relative_to(material / 'assets') and target.is_file()):
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
            if len(pages) > 1:
                entries = []
                for index in reading_order:
                    row, target = pages[index], routes[index]
                    link = f'<a href="{html.escape(relative_url(route, target), quote=True)}"'
                    link += (' aria-current="page"' if index == number else '')
                    link += f'>{html.escape(row["title"])}</a>'
                    sections = section_tree(rendered_pages[index][2], route, target, index == number)
                    if sections:
                        link = '<details class="chapter-outline"' + (' open' if index == number else '') + '><summary>' + link + '</summary>' + sections + '</details>'
                    entries.append('<li>' + link + '</li>')
                navigation = '<details class="course-outline" open><summary>全部章节</summary><ol>' + ''.join(entries) + '</ol></details>'
            else:
                navigation = '<details class="outline" open><summary>目录</summary>' + page_toc + '</details>'
            search_body = body
            if item['id'] == 'nju-gense-2026':
                body = copy_sections(source.read_text(encoding='utf-8'), body, material, source, source_routes, item['url'])
            position = reading_order.index(number)
            prev = (f'<a rel="prev" href="{relative_url(route, routes[reading_order[position-1]])}">'
                    f'← {html.escape(pages[reading_order[position-1]]["title"])}</a>') if position else '<span></span>'
            nxt = (f'<a rel="next" href="{relative_url(route, routes[reading_order[position+1]])}">'
                   f'{html.escape(pages[reading_order[position+1]]["title"])} →</a>') if position + 1 < len(reading_order) else '<span></span>'
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
            text.feed(search_body)
            documents.append({'route': public_route, 'title': page['title'],
                              'text': ' '.join(text.parts)})
        (output / 'search.json').write_text(json.dumps(documents, ensure_ascii=False), encoding='utf-8')
        indexes[item['id']] = documents
    for name in ['reader.css', 'reader.js', 'theme.css', 'theme.js']:
        shutil.copy2(root / 'src' / name, root / 'docs/assets' / name)
    return indexes
