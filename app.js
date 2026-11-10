(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('#theme-toggle');
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let storedTheme = null;
  try { storedTheme = localStorage.getItem('portfolio-theme'); } catch {}
  if (storedTheme === 'light' || storedTheme === 'dark') root.dataset.theme = storedTheme;
  const currentDark = () => root.dataset.theme ? root.dataset.theme === 'dark' : media.matches;
  function updateThemeLabel() {
    const dark = currentDark();
    themeButton.textContent = dark ? '浅色' : '深色';
    themeButton.setAttribute('aria-label', dark ? '切换浅色模式' : '切换深色模式');
  }
  themeButton.addEventListener('click', () => {
    root.dataset.theme = currentDark() ? 'light' : 'dark';
    try { localStorage.setItem('portfolio-theme', root.dataset.theme); } catch {}
    updateThemeLabel();
  });
  media.addEventListener('change', updateThemeLabel);
  updateThemeLabel();

  const tabs = [...document.querySelectorAll('[role="tab"]')];
  function selectTab(tab, focus = false) {
    for (const item of tabs) {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
    }
    if (focus) tab.focus();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
      const move = {ArrowRight: 1, ArrowLeft: -1};
      if (event.key in move) {
        event.preventDefault();
        selectTab(tabs[(index + move[event.key] + tabs.length) % tabs.length], true);
      } else if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault(); selectTab(event.key === 'Home' ? tabs[0] : tabs[tabs.length - 1], true);
      }
    });
  });

  const dialog = document.querySelector('#evidence-dialog');
  if (typeof dialog.showModal === 'function') {
    document.querySelector('[data-evidence]').addEventListener('click', event => {
      event.preventDefault();
      dialog.showModal();
    });
  }
  document.querySelector('#close-dialog').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    }
  });
})();
