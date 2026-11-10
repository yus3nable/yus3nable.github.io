
const toggle=document.querySelector('.font-toggle');
const menu=document.querySelector('.font-menu');
const key='reading-room:font-size';
function size(value){value=Math.min(22,Math.max(14,value));document.documentElement.style.fontSize=value+'px';localStorage.setItem(key,String(value));}
const stored=Number(localStorage.getItem(key));if(stored>=14&&stored<=22)size(stored);
toggle.addEventListener('click',()=>{menu.hidden=!menu.hidden;toggle.setAttribute('aria-expanded',String(!menu.hidden));});
document.querySelectorAll('[data-font]').forEach(button=>button.addEventListener('click',()=>{const current=parseFloat(getComputedStyle(document.documentElement).fontSize);size(button.dataset.font==='reset'?16:current+Number(button.dataset.font));}));
document.addEventListener('click',event=>{if(!event.target.closest('.tools')){menu.hidden=true;toggle.setAttribute('aria-expanded','false');}});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){menu.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();}});
const search=document.querySelector('.search');let index=null;
search.addEventListener('input',async()=>{const results=document.querySelector('.search-results');results.replaceChildren();const query=search.value.trim().toLowerCase();if(!query)return;try{if(!index)index=await fetch(search.dataset.index).then(response=>{if(!response.ok)throw new Error('搜索加载失败');return response.json();});const matches=index.filter(row=>(row.title+' '+row.text).toLowerCase().includes(query)).slice(0,12);for(const row of matches){const li=document.createElement('li');const a=document.createElement('a');a.href=search.dataset.prefix+row.route;a.textContent=row.title;li.append(a);results.append(li);}if(!matches.length)results.textContent='没有找到匹配内容';}catch(error){results.textContent=error.message;}});

const outline=document.querySelector('.course-outline, .outline');if(outline)outline.open=window.matchMedia('(min-width:800px)').matches;

const sectionLinks = [...document.querySelectorAll('[data-section-id]')];
const sections = sectionLinks.map(link => ({link, heading: document.getElementById(link.dataset.sectionId)}));
function markCurrentSection() {
  let current = null;
  for (const section of sections) {
    if (section.heading.getBoundingClientRect().top > window.innerHeight * .3) break;
    current = section.link;
  }
  for (const {link} of sections) {
    if (link === current) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  }
}
if (sections.length) {
  let pending = false;
  window.addEventListener('scroll', () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { markCurrentSection(); pending = false; });
  }, {passive: true});
  window.addEventListener('load', markCurrentSection);
  window.addEventListener('hashchange', markCurrentSection);
  markCurrentSection();
}

const copyData = document.querySelectorAll('.section-copy-data')[0];
if (copyData) {
  const sectionText = JSON.parse(copyData.textContent);
  const copyStatus = document.querySelector('.copy-status');
  document.querySelectorAll('[data-copy-section]').forEach(button => {
    button.addEventListener('click', async () => {
      button.disabled = true;
      copyStatus.textContent = '';
      try {
        await navigator.clipboard.writeText(sectionText[button.dataset.copySection]);
        button.textContent = '已复制';
        copyStatus.textContent = '本小节已复制';
      } catch (error) {
        button.textContent = '复制失败';
        copyStatus.textContent = '复制失败，请重试或选中文字复制。';
        console.error('小节复制失败', error);
      } finally {
        button.disabled = false;
        setTimeout(() => { button.textContent = '复制本节'; }, 1800);
      }
    });
  });
}
