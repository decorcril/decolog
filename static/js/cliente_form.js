const paisSelect = document.getElementById('id_pais');
const camposBR   = document.getElementById('campos_br');
const camposIntl = document.getElementById('campos_intl');
const cep        = document.getElementById('id_cep');
const tipoPessoa = document.getElementById('id_tipo_pessoa');
const labelDoc   = document.getElementById('label_documento');
// Auto preenchimento por CEP
cep.addEventListener('blur', async function () {
  const valor = cep.value.replace(/\D/g, '');
  if (valor.length !== 8) return;

  try {
    const response = await fetch(`https://viacep.com.br/ws/${valor}/json/`);
    const data = await response.json();

    if (data.erro) {
      alert('CEP não encontrado.');
      return;
    }

    document.getElementById('id_logradouro').value = data.logradouro || '';
    document.getElementById('id_bairro').value     = data.bairro     || '';
    document.getElementById('id_cidade').value     = data.localidade || '';
    document.getElementById('id_estado').value     = data.uf         || '';

  } catch (e) {
    console.error('Erro ao buscar CEP:', e);
  }
});

const itiConfig = {
  initialCountry: paisSelect.value.toLowerCase() || 'br',
  separateDialCode: true,
  preferredCountries: ['br', 'ar', 'cl', 'py', 'uy', 'us'],
  utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@23/build/js/utils.js',
};

const itiTelefone = window.intlTelInput(document.getElementById('id_telefone'), itiConfig);
const itiWhatsapp = window.intlTelInput(document.getElementById('id_whatsapp'), itiConfig);

function isBrasil() {
  return paisSelect.value === 'BR';
}

function sincronizarPais() {
  const codigo = paisSelect.value.toLowerCase();
  itiTelefone.setCountry(codigo);
  itiWhatsapp.setCountry(codigo);
}

function atualizarCampos() {
  if (isBrasil()) {
    camposBR.style.removeProperty('display');
    camposIntl.style.setProperty('display', 'none', 'important');
    cep.setAttribute('data-mask', '00000-000');
    labelDoc.textContent = tipoPessoa.value === 'PF' ? 'CPF' : 'CNPJ';
  } else {
    camposBR.style.setProperty('display', 'none', 'important');
    camposIntl.style.removeProperty('display');
    cep.removeAttribute('data-mask');
    labelDoc.textContent = 'Documento';
  }
  if (typeof initMasks === 'function') initMasks();
  sincronizarPais();
}

// Ao submeter, salva o número completo com DDI
document.querySelector('form').addEventListener('submit', function () {
  const telEl = document.getElementById('id_telefone');
  const waEl  = document.getElementById('id_whatsapp');
  // Só substitui se o utils já carregou e o número for válido
  if (itiTelefone.getNumber) {
    const tel = itiTelefone.getNumber();
    if (tel) telEl.value = tel;
  }
  if (itiWhatsapp.getNumber) {
    const wa = itiWhatsapp.getNumber();
    if (wa) waEl.value = wa;
  }
});

paisSelect.addEventListener('change', atualizarCampos);
tipoPessoa.addEventListener('change', () => {
  if (isBrasil()) {
    labelDoc.textContent = tipoPessoa.value === 'PF' ? 'CPF' : 'CNPJ';
  }
});

atualizarCampos();