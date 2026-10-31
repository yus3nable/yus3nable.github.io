(() => {
  'use strict';
  const key = 'reading-room:theme';
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference;
  // 阅读不依赖浏览器是否允许存储偏好。
  try { preference = localStorage.getItem(key); } catch (error) { console.warn('主题偏好无法读取', error); }
  const root = document.documentElement;
  function apply() {
    const dark = preference === 'dark' || (preference !== 'light' && system.matches);
    root.dataset.theme = dark ? 'dark' : 'light';
    document.querySelectorAll('.theme-toggle').forEach(button => {
      const label = dark ? '切换到日间模式' : '切换到夜间模式';
      button.setAttribute('aria-label', label);
      button.setAttribute('title', label);
      button.setAttribute('aria-pressed', String(dark));
    });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? '#20211e' : '#faf9f5';
  }
  apply();
  document.addEventListener('DOMContentLoaded', apply);
  document.addEventListener('click', event => {
    if (!event.target.closest('.theme-toggle')) return;
    preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(key, preference); } catch (error) { console.warn('主题偏好无法保存', error); }
    apply();
  });
  system.addEventListener('change', () => { if (preference !== 'dark' && preference !== 'light') apply(); });
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) { preference = event.newValue; apply(); }
  });
})();
