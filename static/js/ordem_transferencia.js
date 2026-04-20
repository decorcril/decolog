document.addEventListener('DOMContentLoaded', () => {

  // ══════════════════════════════════════════════════
  // ESTADO — lista de produtos adicionados em memória
  // Cada item: { id, nome, codigo, unidade, quantidade }
  // ══════════════════════════════════════════════════
  let produtos = [];

  // ══════════════════════════════════════════════════
  // TOM SELECT — campo de busca de produto
  // Busca por nome e código, carrega saldo ao selecionar
  // ══════════════════════════════════════════════════
  const selectProdutoEl = document.getElementById('select-produto');
  const tomSelect = new TomSelect(selectProdutoEl, {
    placeholder: 'Buscar por nome ou código...',
    allowEmptyOption: true,
    maxOptions: 100,
    searchField: ['text'],

    // Renderiza cada opção no dropdown
    render: {
      option: function(data, escape) {
        return `<div class="py-1">${escape(data.text)}</div>`;
      }
    },

    // Ao selecionar um produto, carrega o saldo disponível via API
    onChange: function(value) {
      const saldoInfo = document.getElementById('saldo-ordem-info');
      const saldoLista = document.getElementById('saldo-ordem-lista');

      if (!value) {
        if (saldoInfo) saldoInfo.style.display = 'none';
        return;
      }

      fetch(`/estoque/saldo/${value}/`)
        .then(r => r.json())
        .then(data => {
          if (!saldoInfo) return;
          if (data.saldos.length === 0) {
            saldoLista.innerHTML = '<span class="text-muted">Sem estoque disponível.</span>';
          } else {
            saldoLista.innerHTML = data.saldos.map(s =>
              `<div class="d-flex justify-content-between">
                <span class="text-muted">${s.local}</span>
                <span class="fw-semibold">${s.quantidade}</span>
              </div>`
            ).join('');
          }
          saldoInfo.style.display = 'block';
        });
    }
  });

  // ══════════════════════════════════════════════════
  // ADICIONAR PRODUTO
  // Valida, adiciona à lista e atualiza a interface
  // ══════════════════════════════════════════════════
  document.getElementById('btn-adicionar').addEventListener('click', () => {
    const produtoId = tomSelect.getValue();
    const quantidade = parseFloat(document.getElementById('input-quantidade').value);
    const option = selectProdutoEl.querySelector(`option[value="${produtoId}"]`);

    // Validações
    if (!produtoId) { mostrarErro('Selecione um produto.'); return; }
    if (!quantidade || quantidade <= 0) { mostrarErro('Informe uma quantidade válida.'); return; }
    if (produtos.find(p => p.id === produtoId)) {
      mostrarErro('Este produto já foi adicionado. Remova e adicione novamente para alterar a quantidade.');
      return;
    }

    // Adiciona à lista
    produtos.push({
      id: produtoId,
      nome: option.dataset.nome,
      codigo: option.dataset.codigo,
      unidade: option.dataset.unidade,
      quantidade,
    });

    // Limpa os campos
    tomSelect.setValue('');
    document.getElementById('input-quantidade').value = '';
    document.getElementById('saldo-ordem-info') && (document.getElementById('saldo-ordem-info').style.display = 'none');
    esconderErro();

    // Atualiza a interface
    renderizarCards();
    atualizarInputsHidden();
  });

  // ══════════════════════════════════════════════════
  // REMOVER PRODUTO
  // Remove da lista ao clicar no botão de lixeira do card
  // ══════════════════════════════════════════════════
  document.addEventListener('click', (e) => {
    if (e.target.closest('.btn-remover-card')) {
      const id = e.target.closest('.btn-remover-card').dataset.id;
      produtos = produtos.filter(p => p.id !== id);
      renderizarCards();
      atualizarInputsHidden();
    }
  });

  // ══════════════════════════════════════════════════
  // RENDERIZAR CARDS
  // Mostra os produtos adicionados como cards
  // Linha sólida = produto normal | tracejada = sem estoque
  // ══════════════════════════════════════════════════
  function renderizarCards() {
    const lista = document.getElementById('lista-produtos');
    const msgVazio = document.getElementById('msg-vazio');
    lista.innerHTML = '';

    if (produtos.length === 0) {
      msgVazio.style.display = 'block';
      return;
    }

    msgVazio.style.display = 'none';

    produtos.forEach(p => {
      lista.innerHTML += `
        <div class="col-sm-6">
          <div class="card h-100">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <div class="fw-semibold small">${p.nome}</div>
                  ${p.codigo
                    ? `<div class="text-muted" style="font-size:0.75rem; font-family: monospace;">${p.codigo}</div>`
                    : ''}
                </div>
                <button type="button"
                  class="btn btn-sm btn-outline-danger btn-remover-card"
                  data-id="${p.id}">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
              <div class="mt-2 fw-bold" style="color: #2422b1;">
                ${p.quantidade} ${p.unidade}
              </div>
            </div>
          </div>
        </div>`;
    });
  }

  // ══════════════════════════════════════════════════
  // INPUTS HIDDEN
  // Sincroniza a lista com inputs ocultos para envio do form
  // ══════════════════════════════════════════════════
  function atualizarInputsHidden() {
    const container = document.getElementById('inputs-hidden');
    container.innerHTML = '';
    produtos.forEach(p => {
      container.innerHTML += `<input type="hidden" name="produto_id" value="${p.id}">`;
      container.innerHTML += `<input type="hidden" name="quantidade" value="${p.quantidade}">`;
    });
  }

  // ══════════════════════════════════════════════════
  // VALIDAÇÃO AO SUBMETER
  // Impede envio se nenhum produto foi adicionado
  // ══════════════════════════════════════════════════
  document.getElementById('form-ordem').addEventListener('submit', (e) => {
    if (produtos.length === 0) {
      e.preventDefault();
      mostrarErro('Adicione pelo menos um produto antes de enviar.');
      window.scrollTo({ top: document.getElementById('alerta-erro').offsetTop - 100, behavior: 'smooth' });
    }
  });

  // ══════════════════════════════════════════════════
  // HELPERS
  // ══════════════════════════════════════════════════
  function mostrarErro(msg) {
    const el = document.getElementById('alerta-erro');
    el.textContent = msg;
    el.style.display = 'block';
  }

  function esconderErro() {
    document.getElementById('alerta-erro').style.display = 'none';
  }

});