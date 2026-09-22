# -*- coding: utf-8 -*-
#
# Camada de compatibilidade de DNS.
#
# O novo customdns.py e um servidor proxy SOCKS5 com DoH e nao possui mais
# a classe DNSOverride. Esta camada reaproveita o resolve_via_doh do
# customdns.py (sem altera-lo) e fornece a classe DNSOverride que os
# players e o default.py esperam, com fallback via requests caso o
# httpx nao esteja disponivel no Kodi.
#
# Uso: from extra_lib.dnscompat import DNSOverride

import socket
import threading

try:
    import ipaddress
    _HAS_IPADDRESS = True
except ImportError:
    _HAS_IPADDRESS = False

# Dominios que nunca devem passar pelo DoH (evita recursao infinita,
# pois a propria consulta DoH precisa resolver o servidor de DNS)
_DOH_DOMAINS = (
    'cloudflare-dns.com',
    'dns.google',
    '1.1.1.1',
    '8.8.8.8',
)

_dns_cache = {}
_cache_lock = threading.Lock()
_original_getaddrinfo = socket.getaddrinfo
_local = threading.local()


def _resolve_via_requests(domain):
    """Fallback de DoH usando requests (modulo sempre presente no Kodi)."""
    try:
        import requests
        r = requests.get(
            'https://cloudflare-dns.com/dns-query',
            params={'name': domain, 'type': 'A'},
            headers={'Accept': 'application/dns-json'},
            timeout=10,
        )
        data = r.json()
        if data.get('Status') == 0:
            for record in data.get('Answer', []):
                if record.get('type') == 1:
                    return record['data']
    except Exception:
        pass
    return None


def resolve_doh(domain):
    """Resolve um dominio via DoH (usa o customdns, com cache e fallback)."""
    if not domain:
        return None
    domain = str(domain).lower().strip('.')

    if is_valid_ipv4(domain):
        return domain

    with _cache_lock:
        if domain in _dns_cache:
            return _dns_cache[domain]

    ip = None
    if domain not in _DOH_DOMAINS:
        # 1) Tenta usar o resolve_via_doh do customdns.py (sem altera-lo)
        try:
            from extra_lib.customdns import resolve_via_doh
        except Exception:
            try:
                from customdns import resolve_via_doh
            except Exception:
                resolve_via_doh = None
        if resolve_via_doh:
            try:
                ip = resolve_via_doh(domain)
            except Exception:
                ip = None

        # 2) Fallback: DoH direto via requests
        if not ip:
            ip = _resolve_via_requests(domain)

    if ip:
        with _cache_lock:
            _dns_cache[domain] = ip
    return ip


def is_valid_ipv4(host):
    """Retorna True se o host ja e um endereco IPv4 valido."""
    host = str(host or '').strip()
    if not _HAS_IPADDRESS:
        parts = host.split('.')
        if len(parts) != 4:
            return False
        for p in parts:
            if not p.isdigit() or not 0 <= int(p) <= 255:
                return False
        return True
    try:
        ipaddress.IPv4Address(host)
        return True
    except Exception:
        return False


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """getaddrinfo que resolve via DoH antes de cair no DNS do sistema."""
    host_str = str(host or '')
    if (
        getattr(_local, 'in_doh', False)
        or not host_str
        or is_valid_ipv4(host_str)
        or host_str.lower() in _DOH_DOMAINS
        or (family not in (0, socket.AF_INET))
        or host_str.startswith(('127.', '10.', '192.168.', '169.254.'))
    ):
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    _local.in_doh = True
    try:
        ip = resolve_doh(host_str)
    except Exception:
        ip = None
    finally:
        _local.in_doh = False

    if not ip:
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    results = []
    try:
        if type in (0, socket.SOCK_STREAM):
            results.append((socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (ip, port)))
        if type in (0, socket.SOCK_DGRAM):
            results.append((socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, '', (ip, port)))
    except Exception:
        results = []
    if results:
        return results
    return _original_getaddrinfo(host, port, family, type, proto, flags)


class DNSOverride(object):
    """Compativel com a antiga classe DNSOverride do customdns.py.

    Ao instanciar, ativa a resolucao DNS-over-HTTPS para todas as
    conexoes do processo (requests, urllib, sockets, etc.).
    """

    def __init__(self):
        try:
            socket.getaddrinfo = _patched_getaddrinfo
        except Exception:
            pass

    def resolve(self, domain):
        return resolve_doh(domain)

    def is_valid_ipv4(self, host):
        return is_valid_ipv4(host)

    @staticmethod
    def restore():
        try:
            socket.getaddrinfo = _original_getaddrinfo
        except Exception:
            pass
