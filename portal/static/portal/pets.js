(function () {
  'use strict';

  var modal = document.getElementById('petModal');
  var openBtn = document.getElementById('fabOpen');
  var closeBtn = document.getElementById('cancelModal');
  var cancelBtn = document.getElementById('cancelModal2');
  var salvarBtn = document.getElementById('salvarPet');
  var form = document.getElementById('petForm');
  var formMsg = document.getElementById('petFormMsg');

  function showFormMsg(type, text) {
    if (!formMsg) return;
    formMsg.className = 'alert alert-' + type;
    formMsg.textContent = text;
    formMsg.style.display = 'block';
  }

  function clearFormMsg() {
    if (!formMsg) return;
    formMsg.style.display = 'none';
    formMsg.textContent = '';
    formMsg.className = '';
  }

  function openModal() {
    if (!modal) return;
    modal.classList.add('open');
    document.body.classList.add('modal-open');
    clearFormMsg();

    window.setTimeout(function () {
      var first = form && form.querySelector('[name="nome"]');
      if (first) first.focus();
    }, 50);
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    document.body.classList.remove('modal-open');
    clearFormMsg();
  }

  function fieldValue(name) {
    var input = form && form.querySelector('[name="' + name + '"]');
    return input ? input.value : '';
  }

  function numberOrNull(value, parser) {
    if (value === '' || value === null || typeof value === 'undefined') return null;
    var parsed = parser(value);
    return isNaN(parsed) ? null : parsed;
  }

  function setSaving(isSaving) {
    if (!salvarBtn) return;
    salvarBtn.disabled = isSaving;
    salvarBtn.textContent = isSaving ? 'Salvando...' : 'Salvar pet';
  }

  if (openBtn) openBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  if (modal) {
    modal.addEventListener('click', function (event) {
      if (event.target === modal) closeModal();
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && modal.classList.contains('open')) closeModal();
    });
  }

  if (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (salvarBtn) salvarBtn.click();
    });
  }

  if (salvarBtn && form) {
    salvarBtn.addEventListener('click', function () {
      var url = window.PORTAL && window.PORTAL.criarPetUrl;
      var token = window.PORTAL && window.PORTAL.csrfToken;
      var nome = fieldValue('nome').trim();
      var tipo = fieldValue('tipo');

      if (!url) {
        showFormMsg('error', 'Configuração inválida. Recarregue a página.');
        return;
      }

      if (!nome) {
        showFormMsg('error', 'Informe o nome do animal.');
        var nomeInput = form.querySelector('[name="nome"]');
        if (nomeInput) nomeInput.focus();
        return;
      }

      if (!tipo) {
        showFormMsg('error', 'Selecione o tipo do animal.');
        var tipoInput = form.querySelector('[name="tipo"]');
        if (tipoInput) tipoInput.focus();
        return;
      }

      var raca = fieldValue('raca').trim();
      var payload = {
        usuario_uuid: fieldValue('usuario_uuid'),
        nome: nome,
        tipo: tipo,
        sexo: fieldValue('sexo') || null,
        raca: raca || null,
        idade: numberOrNull(fieldValue('idade'), function (value) { return parseInt(value, 10); }),
        peso: numberOrNull(fieldValue('peso'), parseFloat),
        altura: numberOrNull(fieldValue('altura'), parseFloat)
      };

      setSaving(true);
      clearFormMsg();

      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': token || ''
        },
        body: JSON.stringify(payload)
      })
      .then(function (response) {
        return response.json().catch(function () {
          return {};
        }).then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.ok) {
          window.location.reload();
          return;
        }

        showFormMsg('error', result.data.erro || result.data.detail || 'Erro ao salvar pet. Tente novamente.');
        setSaving(false);
      })
      .catch(function () {
        showFormMsg('error', 'Erro de conexão. Verifique sua rede e tente novamente.');
        setSaving(false);
      });
    });
  }
}());
