const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/theme.js'), 'utf8');

function setup(saved = null, dark = false, blocked = false) {
  const events = {}, attributes = {}, root = {dataset: {}}, meta = {};
  const button = {setAttribute: (name, value) => { attributes[name] = value; }};
  const system = {matches: dark, addEventListener: (name, fn) => { events.system = fn; }};
  const storage = {value: saved, getItem() { if (blocked) throw Error('blocked'); return this.value; },
    setItem(key, value) { if (blocked) throw Error('blocked'); this.value = value; }};
  const context = {document: {documentElement: root, querySelectorAll: () => [button], querySelector: () => meta,
    addEventListener: (name, fn) => { events[name] = fn; }}, localStorage: storage,
    window: {matchMedia: () => system, addEventListener: (name, fn) => { events[name] = fn; }}, console: {warn() {}}};
  vm.runInNewContext(source, context);
  return {events, attributes, root, storage, system, meta, click() { events.click({target: {closest: () => button}}); }};
}

test('默认跟随系统，系统切换后更新', () => {
  const state = setup(null, true);
  assert.equal(state.root.dataset.theme, 'dark');
  assert.equal(state.meta.content, '#20211e');
  state.system.matches = false; state.events.system();
  assert.equal(state.root.dataset.theme, 'light');
});
test('按钮切换并保存偏好，覆盖系统设置', () => {
  const state = setup('light', true); state.click();
  assert.equal(state.storage.value, 'dark');
  assert.equal(state.attributes['aria-pressed'], 'true');
  assert.equal(state.attributes['aria-label'], '切换到日间模式');
  state.system.matches = false; state.events.system();
  assert.equal(state.root.dataset.theme, 'dark');
});
test('刷新恢复选择，其他标签页切换保持一致', () => {
  const state = setup('dark');
  assert.equal(state.root.dataset.theme, 'dark');
  state.events.storage({key: 'reading-room:theme', newValue: 'light'});
  assert.equal(state.root.dataset.theme, 'light');
});
test('存储被禁用时仍可切换', () => {
  const state = setup(null, false, true); state.click();
  assert.equal(state.root.dataset.theme, 'dark');
});
test('无效的已存偏好继续跟随系统', () => {
  const state = setup('invalid', true);
  assert.equal(state.root.dataset.theme, 'dark');
  state.system.matches = false; state.events.system();
  assert.equal(state.root.dataset.theme, 'light');
});
