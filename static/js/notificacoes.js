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

  let totalAnterior = 0;
  let dropdownAberto = false;

  function getCsrf() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  }

  function atualizarBadge(total) {
    if (total > 0) {
      badge.textContent   = total > 99 ? '99+' : total;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  }

  function renderLista(itens) {
    if (itens.length === 0) {
      lista.innerHTML = `
        <li class="px-3 py-3 text-center text-muted small">
          <i class="bi bi-check-circle text-success me-1"></i> Nada por aqui!
        </li>`;
      return;
    }

    lista.innerHTML = itens.map(n => `
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
      item.addEventListener('click', function (e) {
        e.preventDefault();
        const destino = this.href;

        fetch(`${URL_LIDA}${this.dataset.pedidoPk}/lida/`, {
          method:  'POST',
          headers: {
            'X-CSRFToken':  getCsrf(),
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: `tipo=${encodeURIComponent(this.dataset.tipo)}`,
        }).finally(() => {
          window.location.href = destino;
        });
      });
    });
  }

  function buscarNotificacoes() {
    fetch(URL_LISTA)
      .then(r => r.json())
      .then(data => {
        if (!data.ok) return;

        atualizarBadge(data.total);

        // Atualiza lista se dropdown estiver aberto
        if (dropdownAberto) {
          renderLista(data.itens);
        }

        // Se o total aumentou e o dropdown está fechado, pisca o badge
        if (data.total > totalAnterior && !dropdownAberto) {
          badge.classList.add('animate__animated', 'animate__bounce');
          setTimeout(() => badge.classList.remove('animate__animated', 'animate__bounce'), 1000);
        }

        totalAnterior = data.total;
      })
      .catch(() => {});
  }

  // Carrega ao abrir o dropdown
  btn.addEventListener('show.bs.dropdown', () => {
    dropdownAberto = true;
    buscarNotificacoes();
  });

  btn.addEventListener('hide.bs.dropdown', () => {
    dropdownAberto = false;
  });

  // Polling a cada 15 segundos
  setInterval(buscarNotificacoes, 15000);

  // Carrega imediatamente
  buscarNotificacoes();
})();