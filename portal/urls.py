from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("demo/", views.demo_start, name="demo_start"),
    path("preview/", views.preview_template, name="preview"),
    path("preview/<slug:template_name>/", views.preview_template, name="preview_template"),

    # =========================
    # AUTENTICAÇÃO
    # =========================
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # =========================
    # RESPONSÁVEL
    # =========================
    path("responsavel/", views.responsavel_view, name="responsavel"),

    # =========================
    # PETS
    # =========================
    path("pets/", views.pets_view, name="pets"),

    # ✅ NOVA ROTA: criação de pet via portal (proxy para backend)
    # NÃO quebra nada existente
    path("pets/criar/", views.criar_pet, name="criar_pet"),

    # Detalhe / prontuário do pet
    path("pets/<uuid:pet_uuid>/", views.pet_detalhe_view, name="pet_detalhe"),

    # =========================
    # PROXIES (mantidos para compatibilidade)
    # =========================
    path("proxy/pets/", views.proxy_pets, name="proxy_pets"),
    path(
        "proxy/pets/<uuid:pet_uuid>/observacoes/",
        views.proxy_pet_observacao,
        name="proxy_pet_observacao",
    ),
]
