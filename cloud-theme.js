// Public display preference only; never stores school or authentication data.
let savedTheme;try{savedTheme=localStorage.getItem('ag-cloud-theme');}catch{}
document.documentElement.dataset.theme = savedTheme === 'dark' ? 'dark' : 'light';
const themeButton = document.createElement('button');
themeButton.className = 'theme-toggle secondary';
function updateThemeButton() {
  const dark = document.documentElement.dataset.theme === 'dark';
  themeButton.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${dark ? '<circle cx="12" cy="12" r="4"/><path d="M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5L19 19 M5 19l1.5-1.5 M17.5 6.5L19 5"/>' : '<path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z"/>'}</svg>`;
  themeButton.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} theme`);
  themeButton.title = themeButton.getAttribute('aria-label');
}
themeButton.onclick = () => {
  document.documentElement.classList.add('switching-theme');
  const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = theme;
  try{localStorage.setItem('ag-cloud-theme', theme);}catch{}
  updateThemeButton();
  requestAnimationFrame(()=>requestAnimationFrame(()=>document.documentElement.classList.remove('switching-theme')));
};
updateThemeButton();
document.querySelector('header').append(themeButton);
