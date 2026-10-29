(() => {
  'use strict';
  const library = JSON.parse(document.getElementById('library-data').textContent);
  const search = document.getElementById('search');
  const status = document.getElementById('search-status');
  const cards = [...document.querySelectorAll('.collection')];
  const resultSection = document.getElementById('document-results');
  const resultsList = document.getElementById('results-list');
  const empty = document.getElementById('empty-state');
  const more = document.getElementById('more-results');
  const retry = document.getElementById('retry-search');
  const storageKey = 'reading-room:last-opened';
  let filter = '全部';
  let documents;
  let loading;
  let queryVersion = 0;
  let limit = 12;
  let matches = [];
  let timer;

  function showContinue(record) {
    if (!record || !library.some(item => record.url.startsWith(item.url))) return;
    const link = document.getElementById('continue-link');
    link.href = record.url;
    link.textContent = record.title;
    document.getElementById('continue-reading').hidden = false;
  }
  showContinue(JSON.parse(localStorage.getItem(storageKey) || 'null'));
  document.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    const item = library.find(item => link.href.startsWith(item.url));
    if (!item) return;
    const record = {url: link.href, title: link.dataset.readingTitle || item.title};
    localStorage.setItem(storageKey, JSON.stringify(record));
    showContinue(record);
  });
  document.getElementById('dismiss-continue').addEventListener('click', () => {
    localStorage.removeItem(storageKey);
    document.getElementById('continue-reading').hidden = true;
  });
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
      event.preventDefault();
      search.focus();
    }
    if (event.key === 'Escape' && document.activeElement === search) {
      search.value = '';
      update();
      search.blur();
    }
  });
  document.querySelectorAll('[data-filter]').forEach(button => {
    button.addEventListener('click', () => {
      filter = button.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      update();
    });
  });
  function tokensFor(value) { return value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean); }
  function includesAll(text, tokens) { const value = text.toLocaleLowerCase(); return tokens.every(token => value.includes(token)); }
  async function loadDocuments() {
    if (documents) return documents;
    if (!loading) {
      loading = fetch('assets/search-index.json').then(response => {
        if (!response.ok) throw new Error(`正文索引请求失败：${response.status}`);
        return response.json();
      }).then(data => { documents = data; return data; });
    }
    return loading;
  }
  function excerpt(text, tokens) {
    const position = Math.max(0, text.toLocaleLowerCase().indexOf(tokens[0]) - 32);
    return (position ? '…' : '') + text.slice(position, position + 125) + (text.length > position + 125 ? '…' : '');
  }
  function renderResults(tokens) {
    resultsList.replaceChildren();
    for (const row of matches.slice(0, limit)) {
      const link = document.createElement('a');
      link.className = 'document-result';
      link.href = row.url;
      link.dataset.readingTitle = row.title;
      const source = document.createElement('small');
      source.textContent = row.source;
      const title = document.createElement('h4');
      title.textContent = row.title;
      const summary = document.createElement('p');
      summary.textContent = excerpt(row.text, tokens);
      link.append(source, title, summary);
      resultsList.append(link);
    }
    resultSection.hidden = !matches.length;
    more.hidden = matches.length <= limit;
  }
  async function update() {
    const current = ++queryVersion;
    const tokens = tokensFor(search.value);
    limit = 12;
    matches = [];
    resultSection.hidden = true;
    retry.hidden = true;
    let visible = 0;
    for (const card of cards) {
      const item = library.find(item => item.id === card.dataset.id);
      card.hidden = (filter !== '全部' && item.kind !== filter) || !includesAll([item.title, item.subtitle, item.description, ...item.topics].join(' '), tokens);
      if (!card.hidden) visible++;
    }
    empty.hidden = visible > 0;
    status.hidden = !tokens.length;
    if (!tokens.length) {
      empty.textContent = filter === '文章' ? '还没有文章。' : '没有找到相关内容。';
      empty.hidden = visible > 0;
      return;
    }
    empty.textContent = '没有找到相关内容，试试其他关键词。';
    empty.hidden = true;
    status.textContent = '正在查找正文…';
    try {
      const data = await loadDocuments();
      if (current !== queryVersion) return;
      matches = data.filter(row => (filter === '全部' || row.kind === filter) && includesAll(row.title + ' ' + row.text, tokens))
        .map(row => ({...row, score: tokens.reduce((total, token) => total + (row.title.toLocaleLowerCase().includes(token) ? 20 : 1), 0)}))
        .sort((a, b) => b.score - a.score);
      status.textContent = `找到 ${visible} 项资料、${matches.length} 处正文`;
      empty.hidden = visible + matches.length > 0;
      renderResults(tokens);
    } catch (error) {
      if (current !== queryVersion) return;
      status.textContent = '正文搜索暂时无法加载，资料标题仍可搜索。';
      retry.hidden = false;
      loading = undefined;
      console.error(error);
    }
  }
  search.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(update, 180); });
  more.addEventListener('click', () => { limit += 12; renderResults(tokensFor(search.value)); });
  retry.addEventListener('click', update);
})();
