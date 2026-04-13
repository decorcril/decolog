document.addEventListener('DOMContentLoaded', () => {
  const produtoSelect = document.getElementById('id_produto');
  const saldoInfo = document.getElementById('saldo-info');
  const saldoLista = document.getElementById('saldo-lista');

  function carregarSaldo() {
    const produtoId = produtoSelect.value;

    if (!produtoId) {
      saldoInfo.style.display = 'none';
      return;
    }

    fetch(`/estoque/saldo/${produtoId}/`)
      .then(res => res.json())
      .then(data => {
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

  if (produtoSelect) {
    produtoSelect.addEventListener('change', carregarSaldo);
    if (produtoSelect.value) carregarSaldo();
  }
});