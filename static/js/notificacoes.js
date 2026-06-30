(function () {
  const btn   = document.getElementById('notif-btn');
  const badge = document.getElementById('notif-badge');
  const lista = document.getElementById('notif-lista');

  if (!btn) return;

  const URL_LISTA = btn.dataset.url;
  const URL_LIDA  = btn.dataset.lidaUrl;

  const ICONS = {
    pagamento_pendente: 'bi-cash-coin text-danger',
    pedido_aberto:      'bi-cart3 text-secondary',
    aguard_producao:    'bi-scissors text-primary',
    aguard_montagem:    'bi-tools text-warning',
    pedido_cancelado:   'bi-x-circle text-danger',
    cobranca_30_dias:   'bi-alarm text-danger',
    picking:            'bi-box-seam text-info',
  };

  function getCsrf() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  }

  function atualizarBadge(total) {
    if (total > 0) {
      badge.textContent  = total > 99 ? '99+' : total;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  }

  function carregarNotificacoes() {
    fetch(URL_LISTA)
      .then(r => r.json())
      .then(data => {
        if (!data.ok) return;

        atualizarBadge(data.total);

        if (data.itens.length === 0) {
          lista.innerHTML = `
            <li class="px-3 py-3 text-center text-muted small">
              <i class="bi bi-check-circle text-success me-1"></i> Nada por aqui!
            </li>`;
          return;
        }

        lista.innerHTML = data.itens.map(n => `
          <li>
            <a href="${n.url}" class="dropdown-item px-3 py-2 border-bottom notif-item"
               data-pedido-pk="${n.pedido_pk}" data-tipo="${n.tipo}">
              <div class="d-flex align-items-start gap-2">
                <i class="bi ${ICONS[n.tipo] || 'bi-bell'} mt-1"></i>
                <div>
                  <p class="mb-0 small fw-semibold">${n.pedido} — ${n.cliente}</p>
                  <p class="mb-0 text-muted" style="font-size:0.75rem;">${n.label}</p>
                </div>
              </div>
            </a>
          </li>
        `).join('');

        lista.querySelectorAll('.notif-item').forEach(item => {
          item.addEventListener('click', function () {
            const pedidoPk = this.dataset.pedidoPk;
            const tipo     = this.dataset.tipo;

            fetch(`${URL_LIDA}${pedidoPk}/lida/`, {
              method:  'POST',
              headers: {
                'X-CSRFToken':  getCsrf(),
                'Content-Type': 'application/x-www-form-urlencoded',
              },
              body: `tipo=${encodeURIComponent(tipo)}`,
            }).then(() => {
              // Recarrega a lista após marcar como lida
              carregarNotificacoes();
            });
          });
        });
      })
      .catch(() => {
        lista.innerHTML = `
          <li class="px-3 py-3 text-center text-muted small">
            Erro ao carregar notificações.
          </li>`;
      });
  }

  function atualizarSoBadge() {
    fetch(URL_LISTA)
      .then(r => r.json())
      .then(data => { if (data.ok) atualizarBadge(data.total); });
  }

  // Carrega ao abrir o dropdown
  btn.addEventListener('show.bs.dropdown', carregarNotificacoes);

  // Atualiza badge a cada 60 segundos
  setInterval(atualizarSoBadge, 60000);

  // Carrega imediatamente
  atualizarSoBadge();
})();