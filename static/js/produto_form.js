document.addEventListener('DOMContentLoaded', () => {
  const categoriaSelect = document.getElementById('id_categoria');
  const camposChapa = document.getElementById('campos-chapa');
  const camposBasicos = document.getElementById('campos-basicos');
  const campoEspessuraPF = document.getElementById('campo-espessura-pf');

  function setCamposDisabled(container, disabled) {
    container.querySelectorAll('input, select').forEach(campo => {
      campo.disabled = disabled;
    });
  }

  function atualizarCampos() {
    const categoria = categoriaSelect.value;

    if (categoria === 'chapa') {
      camposChapa.style.display = 'block';
      camposBasicos.style.display = 'none';
      setCamposDisabled(camposChapa, false);
      setCamposDisabled(camposBasicos, true);
    } else if (categoria === 'produto_final') {
      camposChapa.style.display = 'none';
      camposBasicos.style.display = 'block';
      campoEspessuraPF.style.display = 'block';
      setCamposDisabled(camposChapa, true);
      setCamposDisabled(camposBasicos, false);
    } else {
      camposChapa.style.display = 'none';
      camposBasicos.style.display = 'block';
      campoEspessuraPF.style.display = 'none';
      setCamposDisabled(camposChapa, true);
      setCamposDisabled(camposBasicos, false);
    }
  }

  if (categoriaSelect) {
    categoriaSelect.addEventListener('change', atualizarCampos);
    atualizarCampos();
  }
});