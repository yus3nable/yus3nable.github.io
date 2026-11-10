const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/reader.js'), 'utf8');

function setup(writeText) {
  const handlers = {}, timers = [], errors = [];
  const text = '## 会成长的个人助手\n\n正文。\n\n```js\nrun();\n```';
  const button = {dataset: {copySection: 'assistant'}, textContent: '复制本节',
    addEventListener(name, fn) { handlers[name] = fn; }};
  const status = {textContent: ''};
  const unused = {addEventListener() {}};
  vm.runInNewContext(source, {
    document: {
      documentElement: {style: {}}, addEventListener() {},
      querySelector(selector) { return selector === '.copy-status' ? status : unused; },
      querySelectorAll(selector) {
        if (selector === '.section-copy-data') return [{textContent: JSON.stringify({assistant: text})}];
        if (selector === '[data-copy-section]') return [button];
        return [];
      }
    },
    localStorage: {getItem() { return null; }},
    window: {matchMedia: () => ({matches: true})},
    navigator: {clipboard: {writeText}},
    setTimeout(fn) { timers.push(fn); },
    console: {error(...args) { errors.push(args); }}
  });
  return {handlers, timers, errors, button, status, text};
}

test('点击复制完整小节并显示成功反馈，随后恢复按钮', async () => {
  let copied;
  const state = setup(async text => { copied = text; });
  const pending = state.handlers.click();
  assert.equal(state.button.disabled, true);
  await pending;
  assert.equal(copied, state.text);
  assert.equal(state.button.textContent, '已复制');
  assert.equal(state.status.textContent, '本小节已复制');
  assert.equal(state.button.disabled, false);
  state.timers[0]();
  assert.equal(state.button.textContent, '复制本节');
});

test('剪贴板被拒绝时显示失败，保留错误并允许重试', async () => {
  const error = new Error('clipboard denied');
  const state = setup(async () => { throw error; });
  await state.handlers.click();
  assert.equal(state.button.textContent, '复制失败');
  assert.match(state.status.textContent, /复制失败/);
  assert.equal(state.button.disabled, false);
  assert.equal(state.errors[0][1], error);
});
