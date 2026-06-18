/* Selenio Analytics — JS */

// ── Tema dark/light ──────────────────────────────
function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('selenio-theme', next);
}

(function() {
  const saved = localStorage.getItem('selenio-theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
})();

// ── Menu grupo com submenus ──────────────────────
function toggleNavGroup(id) {
  const el      = document.getElementById(id);
  const chevron = document.getElementById('chevron-' + id);
  const isOpen  = el.classList.contains('open');
  el.classList.toggle('open', !isOpen);
  if (chevron) chevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(90deg)';
}

// Inicializa chevrons para grupos abertos
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-group-items.open').forEach(el => {
    const chevron = document.getElementById('chevron-' + el.id);
    if (chevron) chevron.style.transform = 'rotate(90deg)';
  });

  // Auto-dismiss flash
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .5s'; }, 4000);
    setTimeout(() => { el.remove(); }, 4500);
  });
});
