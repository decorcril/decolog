document.addEventListener('DOMContentLoaded', () => {
  const mobileSidebar = document.getElementById('mobile-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const btnOpen = document.getElementById('mobile-menu-toggle');
  const btnClose = document.getElementById('mobile-sidebar-close');

  if (!mobileSidebar) return;

  function abrirSidebar() {
    mobileSidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function fecharSidebar() {
    mobileSidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  if (btnOpen) btnOpen.addEventListener('click', abrirSidebar);
  if (btnClose) btnClose.addEventListener('click', fecharSidebar);
  if (overlay) overlay.addEventListener('click', fecharSidebar);

  mobileSidebar.querySelectorAll('.mobile-nav-link').forEach(link => {
    link.addEventListener('click', fecharSidebar);
  });
});