document.addEventListener('DOMContentLoaded', () => {
  const produtoSelect = document.getElementById('id_produto');
  const localSelect = document.getElementById('id_local');
  const saldoInfo = document.getElementById('saldo-info');
  const saldoValor = document.getElementById('saldo-valor');

  function carregarSaldo() {
    const produtoId = produtoSelect.value;
    const localId = localSelect.value;

    if (!produtoId || !localId) {
      saldoInfo.style.display = 'none';
      return;
    }

    fetch(`/estoque/saldo/${produtoId}/`)
      .then(res => res.json())
      .then(data => {
        const saldo = data.saldos.find(s => s.local_id == localId);
        if (saldo) {
          saldoValor.textContent = saldo.quantidade;
        } else {
          saldoValor.textContent = '0 (sem registro)';
        }
        saldoInfo.style.display = 'block';
      });
  }

  if (produtoSelect) produtoSelect.addEventListener('change', carregarSaldo);
  if (localSelect) localSelect.addEventListener('change', carregarSaldo);
});