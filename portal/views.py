import json
import re
import requests
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from .forms import LoginForm, BuscarResponsavelForm, CadastroResponsavelForm

# CONFIGURAÇÃO
BACKEND_URL = getattr(settings, "BACKEND_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
BACKEND_BASE_URL = BACKEND_URL.replace("/api/v1", "")

DEMO_CRMV = "DEMO"
DEMO_SENHA = "demo123"
DEMO_VET_TOKEN = "demo-vet-token"
DEMO_VET_NOME = "Dra. Ana Demo"
DEMO_RESPONSAVEL = {
    "uuid": "22222222-2222-2222-2222-222222222222",
    "nome": "Mariana Costa",
    "cpf": "52998224725",
    "telefone": "(81) 99999-0000",
}
DEMO_PET_UUID = "11111111-1111-1111-1111-111111111111"
DEMO_PETS = [
    {
        "uuid": DEMO_PET_UUID,
        "nome": "Luna",
        "tipo": "Cachorro",
        "sexo": "Femea",
        "raca": "SRD",
        "idade": 5,
        "peso": 12.4,
        "altura": 48,
    },
    {
        "uuid": "33333333-3333-3333-3333-333333333333",
        "nome": "Mingau",
        "tipo": "Gato",
        "sexo": "Macho",
        "raca": "Persa",
        "idade": 3,
        "peso": 4.8,
        "altura": 25,
    },
]
DEMO_PET_DETAILS = {
    DEMO_PET_UUID: {
        **DEMO_PETS[0],
        "videos": [],
        "prontuario": [
            {
                "veterinario": DEMO_VET_NOME,
                "data": "22/06/2026 17:20",
                "texto": "Tutor relata tosse seca principalmente durante a noite. Animal ativo, sem febre no atendimento.",
            },
            {
                "veterinario": DEMO_VET_NOME,
                "data": "20/06/2026 09:15",
                "texto": "Orientado observar frequencia da tosse e retornar com novo video se houver piora.",
            },
        ],
    },
    "33333333-3333-3333-3333-333333333333": {
        **DEMO_PETS[1],
        "videos": [],
        "prontuario": [
            {
                "veterinario": DEMO_VET_NOME,
                "data": "21/06/2026 10:40",
                "texto": "Espirros ocasionais e tosse leve. Sem alteracao evidente na ausculta.",
            },
        ],
    },
}

# UTILITÁRIOS
def normalizar_cpf(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")

def safe_json(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return None

def payload_request(request):
    content_type = request.META.get("CONTENT_TYPE", "").lower()
    if "application/json" in content_type:
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            return {}
    return request.POST.dict()

def demo_enabled():
    return getattr(settings, "DEMO_MODE", settings.DEBUG)

def demo_session_active(request):
    return demo_enabled() and request.session.get("demo_mode")

def set_responsavel_session(request, responsavel):
    request.session["responsavel_uuid"] = responsavel.get("uuid")
    request.session["responsavel_nome"] = responsavel.get("nome")
    request.session["responsavel_cpf"] = responsavel.get("cpf")

def reset_demo_data(request, incluir_responsavel=False):
    request.session["demo_responsavel"] = deepcopy(DEMO_RESPONSAVEL)
    request.session["demo_pets"] = deepcopy(DEMO_PETS)
    request.session["demo_pet_details"] = deepcopy(DEMO_PET_DETAILS)
    if incluir_responsavel:
        set_responsavel_session(request, DEMO_RESPONSAVEL)

def iniciar_demo(request, incluir_responsavel=False):
    request.session["vet_uuid"] = DEMO_VET_TOKEN
    request.session["vet_nome"] = DEMO_VET_NOME
    request.session["demo_mode"] = True
    reset_demo_data(request, incluir_responsavel=incluir_responsavel)

def demo_pets(request):
    pets = request.session.get("demo_pets")
    if pets is None:
        pets = deepcopy(DEMO_PETS)
        request.session["demo_pets"] = pets
    return pets

def demo_pet_details(request):
    details = request.session.get("demo_pet_details")
    if details is None:
        details = deepcopy(DEMO_PET_DETAILS)
        request.session["demo_pet_details"] = details
    return details

def demo_pet_detail(request, pet_uuid):
    pet_uuid = str(pet_uuid)
    details = demo_pet_details(request)
    if pet_uuid in details:
        return details[pet_uuid]

    for pet in demo_pets(request):
        if str(pet.get("uuid")) == pet_uuid:
            details[pet_uuid] = {**pet, "videos": [], "prontuario": []}
            request.session["demo_pet_details"] = details
            request.session.modified = True
            return details[pet_uuid]
    return None

def cadastrar_demo_pet(request, payload):
    pet_uuid = str(uuid4())
    pet = {
        "uuid": pet_uuid,
        "nome": payload.get("nome") or "Pet demo",
        "tipo": payload.get("tipo") or "Cachorro",
        "sexo": payload.get("sexo") or "-",
        "raca": payload.get("raca") or "-",
        "idade": payload.get("idade"),
        "peso": payload.get("peso"),
        "altura": payload.get("altura"),
    }

    pets = demo_pets(request)
    pets.append(pet)

    details = demo_pet_details(request)
    details[pet_uuid] = {**pet, "videos": [], "prontuario": []}

    request.session["demo_pets"] = pets
    request.session["demo_pet_details"] = details
    request.session.modified = True
    return pet

def credenciais_demo(crmv, senha):
    return demo_enabled() and crmv.upper() == DEMO_CRMV and senha == DEMO_SENHA

def demo_view(request):
    iniciar_demo(request, incluir_responsavel=True)
    messages.info(request, "Modo demonstracao ativado com dados fake.")
    return redirect("portal:pets")

# LOGIN
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.session.get("vet_uuid"):
        return redirect("portal:responsavel")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        crmv = (form.cleaned_data["crmv"] or "").strip()
        senha = form.cleaned_data["senha"]
        if credenciais_demo(crmv, senha):
            iniciar_demo(request)
            messages.info(request, "Modo demonstracao ativado.")
            return redirect("portal:responsavel")
        try:
            r = requests.post(f"{BACKEND_URL}/login/", json={"crmv": crmv, "senha": senha}, timeout=10)
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

# RESPONSÁVEL
@require_http_methods(["GET", "POST"])
def responsavel_view(request):
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
                if demo_session_active(request):
                    responsavel = request.session.get("demo_responsavel") or deepcopy(DEMO_RESPONSAVEL)
                    if cpf == responsavel.get("cpf") or cpf == DEMO_RESPONSAVEL["cpf"]:
                        if cpf == DEMO_RESPONSAVEL["cpf"]:
                            responsavel = deepcopy(DEMO_RESPONSAVEL)
                            request.session["demo_responsavel"] = responsavel
                            request.session["demo_pets"] = deepcopy(DEMO_PETS)
                            request.session["demo_pet_details"] = deepcopy(DEMO_PET_DETAILS)
                        set_responsavel_session(request, responsavel)
                        contexto["responsavel_encontrado"] = True
                        contexto["responsavel_nome"] = responsavel.get("nome")
                        contexto["responsavel_cpf"] = responsavel.get("cpf")
                    else:
                        contexto["mostrar_cadastro"] = True
                        contexto["form_cadastro"] = CadastroResponsavelForm(initial={"cpf": cpf})
                        messages.info(request, "Responsavel nao encontrado. Cadastre abaixo.")
                    return render(request, "portal/responsavel.html", contexto)
                try:
                    r = requests.get(f"{BACKEND_URL}/responsavel/", params={"q": cpf}, timeout=10)
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
                    contexto["form_cadastro"] = CadastroResponsavelForm(initial={"cpf": cpf})
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
                if demo_session_active(request):
                    responsavel = {
                        "uuid": str(uuid4()),
                        **payload,
                    }
                    request.session["demo_responsavel"] = responsavel
                    request.session["demo_pets"] = []
                    request.session["demo_pet_details"] = {}
                    set_responsavel_session(request, responsavel)
                    contexto["responsavel_encontrado"] = True
                    contexto["responsavel_nome"] = responsavel.get("nome")
                    contexto["responsavel_cpf"] = responsavel.get("cpf")
                    contexto["mostrar_cadastro"] = False
                    messages.success(request, "Responsavel cadastrado com sucesso no modo demo.")
                    return render(request, "portal/responsavel.html", contexto)
                try:
                    r = requests.post(f"{BACKEND_URL}/responsavel/", json=payload, timeout=10)
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

# PETS
@require_http_methods(["GET"])
def pets_view(request):
    if not request.session.get("vet_uuid"):
        return redirect("portal:login")
    responsavel_uuid = request.session.get("responsavel_uuid")
    if not responsavel_uuid:
        return redirect("portal:responsavel")
    if demo_session_active(request):
        contexto = {
            "vet_nome": request.session.get("vet_nome"),
            "responsavel_nome": request.session.get("responsavel_nome"),
            "responsavel_uuid": responsavel_uuid,
            "pets": demo_pets(request),
        }
        return render(request, "portal/pets.html", contexto)
    try:
        r = requests.get(f"{BACKEND_URL}/responsavel/{responsavel_uuid}/pets/", timeout=10)
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

# CRIAÇÃO DE PET
@require_http_methods(["POST"])
@csrf_protect
def criar_pet(request):
    wants_json = "application/json" in request.META.get("CONTENT_TYPE", "").lower()

    if not request.session.get("vet_uuid"):
        if wants_json:
            return JsonResponse({"erro": "Não autenticado."}, status=401)
        return redirect("portal:login")
    responsavel_uuid = request.session.get("responsavel_uuid")
    if not responsavel_uuid:
        if wants_json:
            return JsonResponse({"erro": "Responsável não definido."}, status=400)
        messages.error(request, "Responsável não definido.")
        return redirect("portal:pets")

    incoming = payload_request(request)
    if demo_session_active(request):
        if not incoming.get("nome") or not incoming.get("tipo"):
            erro = {"erro": "Nome e tipo sao obrigatorios."}
            if wants_json:
                return JsonResponse(erro, status=400)
            messages.error(request, erro["erro"])
            return redirect("portal:pets")
        pet = cadastrar_demo_pet(request, incoming)
        if wants_json:
            return JsonResponse({"ok": True, "pet": pet}, status=201)
        messages.success(request, "Pet cadastrado com sucesso no modo demo.")
        return redirect("portal:pets")
    payload = {
        "usuario_uuid": responsavel_uuid,
        "nome": incoming.get("nome"),
        "tipo": incoming.get("tipo"),
        "sexo": incoming.get("sexo"),
        "raca": incoming.get("raca"),
        "idade": incoming.get("idade"),
        "peso": incoming.get("peso"),
        "altura": incoming.get("altura"),
    }
    try:
        r = requests.post(f"{BACKEND_URL}/pets/", json=payload, timeout=10)
    except requests.RequestException:
        if wants_json:
            return JsonResponse({"erro": "Erro ao conectar com o backend."}, status=502)
        messages.error(request, "Erro ao conectar com o backend.")
        return redirect("portal:pets")
    data = safe_json(r) or {}
    if r.status_code in (200, 201):
        if wants_json:
            return JsonResponse({"ok": True, "pet": data}, status=r.status_code)
        messages.success(request, "Pet cadastrado com sucesso.")
    else:
        if wants_json:
            return JsonResponse(
                data or {"erro": "Erro ao cadastrar pet."},
                status=r.status_code,
            )
        messages.error(request, data.get("erro", "Erro ao cadastrar pet."))
    return redirect("portal:pets")

# PRONTUÁRIO DO PET
@require_http_methods(["GET"])
def pet_detalhe_view(request, pet_uuid):
    if not request.session.get("vet_uuid"):
        return redirect("portal:login")
    if demo_session_active(request):
        pet = demo_pet_detail(request, pet_uuid)
        if not pet:
            messages.error(request, "Pet nao encontrado no modo demo.")
            return redirect("portal:pets")
        contexto = {
            "pet": pet,
            "proxy_pet_observacao_url": f"/portal/proxy/pets/{pet_uuid}/observacoes/",
            "BACKEND_BASE_URL": BACKEND_BASE_URL,
        }
        return render(request, "portal/pet_detalhe.html", contexto)
    try:
        r = requests.get(f"{BACKEND_URL}/pets/{pet_uuid}/", timeout=10)
    except requests.RequestException:
        messages.error(request, "Erro ao conectar com o backend.")
        return redirect("portal:pets")
    if r.status_code != 200:
        data = safe_json(r)
        messages.error(request, (data or {}).get("erro", "Erro ao carregar prontuário."))
        return redirect("portal:pets")
    pet = safe_json(r) or {}
    videos = pet.get("videos") or []
    def parse_data_upload(v):
        s = v.get("data_upload")
        if not s:
            return datetime.min
        try:
            return datetime.strptime(s, "%d/%m/%Y %H:%M")
        except ValueError:
            return datetime.min
    pet["videos"] = sorted(videos, key=parse_data_upload, reverse=True)
    contexto = {
        "pet": pet,
        "proxy_pet_observacao_url": f"/portal/proxy/pets/{pet_uuid}/observacoes/",
        "BACKEND_BASE_URL": BACKEND_BASE_URL,
    }
    return render(request, "portal/pet_detalhe.html", contexto)

# LOGOUT
def logout_view(request):
    request.session.flush()
    return redirect("portal:login")

# PROXIES
@csrf_exempt
@require_http_methods(["POST"])
def proxy_pets(request):
    if not request.session.get("vet_uuid"):
        return JsonResponse({"erro": "Não autenticado."}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"erro": "JSON inválido."}, status=400)
    if demo_session_active(request):
        if not payload.get("nome") or not payload.get("tipo"):
            return JsonResponse({"erro": "Nome e tipo sao obrigatorios."}, status=400)
        pet = cadastrar_demo_pet(request, payload)
        return JsonResponse(pet, status=201)
    r = requests.post(f"{BACKEND_URL}/pets/", json=payload, timeout=10)
    return JsonResponse(safe_json(r) or {}, status=r.status_code)

@csrf_exempt
@require_http_methods(["POST"])
def proxy_pet_observacao(request, pet_uuid):
    if not request.session.get("vet_uuid"):
        return JsonResponse({"erro": "Não autenticado."}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    if demo_session_active(request):
        pet = demo_pet_detail(request, pet_uuid)
        if not pet:
            return JsonResponse({"erro": "Pet nao encontrado."}, status=404)
        texto = (payload.get("texto") or "").strip()
        if not texto:
            return JsonResponse({"erro": "Texto da observacao e obrigatorio."}, status=400)

        observacao = {
            "id": len(pet.get("prontuario") or []) + 1,
            "veterinario": request.session.get("vet_nome") or DEMO_VET_NOME,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "texto": texto,
        }
        pet.setdefault("prontuario", []).insert(0, observacao)
        details = demo_pet_details(request)
        details[str(pet_uuid)] = pet
        request.session["demo_pet_details"] = details
        request.session.modified = True
        return JsonResponse(observacao, status=201)

    r = requests.post(
        f"{BACKEND_URL}/pets/{pet_uuid}/observacoes/",
        json=payload,
        timeout=10,
    )

    return JsonResponse(safe_json(r) or {}, status=r.status_code)
