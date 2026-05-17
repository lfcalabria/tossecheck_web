(function () {
  'use strict';

  /* ── Modal de cadastro de pet ── */
  var modal   = document.getElementById('petModal');
  var fab     = document.getElementById('fabOpen');
  var cancel1 = document.getElementById('cancelModal');
  var cancel2 = document.getElementById('cancelModal2');
  var salvarBtn = document.getElementById('salvarPet');
  var form    = document.getElementById('petForm');
  var formMsg = document.getElementById('petFormMsg');

  function openModal() {
    if (modal) modal.classList.add('open');
  }

  function closeModal() {
    if (modal) {
      modal.classList.remove('open');
      if (formMsg) { formMsg.style.display = 'none'; formMsg.textContent = ''; }
    }
  }

  function showFormMsg(type, text) {
    if (!formMsg) return;
    formMsg.className = 'alert alert-' + type;
    formMsg.textContent = text;
    formMsg.style.display = 'block';
  }

  if (fab)     fab.addEventListener('click', openModal);
  if (cancel1) cancel1.addEventListener('click', closeModal);
  if (cancel2) cancel2.addEventListener('click', closeModal);

  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('open')) closeModal();
    });
  }

  if (salvarBtn && form) {
    salvarBtn.addEventListener('click', function () {
      var url   = window.PORTAL && window.PORTAL.criarPetUrl;
      var token = window.PORTAL && window.PORTAL.csrfToken;

      if (!url) {
        showFormMsg('error', 'Configuração inválida. Recarregue a página.');
        return;
      }

      var nome   = (form.querySelector('[name="nome"]')   || {}).value || '';
      var tipo   = (form.querySelector('[name="tipo"]')   || {}).value || '';
      var uuid   = (form.querySelector('[name="usuario_uuid"]') || {}).value || '';

      if (!nome.trim()) {
        showFormMsg('error', 'Informe o nome do animal.');
        var n = form.querySelector('[name="nome"]');
        if (n) n.focus();
        return;
      }
      if (!tipo) {
        showFormMsg('error', 'Selecione o tipo do animal (Gato ou Cachorro).');
        return;
      }

      var sexo   = (form.querySelector('[name="sexo"]')   || {}).value || null;
      var raca   = (form.querySelector('[name="raca"]')   || {}).value || null;
      var idade  = (form.querySelector('[name="idade"]')  || {}).value;
      var peso   = (form.querySelector('[name="peso"]')   || {}).value;
      var altura = (form.querySelector('[name="altura"]') || {}).value;

      var payload = {
        usuario_uuid: uuid,
        nome: nome.trim(),
        tipo: tipo,
        sexo: sexo || null,
        raca: raca ? raca.trim() || null : null,
        idade:  idade  ? parseInt(idade,  10) : null,
        peso:   peso   ? parseFloat(peso)     : null,
        altura: altura ? parseFloat(altura)   : null
      };

      salvarBtn.disabled = true;
      salvarBtn.textContent = 'Salvando…';
      if (formMsg) formMsg.style.display = 'none';

      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': token || ''
        },
        body: JSON.stringify(payload)
      })
      .then(function (r) {
        if (r.ok) {
          location.reload();
        } else {
          r.json().then(function (data) {
            showFormMsg('error', data.erro || data.detail || 'Erro ao salvar pet. Tente novamente.');
          }).catch(function () {
            showFormMsg('error', 'Erro ao salvar pet. Tente novamente.');
          });
          salvarBtn.disabled = false;
          salvarBtn.textContent = 'Salvar Pet';
        }
      })
      .catch(function () {
        showFormMsg('error', 'Erro de conexão. Verifique sua rede e tente novamente.');
        salvarBtn.disabled = false;
        salvarBtn.textContent = 'Salvar Pet';
      });
    });
  }

}());
