#!/usr/bin/env python3
"""Build the personal reading room from its catalog and public search indexes."""
import argparse
import html
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urljoin
from readings import build_readings

ROOT = Path(__file__).resolve().parents[1]

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fragments = []
    def handle_data(self, data):
        self.fragments.append(data)

def plain(value):
    parser = PlainText()
    parser.feed(value)
    return re.sub(r'\s+', ' ', ''.join(parser.fragments).replace('\u200b', '')).strip()

def fetch_index(item):
    response = subprocess.run(['curl', '--compressed', '--fail', '--silent', '--show-error', '--retry', '2', '--retry-all-errors', '--max-time', '60', urljoin(item['url'], item['searchPath'])], check=True, capture_output=True)
    return json.loads(response.stdout)

def cover_svg(item):
    settings = {
        'nju-os-reading': ('#b16449', '#faf3e7', ['南京大学', '操作系统'], '2026', 'OPERATING SYSTEMS'),
        'ostep-zh-markdown': ('#e8e2d5', '#474b3e', ['操作系统', '导论'], 'OSTEP', 'THREE EASY PIECES'),
        'programmer-self-cultivation-reading': ('#343b34', '#f0eadc', ['程序员的', '自我修养'], 'C / C++', 'LINKING & LOADING'),
        'bv1lsht6feaq': ('#e1d0bd', '#534638', ['Lauren Tan', 'AI 工作流'], '64 MIN', 'AGENTS & WORKFLOWS'),
    }
    bg, ink, title, small, bottom = settings.get(item['id'], ('#e8e2d5', '#474b3e', [item['kind'], '图文阅读'], '', ''))
    motif = '<path d="M50 130h46m0 0v25m0-25h46m-46 25h46"/><rect x="35" y="120" width="15" height="20" rx="2"/><rect x="142" y="120" width="15" height="20" rx="2"/><rect x="142" y="145" width="15" height="20" rx="2"/>'
    if item['id'] == 'ostep-zh-markdown':
        motif = '<circle cx="73" cy="142" r="25"/><circle cx="119" cy="142" r="25"/><path d="M49 177h94"/>'
    elif item['id'] == 'programmer-self-cultivation-reading':
        motif = '<rect x="42" y="125" width="108" height="47" rx="2"/><path d="M78 125v47m36-47v47M42 149h108"/>'
    elif item['kind'] == '文章':
        motif = '<path d="M40 126h108m-108 15h82m-82 15h100m-100 15h67"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="192" height="250" viewBox="0 0 192 250"><rect width="192" height="250" fill="{bg}"/><path d="M10 0v250" stroke="{ink}" opacity=".14"/><g fill="{ink}" font-family="Songti SC,STSong,serif"><text x="29" y="55" font-size="23">{title[0]}</text><text x="29" y="88" font-size="23">{title[1]}</text></g><g stroke="{ink}" fill="none" stroke-width="1.2" opacity=".65">{motif}</g><g fill="{ink}" font-family="Arial,sans-serif"><text x="29" y="206" font-size="11">{html.escape(small)}</text><text x="29" y="226" font-size="8" letter-spacing=".7">{html.escape(bottom)}</text></g></svg>'''

def build(sync):
    catalog = json.loads((ROOT/'data/library.json').read_text())
    assert len({item['id'] for item in catalog}) == len(catalog)
    output = ROOT/'docs'
    assets = output/'assets'
    assets.mkdir(parents=True, exist_ok=True)
    for name in ['style.css', 'app.js', 'theme.css', 'theme.js']:
        shutil.copy2(ROOT/'src'/name, assets/name)
    local_indexes = build_readings(ROOT, catalog)
    rows = []
    documents = []
    source_counts = {}
    for order, item in enumerate(catalog):
        e = lambda key: html.escape(item[key], quote=True)
        (assets/item['cover']).write_text(cover_svg(item))
        rows.append(f'''<article class="collection" data-id="{e('id')}" style="--order:{order}"><a class="cover-link" href="{e('url')}" aria-label="阅读{e('title')}"><img src="assets/{e('cover')}" width="146" height="190" alt="" decoding="async"></a><div class="collection-content"><p class="collection-meta">{e('kind')} · {e('detail')}</p><h3><a href="{e('url')}">{e('title')}</a></h3><p class="collection-description">{e('description')}</p></div><a class="read-link" href="{e('url')}" aria-label="开始阅读{e('title')}">开始阅读<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6"/></svg></a></article>''')
        cache = ROOT/'maintenance'/f"{item['id']}-search-source.json"
        if item['id'] in local_indexes:
            data = local_indexes[item['id']]
        elif sync or not cache.exists():
            data = fetch_index(item)
            cache.write_text(json.dumps(data, ensure_ascii=False))
        else:
            data = json.loads(cache.read_text())
        entries = data if isinstance(data, list) else data['docs']
        grouped = {}
        for entry in entries:
            route = entry.get('route') or entry.get('location')
            if not route:
                continue
            url = urljoin(item['url'], route)
            if not url.startswith(item['url']):
                continue
            canonical = url.split('#', 1)[0]
            title = plain(entry['title'])
            text = re.sub(r'\s+', ' ', entry.get('text', '').replace('\u200b', '')).strip() if isinstance(data, list) else plain(entry.get('text', ''))
            if canonical not in grouped:
                grouped[canonical] = {'title': title, 'text': text, 'url': url, 'source': item['title'], 'kind': item['kind']}
            elif text and text not in grouped[canonical]['text']:
                grouped[canonical]['text'] += ' ' + title + ' ' + text
        documents.extend(grouped.values())
        source_counts[item['id']] = len(grouped)
    asset_version = str(max((ROOT/'src'/name).stat().st_mtime_ns for name in ['style.css', 'app.js', 'theme.css', 'theme.js']))
    content_inputs = [ROOT/'data/library.json', *list((ROOT/'content').rglob('*.md')), *list((ROOT/'content').rglob('*.json'))]
    content_version = str(max(path.stat().st_mtime_ns for path in content_inputs))
    page = (ROOT/'src/page.html').read_text().replace('{{ASSET_VERSION}}', asset_version).replace('{{CONTENT_VERSION}}', content_version).replace('{{TOTAL}}', str(len(catalog))).replace('{{COLLECTIONS}}', '\n'.join(rows)).replace('{{DATA}}', json.dumps(catalog, ensure_ascii=False).replace('<', '\\u003c'))
    (output/'index.html').write_text(page)
    (output/'404.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>没有找到这页 · 阅读室</title><link rel="stylesheet" href="/assets/style.css"><main class="page-shell intro"><h1 style="font-size:48px">这页暂时不在书架上</h1><p><a href="/">回到阅读室</a></p></main></html>''')
    (output/'.nojekyll').write_text('')
    (assets/'mark.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#faf9f5"/><path d="M16 9C12 5 6 5 3 6v19c5-1 9 0 13 3 4-3 8-4 13-3V6c-3-1-9-1-13 3ZM16 9v19" fill="none" stroke="#a44e35" stroke-width="1.6"/></svg>')
    (assets/'search-index.json').write_text(json.dumps(documents, ensure_ascii=False, separators=(',', ':')))
    report = {'collections': len(catalog), 'search_documents': len(documents), 'documents_by_collection': source_counts}
    (ROOT/'maintenance/build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sync-search', action='store_true', help='Fetch the latest public search indexes before building')
    build(parser.parse_args().sync_search)
