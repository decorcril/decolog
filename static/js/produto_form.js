document.addEventListener('DOMContentLoaded', () => {
  const categoriaSelect = document.getElementById('id_categoria');
  const campoCorEspessura = document.getElementById('campos-cor-espessura');
  const campoDimensoes = document.getElementById('campos-dimensoes');

  function atualizarCampos() {
    const categoria = categoriaSelect.value;

    if (categoria === 'insumo') {
      campoCorEspessura.style.display = 'none';
      campoDimensoes.style.display = 'none';
    } else if (categoria === 'chapa') {
      campoCorEspessura.style.display = 'flex';
      campoDimensoes.style.display = 'block';
    } else if (categoria === 'produto_final') {
      campoCorEspessura.style.display = 'flex';
      campoDimensoes.style.display = 'block';
    } else {
      campoCorEspessura.style.display = 'none';
      campoDimensoes.style.display = 'none';
    }
  }

  if (categoriaSelect) {
    categoriaSelect.addEventListener('change', atualizarCampos);
    atualizarCampos();
  }
});