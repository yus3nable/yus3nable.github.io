/* Section copying for the independently published MkDocs readers. */
(() => {
  function installCopyControls() {
    const article = document.querySelector('.md-content__inner');
    if (!article) return;
    const headings = [...article.querySelectorAll('h1, h2, h3, h4, h5, h6')];
    const status = document.createElement('p');
    status.className = 'copy-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    article.append(status);

    headings.forEach((heading, index) => {
      const title = heading.textContent.replace(/¶$/, '').trim();
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'copy-section';
      button.setAttribute('aria-label', `复制“${title}”小节`);
      button.title = `复制“${title}”小节`;
      button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><g class="copy-symbol"><rect x="3" y="8" width="13" height="13" rx="3"/><path d="M8 8V6a3 3 0 0 1 3-3h7a3 3 0 0 1 3 3v7a3 3 0 0 1-3 3h-2"/></g><path class="copy-success" d="m5 12 4 4L19 6"/><path class="copy-error" d="m7 7 10 10M17 7 7 17"/></svg>';
      heading.append(button);
      button.addEventListener('click', async () => {
        button.disabled = true;
        status.textContent = '';
        const end = headings.slice(index + 1).find(next => next.tagName <= heading.tagName);
        const range = document.createRange();
        range.setStartBefore(heading);
        if (end) range.setEndBefore(end);
        else range.setEnd(article, article.childNodes.length);
        const container = document.createElement('div');
        container.append(range.cloneContents());
        container.querySelectorAll('button, .headerlink, .copy-status, script, style, .md-content__button, .reader-actions, .reading-detail, .reading-mode').forEach(node => node.remove());
        container.querySelectorAll('[href], [src]').forEach(node => {
          for (const attribute of ['href', 'src']) {
            if (node.hasAttribute(attribute)) node.setAttribute(attribute, new URL(node.getAttribute(attribute), location.href).href);
          }
        });
        container.style.cssText = 'position:fixed;left:-10000px;top:0;width:800px;';
        document.body.append(container);
        container.querySelectorAll('img').forEach(image => image.replaceWith(document.createTextNode(`\n![${image.alt}](${image.src})\n`)));
        const text = container.innerText.trim();
        container.remove();
        try {
          await navigator.clipboard.writeText(text);
          button.dataset.copyState = 'copied';
          status.textContent = '本小节已复制';
        } catch (error) {
          button.dataset.copyState = 'error';
          status.textContent = '复制失败，请重试或选中文字复制。';
          console.error('小节复制失败', error);
        } finally {
          button.disabled = false;
          setTimeout(() => { delete button.dataset.copyState; }, 1800);
        }
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installCopyControls);
  else installCopyControls();
})();
