# -*- coding: utf-8 -*-
#
# secureurl.py - Converte streams http:// para https:// (quando o servidor
# aceita TLS) para que a operadora nao consiga ver o conteudo do video.
#
# - Nunca converte enderecos locais (127.x, 10.x, 192.168.x, 172.16-31.x,
#   localhost) usados pelos proxies internos do addon.
# - Remove a porta :80 ao converter (https usa 443; ":80" quebrava o TLS).
# - Mantem cache dos hosts que NAO aceitam https, para nao perder tempo
#   tentando de novo (cai direto no http original).
# - patch_requests() enrola requests.get/head/post: tenta https primeiro e,
#   se o servidor recusar TLS OU devolver erro 4xx/5xx (enquanto o http
#   funciona), refaz em http. Nenhum canal deixa de abrir.
# - play_url() e para tocar no Kodi: testa o https antes (1 vez por host,
#   em cache); se nao estiver bom, devolve o http original.
#
# Pode ser desligado nas configuracoes do addon: "Forcar HTTPS nos streams".

import re
import threading
import time

try:
    from urllib.parse import urlparse
except ImportError:  # py2 antigo
    from urlparse import urlparse

try:
    string_types = (str, unicode)
except NameError:
    string_types = (str,)

_lock = threading.Lock()
_enabled = None
_checked_at = 0.0
_broken_hosts = set()      # hosts onde https falhou -> usar http direto
_verified_hosts = {}       # host -> True (https ok) / False (só http)
_patched = False
_orig = {}                 # requests originais (sem patch)
_CHECK_INTERVAL = 30.0

_LOCAL_HOSTS = ('127.0.0.1', 'localhost', '0.0.0.0', '::1')


def _is_local(host):
    """True para enderecos locais/rede interna (proxies do proprio addon)."""
    h = (host or '').lower().strip('[]')
    if not h or h in _LOCAL_HOSTS:
        return True
    if h.startswith('127.') or h.startswith('10.') or h.startswith('192.168.') or h.startswith('169.254.'):
        return True
    if h.startswith('172.'):
        try:
            second = int(h.split('.')[1])
            if 16 <= second <= 31:
                return True
        except (ValueError, IndexError):
            return False
    return False


def is_enabled():
    """Le a configuracao 'force_https' do addon (com cache de 30s)."""
    global _enabled, _checked_at
    now = time.time()
    if _enabled is None or (now - _checked_at) > _CHECK_INTERVAL:
        try:
            import xbmcaddon
            enabled = xbmcaddon.Addon('plugin.video.gloriosotv').getSetting('force_https')
            _enabled = (enabled != 'false')  # default/'' = ligado
        except Exception:
            _enabled = True
        _checked_at = now
    return _enabled


def _host_of(url):
    try:
        return (urlparse(url).hostname or '').lower()
    except Exception:
        return ''


def to_https(url):
    """Converte http:// -> https:// (remove porta :80, preserva headers '|')."""
    if not isinstance(url, string_types) or not url.startswith('http://'):
        return url
    if not is_enabled():
        return url

    base, sep, rest = url.partition('|')

    host = _host_of(base)
    if not host or _is_local(host) or host in _broken_hosts:
        return url

    base = base[7:]  # remove 'http://'
    # https nao usa a porta 80; manter ':80' quebra o handshake TLS
    auth = base.split('/', 1)[0]
    if auth.lower().endswith(':80'):
        base = auth[:-3] + base[len(auth):]
    return 'https://' + base + (sep + rest if sep else '')


def _mark_broken(url):
    """Marca o host como sem TLS para nao tentar https de novo."""
    try:
        host = _host_of(url)
        if host:
            _broken_hosts.add(host)
    except Exception:
        pass


def play_url(url):
    """URL pronta para TOCAR no Kodi.

    Testa o https antes (1 probe por host, em cache): se o servidor
    aceitar TLS sem dar erro/4xx, toca em https; senao toca no http
    original, exatamente como antes. Nada de canal quebrar.
    """
    if not isinstance(url, string_types):
        return url

    base, sep, rest = url.partition('|')

    scheme = base.split('://', 1)[0].lower() if '://' in base else ''
    if scheme not in ('http', 'https'):
        return url  # plugin://, magnet:, etc.

    if not is_enabled() or scheme == 'https':
        return url

    host = _host_of(base)
    if not host or _is_local(host):
        return url

    verified = _verified_hosts.get(host)
    if verified is None:
        verified = _probe_https(base)
        _verified_hosts[host] = verified
        if not verified:
            _broken_hosts.add(host)

    if verified:
        return to_https(url)
    return url


def _probe_https(url):
    """GET leve no https; True se o servidor respondeu bem (<400)."""
    try:
        import requests
        get = _orig.get('get') or requests.get
        r = get(to_https(url), stream=True, timeout=(3.05, 5), allow_redirects=True)
        ok = getattr(r, 'status_code', 0) < 400
        try:
            r.close()
        except Exception:
            pass
        return ok
    except Exception:
        return False


def patch_requests():
    """Enrola requests.get/head/post/put com conversao https + fallback http.

    Idempotente: pode ser chamado varias vezes sem problema.
    Fallback acontece quando o https da erro de conexao OU quando devolve
    status 4xx/5xx e o http original responde melhor.
    """
    global _patched
    if _patched:
        return
    with _lock:
        if _patched:
            return
        try:
            import requests
        except ImportError:
            return

        fallback_errors = (requests.exceptions.ConnectionError,)

        def _wrap(orig, name):
            _orig[name] = orig

            def wrapped(url, *args, **kwargs):
                if not isinstance(url, string_types):
                    return orig(url, *args, **kwargs)
                new_url = to_https(url)
                if new_url == url:
                    return orig(url, *args, **kwargs)
                try:
                    resp = orig(new_url, *args, **kwargs)
                except fallback_errors:
                    # TLS recusado / conexao caiu: volta pro http
                    _mark_broken(url)
                    return orig(url, *args, **kwargs)
                status = getattr(resp, 'status_code', 200)
                if status >= 400:
                    # https conectou mas o servidor negou (403/429/...):
                    # tenta o http original e fica com o melhor resultado
                    try:
                        resp2 = orig(url, *args, **kwargs)
                        status2 = getattr(resp2, 'status_code', 0)
                        if status2 < status:
                            _mark_broken(url)
                            try:
                                resp.close()
                            except Exception:
                                pass
                            return resp2
                    except Exception:
                        pass
                return resp
            return wrapped

        requests.get = _wrap(requests.get, 'get')
        requests.head = _wrap(requests.head, 'head')
        requests.post = _wrap(requests.post, 'post')
        requests.put = _wrap(requests.put, 'put')
        _patched = True
