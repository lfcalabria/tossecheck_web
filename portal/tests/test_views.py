import uuid
import requests
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest.mock import patch

PET_UUID = str(uuid.uuid4())


class TestLoginViews(TestCase):
    def setUp(self):
        self.client = self.client_class()
        self.login_url = reverse('portal:login')
        self.responsavel_url = reverse('portal:responsavel')

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/login.html')

    def test_login_view_get_with_auth_redirects(self):
        session = self.client.session
        session['vet_uuid'] = 'some-uuid'
        session.save()
        response = self.client.get(self.login_url)
        self.assertRedirects(response, self.responsavel_url)

    @patch('portal.views.requests.post')
    def test_login_view_post_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "token": "abc123",
            "veterinario": {"nome": "Dr. João"}
        }
        response = self.client.post(self.login_url, {'crmv': '123', 'senha': 'pass'})
        self.assertRedirects(response, self.responsavel_url)
        session = self.client.session
        self.assertIn('vet_uuid', session)
        self.assertIn('vet_nome', session)
        self.assertEqual(session['vet_nome'], 'Dr. João')

    @patch('portal.views.requests.post')
    def test_login_view_post_invalid_credentials(self, mock_post):
        mock_post.return_value.status_code = 401
        mock_post.return_value.json.return_value = {"erro": "Credenciais inválidas"}
        response = self.client.post(self.login_url, {'crmv': '123', 'senha': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/login.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Credenciais inválidas" in str(m) for m in messages))

    def test_login_view_post_invalid_form(self):
        response = self.client.post(self.login_url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/login.html')
        self.assertFalse(response.context['form'].is_valid())

    @patch('portal.views.requests.post')
    def test_login_view_post_backend_down(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Connection error")
        response = self.client.post(self.login_url, {'crmv': '123', 'senha': 'pass'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/login.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro ao conectar com o backend" in str(m) for m in messages))

    def test_home_redirect(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/portal/login/')


class TestResponsavelViews(TestCase):
    @patch('portal.views.requests.get')
    def test_responsavel_buscar_server_error(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_get.return_value.status_code = 500
        mock_get.return_value.json.return_value = {"erro": "Erro interno"}
        response = self.client.post(self.responsavel_url, {
            'acao': 'buscar',
            'cpf': '529.982.247-25'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro ao buscar responsável." in str(m) for m in messages))

    def setUp(self):
        self.client = self.client_class()
        self.responsavel_url = reverse('portal:responsavel')
        self.login_url = reverse('portal:login')

    def test_responsavel_view_without_auth(self):
        response = self.client.get(self.responsavel_url)
        self.assertRedirects(response, self.login_url)

    def test_responsavel_view_get(self):
        session = self.client.session
        session['vet_uuid'] = 'some-uuid'
        session['responsavel_uuid'] = 'old-uuid'
        session['responsavel_nome'] = 'Old'
        session['responsavel_cpf'] = '00000000000'
        session.save()
        response = self.client.get(self.responsavel_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/responsavel.html')
        session = self.client.session
        self.assertNotIn('responsavel_uuid', session)
        self.assertNotIn('responsavel_nome', session)
        self.assertNotIn('responsavel_cpf', session)

    @patch('portal.views.requests.get')
    def test_responsavel_buscar_success(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "uuid": "resp-uuid",
            "nome": "Maria",
            "cpf": "52998224725"
        }
        response = self.client.post(self.responsavel_url, {
            'acao': 'buscar',
            'cpf': '529.982.247-25'
        })
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        self.assertEqual(session['responsavel_uuid'], 'resp-uuid')
        self.assertEqual(session['responsavel_nome'], 'Maria')
        self.assertEqual(session['responsavel_cpf'], '52998224725')
        self.assertTrue(response.context.get('responsavel_encontrado'))

    @patch('portal.views.requests.get')
    def test_responsavel_buscar_not_found(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_get.return_value.status_code = 404
        response = self.client.post(self.responsavel_url, {
            'acao': 'buscar',
            'cpf': '529.982.247-25'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get('mostrar_cadastro'))
        self.assertEqual(
            response.context['form_cadastro'].initial.get('cpf'),
            '52998224725'
        )

    @patch('portal.views.requests.get')
    def test_responsavel_buscar_api_down(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_get.side_effect = requests.ConnectionError("Backend unreachable")
        response = self.client.post(self.responsavel_url, {
            'acao': 'buscar',
            'cpf': '529.982.247-25'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro" in str(m) for m in messages))

    @patch('portal.views.requests.post')
    def test_responsavel_cadastrar_success(self, mock_post):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "uuid": "new-uuid",
            "nome": "João",
            "cpf": "52998224725"
        }
        response = self.client.post(self.responsavel_url, {
            'acao': 'cadastrar',
            'nome': 'João',
            'cpf': '529.982.247-25',
            'telefone': '11999999999'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("sucesso" in str(m).lower() for m in messages))
        session = self.client.session
        self.assertEqual(session['responsavel_uuid'], 'new-uuid')

    @patch('portal.views.requests.post')
    def test_responsavel_cadastrar_request_exception(self, mock_post):
        """Força RequestException no requests.post do cadastrar"""
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_post.side_effect = requests.RequestException("Erro ao cadastrar - API fora")
        response = self.client.post(self.responsavel_url, {
            'acao': 'cadastrar',
            'nome': 'João',
            'cpf': '529.982.247-25',
            'telefone': '11999999999'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro ao conectar com a API" in str(m) for m in messages))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/responsavel.html')

    @patch('portal.views.requests.get')
    def test_responsavel_buscar_request_exception(self, mock_get):
        """Testa o except requests.RequestException direto (não apenas subclasse)"""
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_get.side_effect = requests.RequestException("Erro genérico de conexão")
        response = self.client.post(self.responsavel_url, {
            'acao': 'buscar',
            'cpf': '529.982.247-25'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro ao conectar com a API" in str(m) for m in messages))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/responsavel.html')

    @patch('portal.views.requests.post')
    def test_responsavel_cadastrar_failure(self, mock_post):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"erro": "Dados inválidos"}
        response = self.client.post(self.responsavel_url, {
            'acao': 'cadastrar',
            'nome': 'João',
            'cpf': '529.982.247-25',
            'telefone': '11999999999'
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro ao cadastrar responsável" in str(m) for m in messages))

    def test_responsavel_prosseguir(self):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session['responsavel_uuid'] = 'resp-uuid'
        session.save()
        response = self.client.post(self.responsavel_url, {'acao': 'prosseguir'})
        self.assertRedirects(response, reverse('portal:pets'), fetch_redirect_response=False)


class TestPetViews(TestCase):
    def setUp(self):
        self.client = self.client_class()
        self.pets_url = reverse('portal:pets')
        self.criar_pet_url = reverse('portal:criar_pet')
        self.responsavel_url = reverse('portal:responsavel')
        self.login_url = reverse('portal:login')

    def test_criar_pet_sem_responsavel(self):
        """Cobre messages.error + redirect p/ portal:pets quando não há responsável"""
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()

        # Removido o follow=True para ele parar no primeiro redirect
        response = self.client.post(self.criar_pet_url, {
            'nome': 'Rex',
            'tipo': 'cachorro'
        })

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Responsável não definido" in str(m) for m in messages),
            "A mensagem de erro não foi gerada."
        )

        # fetch_redirect_response=False evita que o assert tente carregar a próxima página
        self.assertRedirects(response, self.pets_url, fetch_redirect_response=False)

    def test_pets_view_without_auth(self):
        response = self.client.get(self.pets_url)
        self.assertRedirects(response, self.login_url)

    def test_pets_view_without_responsavel(self):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        response = self.client.get(self.pets_url)
        self.assertRedirects(response, self.responsavel_url)

    @patch('portal.views.requests.get')
    def test_pets_view_success(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session['responsavel_uuid'] = 'resp-uuid'
        session.save()
        mock_get.return_value.status_code = 200
        # ✅ CORREÇÃO 1: adicionado "uuid": PET_UUID para o template renderizar o link
        mock_get.return_value.json.return_value = {
            "pets": [{"uuid": PET_UUID, "nome": "Rex", "tipo": "cachorro"}]
        }
        response = self.client.get(self.pets_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/pets.html')
        self.assertEqual(len(response.context['pets']), 1)

    @patch('portal.views.requests.get')
    def test_pets_view_api_down(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session['responsavel_uuid'] = 'resp-uuid'
        session.save()
        mock_get.side_effect = requests.ConnectionError("Backend error")
        response = self.client.get(self.pets_url)
        self.assertRedirects(response, self.responsavel_url, fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro" in str(m) for m in messages))

    def test_criar_pet_without_auth(self):
        response = self.client.post(self.criar_pet_url, {'nome': 'Rex', 'tipo': 'cachorro'})
        self.assertRedirects(response, self.login_url)

    @patch('portal.views.requests.post')
    def test_criar_pet_success(self, mock_post):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session['responsavel_uuid'] = 'resp-uuid'
        session.save()
        mock_post.return_value.status_code = 201
        response = self.client.post(self.criar_pet_url, {
            'nome': 'Rex',
            'tipo': 'cachorro'
        })
        self.assertRedirects(response, self.pets_url, fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("sucesso" in str(m).lower() for m in messages))

    @patch('portal.views.requests.post')
    def test_criar_pet_backend_error(self, mock_post):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session['responsavel_uuid'] = 'resp-uuid'
        session.save()
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"erro": "Dados inválidos"}
        response = self.client.post(self.criar_pet_url, {
            'nome': '',
            'tipo': ''
        })
        self.assertRedirects(response, self.pets_url, fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Dados inválidos" in str(m) for m in messages))

    @patch('portal.views.requests.post')
    def test_criar_pet_backend_down(self, mock_post):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session['responsavel_uuid'] = 'resp-uuid'
        session.save()
        mock_post.side_effect = requests.ConnectionError("Connection error")
        response = self.client.post(self.criar_pet_url, {
            'nome': 'Rex',
            'tipo': 'cachorro'
        })
        self.assertRedirects(response, self.pets_url, fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro" in str(m) for m in messages))

    def test_pet_detalhe_without_auth(self):
        response = self.client.get(reverse('portal:pet_detalhe', args=[PET_UUID]))
        self.assertRedirects(response, self.login_url)

    @patch('portal.views.requests.get')
    def test_pet_detalhe_success(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        pet_uuid = PET_UUID
        mock_get.return_value.status_code = 200
        # ✅ CORREÇÃO 2: mock retorna um dict de pet único, não {"pets": [...]}
        mock_get.return_value.json.return_value = {"uuid": PET_UUID, "nome": "Rex"}
        response = self.client.get(reverse('portal:pet_detalhe', args=[pet_uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/pet_detalhe.html')
        self.assertEqual(response.context['pet']['nome'], 'Rex')

    @patch('portal.views.requests.get')
    def test_pet_detalhe_not_found(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = {"erro": "Pet não encontrado"}
        response = self.client.get(reverse('portal:pet_detalhe', args=[PET_UUID]))
        self.assertRedirects(response, self.pets_url, fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Pet não encontrado" in str(m) for m in messages))

    @patch('portal.views.requests.get')
    def test_pet_detalhe_backend_down(self, mock_get):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_get.side_effect = requests.ConnectionError("Backend error")
        response = self.client.get(reverse('portal:pet_detalhe', args=[PET_UUID]))
        self.assertRedirects(response, self.pets_url, fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erro" in str(m) for m in messages))

    @patch('portal.views.requests.get')
    def test_pet_detalhe_videos_data_upload(self, mock_get):
        """Cobre parse_data_upload: data válida, ausente, None, vazia e formato inválido"""
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "uuid": PET_UUID,
            "nome": "Rex",
            "videos": [
                {"id": 1, "data_upload": "15/05/2026 14:30"},  # ✅ strptime OK
                {"id": 2},  # ❌ sem chave → if not s
                {"id": 3, "data_upload": None},  # ❌ None → if not s
                {"id": 4, "data_upload": ""},  # ❌ vazio → if not s
                {"id": 5, "data_upload": "invalido"},  # ❌ ValueError
            ]
        }

        response = self.client.get(reverse('portal:pet_detalhe', args=[PET_UUID]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/pet_detalhe.html')
        self.assertEqual(len(response.context['pet']['videos']), 5)

        # Ordenação reverse: vídeo com data válida (2026) vem primeiro
        self.assertEqual(response.context['pet']['videos'][0]["id"], 1)
        self.assertEqual(response.context['pet']['videos'][1]["id"], 2)

class TestLogoutView(TestCase):
    def test_logout_view(self):
        session = self.client.session
        session['vet_uuid'] = 'some-uuid'
        session.save()
        response = self.client.get(reverse('portal:logout'))
        self.assertRedirects(response, reverse('portal:login'), fetch_redirect_response=False)
        self.assertNotIn('vet_uuid', self.client.session)

class TestProxyViews(TestCase):
    def setUp(self):
        self.client = self.client_class()
        self.proxy_pets_url = reverse('portal:proxy_pets')
        self.proxy_observacao_url = reverse('portal:proxy_pet_observacao', args=[PET_UUID])

    def test_proxy_pets_without_auth(self):
        response = self.client.post(self.proxy_pets_url, {})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"erro": "Não autenticado."})

    @patch('portal.views.requests.post')
    def test_proxy_pets_success(self, mock_post):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"uuid": "new-pet-uuid"}
        response = self.client.post(self.proxy_pets_url, {
            'nome': 'Rex',
            'tipo': 'cachorro'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"uuid": "new-pet-uuid"})

    def test_proxy_pet_observacao_without_auth(self):
        response = self.client.post(self.proxy_observacao_url, {})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"erro": "Não autenticado."})

    @patch('portal.views.requests.post')
    def test_proxy_pet_observacao_success(self, mock_post):
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 1, "texto": "Observação"}
        response = self.client.post(self.proxy_observacao_url, {
            'texto': 'Observação'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"id": 1, "texto": "Observação"})

    def test_proxy_pets_invalid_json(self):
        """Dispara except Exception no json.loads do proxy_pets"""
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        # Envia bytes inválidos para forçar exceção no json.loads
        response = self.client.post(
            self.proxy_pets_url,
            data='{"quebrado": }',  # ← JSON intencionalmente inválido
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"erro": "JSON inválido."})

    def test_proxy_pet_observacao_invalid_json(self):
        """Dispara except Exception no json.loads do proxy_pet_observacao"""
        session = self.client.session
        session['vet_uuid'] = 'vet-uuid'
        session.save()
        response = self.client.post(
            self.proxy_observacao_url,
            data='{"quebrado": }',  # ← JSON intencionalmente inválido
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"erro": "JSON inválido."})