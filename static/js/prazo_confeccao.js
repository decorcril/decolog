document.addEventListener('DOMContentLoaded', function () {
  var select = document.getElementById('id_prazo_confeccao');
  var aviso  = document.getElementById('aviso_pronta_entrega');
  if (!select || !aviso) return;

  function atualizarAviso() {
    aviso.style.display = (select.value === 'pronta') ? 'block' : 'none';
  }

  select.addEventListener('change', atualizarAviso);
  atualizarAviso(); // já mostra certo se abrir a edição com "pronta" já selecionado
});