import base64
import hashlib
import secrets
from urllib.parse import urlencode
from urllib.parse import urlparse, urlunparse
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils.text import slugify
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi.models import ArcanaSSOIdentity


STATE_CACHE_PREFIX = "arcana:sso:state:"
TICKET_CACHE_PREFIX = "arcana:sso:ticket:"


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _base64url(digest)


def _normalize_base_url() -> str:
    return str(getattr(settings, "ARCANA_SSO_BASE_URL", "") or "").strip().rstrip("/")


def _arcana_site_root() -> str:
    """
    Ritorna la root del sito Arcana partendo da ARCANA_SSO_BASE_URL
    (es. https://www.arcanadomine.it/wp-json/ad-sso/v2 -> https://www.arcanadomine.it).
    """
    base = _normalize_base_url()
    if not base:
        return ""
    parsed = urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def _client_registered_origin() -> str:
    """
    Origin della redirect_uri registrata su Arcana per questo client.
    Serve per costruire return_to compatibile con la whitelist AD.
    """
    redirect_uri = str(getattr(settings, "ARCANA_SSO_REDIRECT_URI", "") or "").strip()
    if not redirect_uri:
        return ""
    parsed = urlparse(redirect_uri)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def _frontend_login_url(request) -> str:
    configured = str(getattr(settings, "ARCANA_SSO_FRONTEND_LOGIN_PATH", "/login") or "/login").strip()
    if configured.startswith("http://") or configured.startswith("https://"):
        return configured
    if not configured.startswith("/"):
        configured = f"/{configured}"
    return request.build_absolute_uri(configured)


def _build_unique_username(raw: str) -> str:
    base = slugify(raw or "", allow_unicode=False).replace("-", ".").strip(".")
    if not base:
        base = f"arcana.user.{secrets.token_hex(3)}"
    candidate = base[:150]
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix_txt = f".{suffix}"
        candidate = f"{base[:150 - len(suffix_txt)]}{suffix_txt}"
        suffix += 1
    return candidate


def _upsert_local_user(profile: dict) -> User:
    sub = str(profile.get("sub") or profile.get("arcanadomine_id") or "").strip()
    if not sub:
        raise ValueError("Profilo /userinfo senza sub")

    email = (profile.get("email") or "").strip().lower()
    username_hint = (profile.get("username") or email.split("@")[0] or f"arcana-{sub}").strip()
    first_name = (profile.get("nome") or "").strip()
    last_name = (profile.get("cognome") or "").strip()

    with transaction.atomic():
        identity = ArcanaSSOIdentity.objects.select_related("user").filter(provider_sub=sub).first()
        if identity:
            user = identity.user
        else:
            user = None
            if email:
                user = User.objects.filter(email__iexact=email).first()
            if user is None:
                user = User.objects.create(
                    username=_build_unique_username(username_hint),
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                )
                user.set_unusable_password()
                user.save(update_fields=["password"])

            ArcanaSSOIdentity.objects.create(
                user=user,
                provider_sub=sub,
                email_snapshot=email,
                username_snapshot=username_hint,
                ad_profile_json=profile or {},
            )

        dirty_fields = []
        if email and user.email != email:
            user.email = email
            dirty_fields.append("email")
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            dirty_fields.append("first_name")
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            dirty_fields.append("last_name")
        if not user.is_active:
            user.is_active = True
            dirty_fields.append("is_active")
        if dirty_fields:
            user.save(update_fields=dirty_fields)

        ArcanaSSOIdentity.objects.filter(provider_sub=sub).update(
            email_snapshot=email,
            username_snapshot=username_hint,
            ad_profile_json=profile or {},
        )

    return user


class ArcanaSSOLoginStartView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        if not getattr(settings, "ARCANA_SSO_ENABLED", False):
            return Response({"error": "Arcana SSO non abilitato"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        base_url = _normalize_base_url()
        client_id = str(getattr(settings, "ARCANA_SSO_CLIENT_ID", "") or "").strip()
        redirect_uri = str(getattr(settings, "ARCANA_SSO_REDIRECT_URI", "") or "").strip()
        if not (base_url and client_id and redirect_uri):
            return Response({"error": "Configurazione SSO incompleta"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        next_path = (request.GET.get("next") or "/app").strip() or "/app"
        if not next_path.startswith("/"):
            next_path = "/app"

        verifier = _base64url(secrets.token_bytes(64))
        state = _base64url(secrets.token_bytes(24))
        challenge = _pkce_challenge(verifier)

        cache.set(
            f"{STATE_CACHE_PREFIX}{state}",
            {"code_verifier": verifier, "next_path": next_path},
            timeout=600,
        )

        params = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "openid profile",
                # Forza la schermata di login Arcana per evitare riuso silenzioso
                # di una sessione già aperta con un altro account.
                "prompt": "login",
            }
        )
        return HttpResponseRedirect(f"{base_url}/authorize?{params}")


class ArcanaSSOCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        login_url = _frontend_login_url(request)
        code = (request.GET.get("code") or "").strip()
        state = (request.GET.get("state") or "").strip()
        if not code or not state:
            return HttpResponseRedirect(f"{login_url}?arcana_error=missing_code_or_state")

        state_key = f"{STATE_CACHE_PREFIX}{state}"
        state_data = cache.get(state_key)
        cache.delete(state_key)
        if not state_data:
            return HttpResponseRedirect(f"{login_url}?arcana_error=invalid_state")

        base_url = _normalize_base_url()
        client_id = str(getattr(settings, "ARCANA_SSO_CLIENT_ID", "") or "").strip()
        client_secret = str(getattr(settings, "ARCANA_SSO_CLIENT_SECRET", "") or "").strip()
        redirect_uri = str(getattr(settings, "ARCANA_SSO_REDIRECT_URI", "") or "").strip()

        try:
            token_res = requests.post(
                f"{base_url}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code_verifier": state_data["code_verifier"],
                },
                timeout=12,
            )
            token_res.raise_for_status()
            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                return HttpResponseRedirect(f"{login_url}?arcana_error=missing_access_token")

            userinfo_res = requests.get(
                f"{base_url}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=12,
            )
            userinfo_res.raise_for_status()
            profile = userinfo_res.json()
            user = _upsert_local_user(profile)
            local_token, _ = Token.objects.get_or_create(user=user)
        except Exception:
            return HttpResponseRedirect(f"{login_url}?arcana_error=callback_failed")

        ticket = _base64url(secrets.token_bytes(24))
        cache.set(
            f"{TICKET_CACHE_PREFIX}{ticket}",
            {
                "token": local_token.key,
                "is_staff": bool(user.is_staff),
                "is_superuser": bool(user.is_superuser),
                "next": state_data.get("next_path") or "/app",
            },
            timeout=90,
        )
        return HttpResponseRedirect(f"{login_url}?arcana_ticket={ticket}")


class ArcanaSSOExchangeTicketView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        ticket = str(request.data.get("ticket") or "").strip()
        if not ticket:
            return Response({"error": "ticket richiesto"}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f"{TICKET_CACHE_PREFIX}{ticket}"
        payload = cache.get(cache_key)
        cache.delete(cache_key)
        if not payload:
            return Response({"error": "ticket non valido o scaduto"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_200_OK)


class ArcanaSSOPasswordStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        identity = ArcanaSSOIdentity.objects.filter(user=request.user).first()
        is_arcana_user = bool(identity)
        has_local_password = request.user.has_usable_password()
        ad_status = self._compute_ad_status(identity)
        return Response(
            {
                "is_arcana_user": is_arcana_user,
                "has_local_password": has_local_password,
                "show_reminder": bool(is_arcana_user and not has_local_password),
                "ad_status": ad_status,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _compute_ad_status(identity):
        if not identity:
            return {
                "code": "not_logged",
                "label": "Non loggato con AD",
                "color": "red",
                "raw_ruoli": None,
            }

        profile = identity.ad_profile_json or {}
        raw_ruoli = profile.get("Ruoli", profile.get("ruoli"))
        ruoli_norm = str(raw_ruoli or "").strip()
        ruoli_lc = ruoli_norm.lower()
        not_compliant = (not ruoli_norm) or (ruoli_lc == "registrato")
        if not_compliant:
            return {
                "code": "not_compliant",
                "label": "Non in regola con AD",
                "color": "yellow",
                "raw_ruoli": raw_ruoli,
            }

        return {
            "code": "compliant",
            "label": "In regola con AD",
            "color": "green",
            "raw_ruoli": raw_ruoli,
        }


class ArcanaSSOSetLocalPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not ArcanaSSOIdentity.objects.filter(user=request.user).exists():
            return Response({"error": "Utente non associato ad Arcana SSO"}, status=status.HTTP_403_FORBIDDEN)

        new_password = str(request.data.get("new_password") or "").strip()
        confirm_password = str(request.data.get("confirm_password") or "").strip()
        if len(new_password) < 8:
            return Response({"error": "La password deve essere di almeno 8 caratteri."}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return Response({"error": "Le password non coincidono."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        return Response({"message": "Password locale impostata con successo."}, status=status.HTTP_200_OK)


class ArcanaSSOStaffProfilesView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        identities = (
            ArcanaSSOIdentity.objects.select_related("user")
            .order_by("user__username", "-updated_at")
        )
        results = []
        for identity in identities:
            profile = identity.ad_profile_json or {}
            user = identity.user
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            results.append(
                {
                    "id": str(identity.id),
                    "provider_sub": identity.provider_sub,
                    "created_at": identity.created_at,
                    "updated_at": identity.updated_at,
                    "email_snapshot": identity.email_snapshot,
                    "username_snapshot": identity.username_snapshot,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": full_name or user.username,
                        "is_staff": bool(user.is_staff),
                        "is_superuser": bool(user.is_superuser),
                        "has_local_password": bool(user.has_usable_password()),
                    },
                    "arcana_profile_hr": {
                        "sub": profile.get("sub"),
                        "arcanadomine_id": profile.get("arcanadomine_id"),
                        "username": profile.get("username"),
                        "nome": profile.get("nome"),
                        "cognome": profile.get("cognome"),
                        "email": profile.get("email"),
                        "ruoli": profile.get("ruoli"),
                        "tipologia": profile.get("tipologia"),
                        "stato": profile.get("stato"),
                    },
                    "arcana_profile_json": profile,
                }
            )
        return Response(results, status=status.HTTP_200_OK)


def _probe_arcana_reachable() -> bool:
    """Verifica se l'endpoint base Arcana risponde (rete / DNS / TLS)."""
    base = _normalize_base_url()
    if not base:
        return False
    url = f"{base.rstrip('/')}/"
    try:
        r = requests.get(url, timeout=3.5, allow_redirects=True)
        return r.status_code < 500
    except Exception:
        return False


class ArcanaSSOStatusView(APIView):
    """Stato SSO per la UI di login (abilitazione + raggiungibilità rete)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        enabled = bool(getattr(settings, "ARCANA_SSO_ENABLED", False))
        reachable = _probe_arcana_reachable() if enabled else False
        return Response({"enabled": enabled, "reachable": reachable}, status=status.HTTP_200_OK)


class ArcanaSSOFrontChannelLogoutView(APIView):
    """
    Logout federato su Arcana Domine:
    - invalida la sessione WP Arcana nel browser
    - ritorna alla pagina richiesta (default login frontend KOR35)
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        client_id = str(getattr(settings, "ARCANA_SSO_CLIENT_ID", "") or "").strip()
        arcana_root = _arcana_site_root()
        return_to_raw = (request.GET.get("return_to") or "/login").strip() or "/login"
        client_origin = _client_registered_origin()
        if return_to_raw.startswith("/"):
            if client_origin:
                return_to = urljoin(f"{client_origin}/", return_to_raw.lstrip("/"))
            else:
                return_to = request.build_absolute_uri(return_to_raw)
        else:
            return_to = return_to_raw
        if not (client_id and arcana_root):
            return HttpResponseRedirect(return_to)
        params = urlencode(
            {
                "ad_sso_logout": "1",
                "client_id": client_id,
                "return_to": return_to,
            }
        )
        return HttpResponseRedirect(f"{arcana_root}/?{params}")
