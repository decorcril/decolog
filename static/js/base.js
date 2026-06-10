document.addEventListener('DOMContentLoaded', () => {
  const mobileSidebar = document.getElementById('mobile-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const btnOpen = document.getElementById('mobile-menu-toggle');
  const btnClose = document.getElementById('mobile-sidebar-close');

  if (mobileSidebar) {
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
  }

  // Ativa tooltips Bootstrap
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // ── Modal de confirmação genérico ──
  // Uso: adicione data-confirm="Mensagem" no botão submit
  const modalConfirm = document.getElementById('modal-confirm');
  if (modalConfirm) {
    const modalTitle = modalConfirm.querySelector('#modal-confirm-title');
    const modalBody = modalConfirm.querySelector('#modal-confirm-body');
    const btnConfirm = modalConfirm.querySelector('#modal-confirm-btn');
    const bsModal = new bootstrap.Modal(modalConfirm);
    let formPendente = null;

    document.addEventListener('submit', (e) => {
      const form = e.target;

      // Se já foi confirmado, deixa passar
      if (form.querySelector('input[name="_confirmed"]')) return;

      const btn = form.querySelector('[data-confirm]');
      if (!btn) return;

      e.preventDefault();
      formPendente = form;

      const titulo = btn.dataset.confirmTitle || 'Confirmar ação';
      const mensagem = btn.dataset.confirm || 'Tem certeza que deseja continuar?';

      if (modalTitle) modalTitle.textContent = titulo;
      if (modalBody) modalBody.textContent = mensagem;

      bsModal.show();
    });

    if (btnConfirm) {
      btnConfirm.addEventListener('click', () => {
        bsModal.hide();
        if (formPendente) {
          const form = formPendente;
          formPendente = null;
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = '_confirmed';
          input.value = '1';
          form.appendChild(input);
          form.submit();
        }
      });
    }
  }
});