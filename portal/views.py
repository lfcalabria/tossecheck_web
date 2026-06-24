import json
import re
import requests
from datetime import datetime

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

# LOGIN
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.session.get("vet_uuid"):
        return redirect("portal:responsavel")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        crmv = (form.cleaned_data["crmv"] or "").strip()
        senha = form.cleaned_data["senha"]
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

    r = requests.post(
        f"{BACKEND_URL}/pets/{pet_uuid}/observacoes/",
        json=payload,
        timeout=10,
    )

    return JsonResponse(safe_json(r) or {}, status=r.status_code)
