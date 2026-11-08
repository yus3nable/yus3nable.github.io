const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/reader.js'), 'utf8');

function setup(desktop = true) {
  const events = {}, outline = {open: false};
  const links = ['first', 'second'].map(id => ({dataset: {sectionId: id}, attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; }}));
  const positions = [200, 600];
  const button = {addEventListener() {}};
  const context = {document: {
    documentElement: {style: {}}, addEventListener() {},
    querySelector(selector) {
      if (selector.includes('.outline')) return outline;
      if (selector === '.font-menu') return {hidden: true};
      return button;
    },
    querySelectorAll(selector) { return selector === '[data-section-id]' ? links : []; },
    getElementById(id) { return {getBoundingClientRect: () => ({top: positions[id === 'first' ? 0 : 1]})}; }
  }, localStorage: {getItem() { return null; }},
    window: {innerHeight: 1000, matchMedia: () => ({matches: desktop}),
      addEventListener(name, fn) { events[name] = fn; }},
    requestAnimationFrame(fn) { fn(); }};
  vm.runInNewContext(source, context);
  return {events, outline, links, positions};
}

test('正文滚动后只高亮当前小节', () => {
  const state = setup();
  assert.equal(state.links[0].attributes['aria-current'], 'location');
  state.positions.splice(0, 2, -400, -40);
  state.events.scroll();
  assert.equal(state.links[0].attributes['aria-current'], undefined);
  assert.equal(state.links[1].attributes['aria-current'], 'location');
});

test('页面开头不误选后面的小节，锚点跳转后更新高亮', () => {
  const state = setup();
  state.positions.splice(0, 2, 700, 900);
  state.events.load();
  assert.ok(state.links.every(link => !link.attributes['aria-current']));
  state.positions.splice(0, 2, -200, 20);
  state.events.hashchange();
  assert.equal(state.links[1].attributes['aria-current'], 'location');
});

test('桌面展开导航，手机初始收起', () => {
  assert.equal(setup(true).outline.open, true);
  assert.equal(setup(false).outline.open, false);
});
