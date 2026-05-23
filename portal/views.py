import json
import re
import requests
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from .forms import LoginForm, BuscarResponsavelForm, CadastroResponsavelForm


# =====================================================
# CONFIGURAÇÃO
# =====================================================
BACKEND_URL = getattr(
    settings,
    "BACKEND_API_URL",
    "http://127.0.0.1:8000/api/v1"
).rstrip("/")

BACKEND_BASE_URL = BACKEND_URL.replace("/api/v1", "")


# =====================================================
# UTILITÁRIOS
# =====================================================

def normalizar_cpf(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def safe_json(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return None


def formatar_cpf(valor: str) -> str:
    digits = normalizar_cpf(valor)
    if len(digits) != 11:
        return valor or ""
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


# =====================================================
# MODO DEMO LOCAL
# =====================================================

DEMO_VET = {
    "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "nome": "Dra. Clara Nunes",
    "crmv": "123456",
    "senha": "123456",
}


def demo_data_padrao():
    return {
        "responsaveis": [
            {
                "uuid": "22222222-2222-2222-2222-222222222222",
                "nome": "Mariana Lima",
                "cpf": "52998224725",
                "telefone": "(81) 99999-0000",
                "pets": [
                    {
                        "uuid": "11111111-1111-1111-1111-111111111111",
                        "nome": "Rex",
                        "tipo": "Cachorro",
                        "sexo": "Macho",
                        "raca": "SRD",
                        "idade": 4,
                        "peso": "12.50",
                        "altura": "45.00",
                        "videos": [],
                        "prontuario": [
                            {
                                "veterinario": DEMO_VET["nome"],
                                "data": "23/05/2026 14:30",
                                "texto": "Paciente ativo, com tosse seca ocasional relatada pelo tutor.",
                            },
                            {
                                "veterinario": DEMO_VET["nome"],
                                "data": "21/05/2026 09:15",
                                "texto": "Tutor orientado a observar frequencia da tosse e enviar novos videos.",
                            },
                        ],
                    },
                    {
                        "uuid": "33333333-3333-3333-3333-333333333333",
                        "nome": "Luna",
                        "tipo": "Gato",
                        "sexo": "Femea",
                        "raca": "Siamese",
                        "idade": 2,
                        "peso": "4.20",
                        "altura": "25.00",
                        "videos": [],
                        "prontuario": [],
                    },
                ],
            },
            {
                "uuid": "44444444-4444-4444-4444-444444444444",
                "nome": "Carlos Duarte",
                "cpf": "28664081068",
                "telefone": "(81) 98888-1111",
                "pets": [
                    {
                        "uuid": "55555555-5555-5555-5555-555555555555",
                        "nome": "Mel",
                        "tipo": "Cachorro",
                        "sexo": "Femea",
                        "raca": "Shih-tzu",
                        "idade": 6,
                        "peso": "6.80",
                        "altura": "28.00",
                        "videos": [],
                        "prontuario": [
                            {
                                "veterinario": DEMO_VET["nome"],
                                "data": "18/05/2026 16:40",
                                "texto": "Animal com historico de tosse apos exercicio. Acompanhamento recomendado.",
                            }
                        ],
                    }
                ],
            },
        ]
    }


def modo_demo_ativo(request) -> bool:
    return request.session.get("demo_mode") is True


def garantir_dados_demo(request):
    if not request.session.get("demo_data"):
        request.session["demo_data"] = demo_data_padrao()
    return request.session["demo_data"]


def salvar_dados_demo(request, data):
    request.session["demo_data"] = data
    request.session.modified = True


def buscar_responsavel_demo(data, *, cpf=None, responsavel_uuid=None):
    cpf = normalizar_cpf(cpf) if cpf else None
    responsavel_uuid = str(responsavel_uuid) if responsavel_uuid else None

    for responsavel in data.get("responsaveis", []):
        if cpf and normalizar_cpf(responsavel.get("cpf")) == cpf:
            return responsavel
        if responsavel_uuid and str(responsavel.get("uuid")) == responsavel_uuid:
            return responsavel
    return None


def buscar_pet_demo(data, pet_uuid):
    pet_uuid = str(pet_uuid)
    for responsavel in data.get("responsaveis", []):
        for pet in responsavel.get("pets", []):
            if str(pet.get("uuid")) == pet_uuid:
                return responsavel, pet
    return None, None


def payload_request(request):
    content_type = request.META.get("CONTENT_TYPE", "")
    if "application/json" in content_type:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            return {}
    return request.POST.dict()


def demo_start(request):
    request.session.flush()
    request.session["demo_mode"] = True
    request.session["demo_data"] = demo_data_padrao()
    return redirect("portal:login")


def demo_login(request, form):
    if request.method == "POST" and form.is_valid():
        crmv = (form.cleaned_data["crmv"] or "").strip()
        senha = form.cleaned_data["senha"]

        if crmv == DEMO_VET["crmv"] and senha == DEMO_VET["senha"]:
            garantir_dados_demo(request)
            request.session["vet_uuid"] = DEMO_VET["uuid"]
            request.session["vet_nome"] = DEMO_VET["nome"]
            return redirect("portal:responsavel")

        messages.error(request, "Login invalido no modo demo.")

    return render(request, "portal/login.html", {"form": form})


def contexto_responsavel_demo(request, **overrides):
    contexto = {
        "vet_nome": request.session.get("vet_nome"),
        "form_busca": BuscarResponsavelForm(initial={"cpf": "529.982.247-25"}),
        "form_cadastro": CadastroResponsavelForm(),
        "responsavel_encontrado": False,
        "mostrar_cadastro": False,
        "responsavel_nome": None,
        "responsavel_cpf": None,
    }
    contexto.update(overrides)
    return contexto


def demo_responsavel_view(request):
    if not request.session.get("vet_uuid"):
        return redirect("portal:login")

    data = garantir_dados_demo(request)

    if request.method == "GET":
        request.session.pop("responsavel_uuid", None)
        request.session.pop("responsavel_nome", None)
        request.session.pop("responsavel_cpf", None)

    contexto = contexto_responsavel_demo(request)

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "buscar":
            form = BuscarResponsavelForm(request.POST)
            contexto["form_busca"] = form

            if form.is_valid():
                cpf = normalizar_cpf(form.cleaned_data["cpf"])
                responsavel = buscar_responsavel_demo(data, cpf=cpf)

                if responsavel:
                    request.session["responsavel_uuid"] = responsavel.get("uuid")
                    request.session["responsavel_nome"] = responsavel.get("nome")
                    request.session["responsavel_cpf"] = responsavel.get("cpf")

                    contexto.update(
                        {
                            "responsavel_encontrado": True,
                            "responsavel_nome": responsavel.get("nome"),
                            "responsavel_cpf": formatar_cpf(responsavel.get("cpf")),
                        }
                    )
                else:
                    contexto["mostrar_cadastro"] = True
                    contexto["form_cadastro"] = CadastroResponsavelForm(
                        initial={"cpf": formatar_cpf(cpf)}
                    )
                    messages.info(request, "Responsavel nao encontrado. Cadastre abaixo.")

        elif acao == "cadastrar":
            form = CadastroResponsavelForm(request.POST)
            contexto["form_cadastro"] = form
            contexto["mostrar_cadastro"] = True

            if form.is_valid():
                responsavel = {
                    "uuid": str(uuid.uuid4()),
                    "nome": form.cleaned_data["nome"],
                    "cpf": normalizar_cpf(form.cleaned_data["cpf"]),
                    "telefone": form.cleaned_data["telefone"],
                    "pets": [],
                }
                data["responsaveis"].append(responsavel)
                salvar_dados_demo(request, data)

                request.session["responsavel_uuid"] = responsavel["uuid"]
                request.session["responsavel_nome"] = responsavel["nome"]
                request.session["responsavel_cpf"] = responsavel["cpf"]

                contexto.update(
                    {
                        "responsavel_encontrado": True,
                        "mostrar_cadastro": False,
                        "responsavel_nome": responsavel["nome"],
                        "responsavel_cpf": formatar_cpf(responsavel["cpf"]),
                    }
                )
                messages.success(request, "Responsavel cadastrado no modo demo.")

        elif acao == "prosseguir":
            return redirect("portal:pets")

    return render(request, "portal/responsavel.html", contexto)


def demo_pets_view(request):
    if not request.session.get("vet_uuid"):
        return redirect("portal:login")

    responsavel_uuid = request.session.get("responsavel_uuid")
    if not responsavel_uuid:
        return redirect("portal:responsavel")

    data = garantir_dados_demo(request)
    responsavel = buscar_responsavel_demo(data, responsavel_uuid=responsavel_uuid)
    if not responsavel:
        messages.error(request, "Responsavel demo nao encontrado.")
        return redirect("portal:responsavel")

    contexto = {
        "vet_nome": request.session.get("vet_nome"),
        "responsavel_nome": responsavel.get("nome"),
        "responsavel_uuid": responsavel.get("uuid"),
        "pets": responsavel.get("pets", []),
    }
    return render(request, "portal/pets.html", contexto)


def demo_criar_pet(request):
    if not request.session.get("vet_uuid"):
        return JsonResponse({"erro": "Nao autenticado."}, status=401)

    data = garantir_dados_demo(request)
    payload = payload_request(request)
    responsavel_uuid = payload.get("usuario_uuid") or request.session.get("responsavel_uuid")
    responsavel = buscar_responsavel_demo(data, responsavel_uuid=responsavel_uuid)

    if not responsavel:
        return JsonResponse({"erro": "Responsavel demo nao encontrado."}, status=404)

    nome = (payload.get("nome") or "").strip()
    tipo = payload.get("tipo")
    if not nome or not tipo:
        return JsonResponse({"erro": "Informe nome e tipo do pet."}, status=400)

    pet = {
        "uuid": str(uuid.uuid4()),
        "nome": nome,
        "tipo": tipo,
        "sexo": payload.get("sexo") or "",
        "raca": payload.get("raca") or "",
        "idade": payload.get("idade") or None,
        "peso": payload.get("peso") or None,
        "altura": payload.get("altura") or None,
        "videos": [],
        "prontuario": [],
    }
    responsavel.setdefault("pets", []).append(pet)
    salvar_dados_demo(request, data)

    return JsonResponse({"ok": True, "pet": pet}, status=201)


def demo_pet_detalhe_view(request, pet_uuid):
    if not request.session.get("vet_uuid"):
        return redirect("portal:login")

    data = garantir_dados_demo(request)
    _, pet = buscar_pet_demo(data, pet_uuid)
    if not pet:
        messages.error(request, "Pet demo nao encontrado.")
        return redirect("portal:pets")

    contexto = {
        "pet": pet,
        "proxy_pet_observacao_url": f"/portal/proxy/pets/{pet_uuid}/observacoes/",
        "BACKEND_BASE_URL": "",
    }
    return render(request, "portal/pet_detalhe.html", contexto)


def demo_proxy_pets(request):
    return demo_criar_pet(request)


def demo_proxy_pet_observacao(request, pet_uuid):
    if not request.session.get("vet_uuid"):
        return JsonResponse({"erro": "Nao autenticado."}, status=401)

    data = garantir_dados_demo(request)
    _, pet = buscar_pet_demo(data, pet_uuid)
    if not pet:
        return JsonResponse({"erro": "Pet demo nao encontrado."}, status=404)

    payload = payload_request(request)
    texto = (payload.get("texto") or "").strip()
    if not texto:
        return JsonResponse({"erro": "Informe a observacao."}, status=400)

    observacao = {
        "veterinario": request.session.get("vet_nome") or DEMO_VET["nome"],
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "texto": texto,
    }
    pet.setdefault("prontuario", []).insert(0, observacao)
    salvar_dados_demo(request, data)

    return JsonResponse({"ok": True, "observacao": observacao}, status=201)


# =====================================================
# PREVIEW DOS TEMPLATES
# =====================================================

PREVIEW_PET_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def preview_template(request, template_name="login"):
    previews = {
        "base": ("portal/base.html", {}),
        "login": (
            "portal/login.html",
            {
                "form": LoginForm(),
            },
        ),
        "responsavel": (
            "portal/responsavel.html",
            {
                "vet_nome": "Dra. Ana Souza",
                "form_busca": BuscarResponsavelForm(),
                "form_cadastro": CadastroResponsavelForm(
                    initial={
                        "cpf": "123.456.789-09",
                        "nome": "Mariana Lima",
                        "telefone": "(81) 99999-0000",
                    }
                ),
                "responsavel_encontrado": False,
                "mostrar_cadastro": False,
                "responsavel_nome": None,
                "responsavel_cpf": None,
            },
        ),
        "pets": (
            "portal/pets.html",
            {
                "vet_nome": "Dra. Ana Souza",
                "responsavel_nome": "Mariana Lima",
                "responsavel_uuid": "22222222-2222-2222-2222-222222222222",
                "pets": [
                    {
                        "uuid": PREVIEW_PET_UUID,
                        "nome": "Rex",
                        "tipo": "Cachorro",
                        "sexo": "Macho",
                    },
                    {
                        "uuid": uuid.UUID("33333333-3333-3333-3333-333333333333"),
                        "nome": "Luna",
                        "tipo": "Gato",
                        "sexo": "Femea",
                    },
                ],
            },
        ),
        "pet-detalhe": (
            "portal/pet_detalhe.html",
            {
                "pet": {
                    "uuid": PREVIEW_PET_UUID,
                    "nome": "Rex",
                    "tipo": "Cachorro",
                    "sexo": "Macho",
                    "raca": "SRD",
                    "idade": 4,
                    "peso": "12.50",
                    "altura": "45.00",
                    "videos": [
                        {
                            "url": "/media/videos/exemplo.mp4",
                            "data_upload": datetime(2026, 5, 23, 14, 30),
                        }
                    ],
                    "prontuario": [
                        {
                            "veterinario": "Dra. Ana Souza",
                            "data": "23/05/2026 14:30",
                            "texto": "Paciente ativo, com tosse seca ocasional relatada pelo tutor.",
                        }
                    ],
                },
                "proxy_pet_observacao_url": f"/portal/proxy/pets/{PREVIEW_PET_UUID}/observacoes/",
                "BACKEND_BASE_URL": "",
            },
        ),
    }

    template_info = previews.get(template_name)
    if template_info is None:
        return JsonResponse(
            {
                "erro": "Preview nao encontrado.",
                "disponiveis": list(previews.keys()),
            },
            status=404,
        )

    template_path, contexto = template_info
    return render(request, template_path, contexto)


# =====================================================
# LOGIN
# =====================================================

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.session.get("vet_uuid"):
        return redirect("portal:responsavel")

    form = LoginForm(request.POST or None)

    if modo_demo_ativo(request):
        return demo_login(request, form)

    if request.method == "POST" and form.is_valid():
        crmv = (form.cleaned_data["crmv"] or "").strip()
        senha = form.cleaned_data["senha"]

        try:
            r = requests.post(
                f"{BACKEND_URL}/login/",
                json={"crmv": crmv, "senha": senha},
                timeout=10,
            )
        except requests.RequestException:
            messages.error(request, "Erro ao conectar com o backend.")
            return render(request, "portal/login.html", {"form": form})

        data = safe_json(r) or {}

        if r.status_code == 200:
            request.session["vet_uuid"] = data.get("token")
            request.session["vet_nome"] = (data.get("veterinario") or {}).get("nome", "")
            return redirect("portal:responsavel")

        messages.error(request, data.get("erro", "Login inválido."))

    return render(request, "portal/login.html", {"form": form})


# =====================================================
# RESPONSÁVEL
# =====================================================

@require_http_methods(["GET", "POST"])
def responsavel_view(request):
    if modo_demo_ativo(request):
        return demo_responsavel_view(request)

    if not request.session.get("vet_uuid"):
        return redirect("portal:login")

    if request.method == "GET":
        request.session.pop("responsavel_uuid", None)
        request.session.pop("responsavel_nome", None)
        request.session.pop("responsavel_cpf", None)

    contexto = {
        "vet_nome": request.session.get("vet_nome"),
        "form_busca": BuscarResponsavelForm(),
        "form_cadastro": CadastroResponsavelForm(),
        "responsavel_encontrado": False,
        "mostrar_cadastro": False,
        "responsavel_nome": None,
        "responsavel_cpf": None,
    }

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "buscar":
            form = BuscarResponsavelForm(request.POST)
            contexto["form_busca"] = form

            if form.is_valid():
                cpf = normalizar_cpf(form.cleaned_data["cpf"])

                try:
                    r = requests.get(
                        f"{BACKEND_URL}/responsavel/",
                        params={"q": cpf},
                        timeout=10,
                    )
                except requests.RequestException:
                    messages.error(request, "Erro ao conectar com a API.")
                    return render(request, "portal/responsavel.html", contexto)

                data = safe_json(r)

                if r.status_code == 200 and isinstance(data, dict):
                    request.session["responsavel_uuid"] = data.get("uuid")
                    request.session["responsavel_nome"] = data.get("nome")
                    request.session["responsavel_cpf"] = data.get("cpf")

                    contexto["responsavel_encontrado"] = True
                    contexto["responsavel_nome"] = data.get("nome")
                    contexto["responsavel_cpf"] = data.get("cpf")

                elif r.status_code == 404:
                    contexto["mostrar_cadastro"] = True
                    contexto["form_cadastro"] = CadastroResponsavelForm(
                        initial={"cpf": cpf}
                    )
                    messages.info(request, "Responsável não encontrado. Cadastre abaixo.")
                else:
                    messages.error(request, "Erro ao buscar responsável.")

        elif acao == "cadastrar":
            form = CadastroResponsavelForm(request.POST)
            contexto["form_cadastro"] = form
            contexto["mostrar_cadastro"] = True

            if form.is_valid():
                payload = {
                    "nome": form.cleaned_data["nome"],
                    "cpf": normalizar_cpf(form.cleaned_data["cpf"]),
                    "telefone": form.cleaned_data["telefone"],
                }

                try:
                    r = requests.post(
                        f"{BACKEND_URL}/responsavel/",
                        json=payload,
                        timeout=10,
                    )
                except requests.RequestException:
                    messages.error(request, "Erro ao conectar com a API.")
                    return render(request, "portal/responsavel.html", contexto)

                data = safe_json(r) or {}

                if r.status_code in (200, 201):
                    request.session["responsavel_uuid"] = data.get("uuid")
                    request.session["responsavel_nome"] = data.get("nome")
                    request.session["responsavel_cpf"] = data.get("cpf")

                    contexto["responsavel_encontrado"] = True
                    contexto["responsavel_nome"] = data.get("nome")
                    contexto["responsavel_cpf"] = data.get("cpf")

                    messages.success(request, "Responsável cadastrado com sucesso.")
                else:
                    messages.error(request, "Erro ao cadastrar responsável.")

        elif acao == "prosseguir":
            return redirect("portal:pets")

    return render(request, "portal/responsavel.html", contexto)


# =====================================================
# PETS (LISTAGEM)
# =====================================================

@require_http_methods(["GET"])
def pets_view(request):
    if modo_demo_ativo(request):
        return demo_pets_view(request)

    if not request.session.get("vet_uuid"):
        return redirect("portal:login")

    responsavel_uuid = request.session.get("responsavel_uuid")
    if not responsavel_uuid:
        return redirect("portal:responsavel")

    try:
        r = requests.get(
            f"{BACKEND_URL}/responsavel/{responsavel_uuid}/pets/",
            timeout=10,
        )
    except requests.RequestException:
        messages.error(request, "Erro ao buscar pets.")
        return redirect("portal:responsavel")

    data = safe_json(r) or {}

    contexto = {
        "vet_nome": request.session.get("vet_nome"),
        "responsavel_nome": request.session.get("responsavel_nome"),
        "responsavel_uuid": responsavel_uuid,
        "pets": data.get("pets", []),
    }

    return render(request, "portal/pets.html", contexto)


# =====================================================
# ✅ CRIAÇÃO DE PET (PORTAL → BACKEND)
# =====================================================

@require_http_methods(["POST"])
@csrf_protect
def criar_pet(request):
    if modo_demo_ativo(request):
        return demo_criar_pet(request)

    if not request.session.get("vet_uuid"):
        return redirect("portal:login")

    responsavel_uuid = request.session.get("responsavel_uuid")
    if not responsavel_uuid:
        messages.error(request, "Responsável não definido.")
        return redirect("portal:pets")

    payload = {
        "usuario_uuid": responsavel_uuid,
        "nome": request.POST.get("nome"),
        "tipo": request.POST.get("tipo"),
        "sexo": request.POST.get("sexo"),
        "raca": request.POST.get("raca"),
        "idade": request.POST.get("idade"),
        "peso": request.POST.get("peso"),
        "altura": request.POST.get("altura"),
    }

    try:
        r = requests.post(
            f"{BACKEND_URL}/pets/",
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        messages.error(request, "Erro ao conectar com o backend.")
        return redirect("portal:pets")

    data = safe_json(r) or {}

    if r.status_code in (200, 201):
        messages.success(request, "Pet cadastrado com sucesso.")
    else:
        messages.error(request, data.get("erro", "Erro ao cadastrar pet."))

    return redirect("portal:pets")


# =====================================================
# PRONTUÁRIO DO PET
# =====================================================

@require_http_methods(["GET"])
def pet_detalhe_view(request, pet_uuid):
    if modo_demo_ativo(request):
        return demo_pet_detalhe_view(request, pet_uuid)

    if not request.session.get("vet_uuid"):
        return redirect("portal:login")

    try:
        r = requests.get(
            f"{BACKEND_URL}/pets/{pet_uuid}/",
            timeout=10,
        )
    except requests.RequestException:
        messages.error(request, "Erro ao conectar com o backend.")
        return redirect("portal:pets")

    if r.status_code != 200:
        data = safe_json(r)
        messages.error(request, (data or {}).get("erro", "Erro ao carregar prontuário."))
        return redirect("portal:pets")

    contexto = {
        "pet": safe_json(r),
        "proxy_pet_observacao_url": f"/portal/proxy/pets/{pet_uuid}/observacoes/",
        "BACKEND_BASE_URL": BACKEND_BASE_URL,
    }

    return render(request, "portal/pet_detalhe.html", contexto)


# =====================================================
# LOGOUT
# =====================================================

def logout_view(request):
    if modo_demo_ativo(request):
        request.session.flush()
        request.session["demo_mode"] = True
        request.session["demo_data"] = demo_data_padrao()
        return redirect("portal:login")

    request.session.flush()
    return redirect("portal:login")


# =====================================================
# PROXIES (mantidos para compatibilidade)
# =====================================================

@csrf_exempt
@require_http_methods(["POST"])
def proxy_pets(request):
    if modo_demo_ativo(request):
        return demo_proxy_pets(request)

    if not request.session.get("vet_uuid"):
        return JsonResponse({"erro": "Não autenticado."}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    r = requests.post(
        f"{BACKEND_URL}/pets/",
        json=payload,
        timeout=10,
    )

    return JsonResponse(safe_json(r) or {}, status=r.status_code)


@csrf_exempt
@require_http_methods(["POST"])
def proxy_pet_observacao(request, pet_uuid):
    if modo_demo_ativo(request):
        return demo_proxy_pet_observacao(request, pet_uuid)

    if not request.session.get("vet_uuid"):
        return JsonResponse({"erro": "Não autenticado."}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    r = requests.post(
        f"{BACKEND_URL}/pets/{pet_uuid}/observacoes/",
        json=payload,
        timeout=10,
    )

    return JsonResponse(safe_json(r) or {}, status=r.status_code)
