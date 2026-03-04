# -*- coding: utf-8 -*-
import socket
import struct
import random
import threading
import sys
import ssl
import time
import json
import os

try:
    import xbmc
    import xbmcvfs
    import xbmcaddon
except ImportError:
    xbmc = None

# Configuração de caminhos para o Cache persistente
if xbmc:
    ADDON = xbmcaddon.Addon()
    # No Kodi 20+ usamos xbmcvfs, em versões antigas xbmc.translatePath
    TRANSLATE = xbmcvfs.translatePath if sys.version_info[0] == 3 else xbmc.translatePath
    profile = TRANSLATE(ADDON.getAddonInfo('profile'))
    if not os.path.exists(profile):
        os.makedirs(profile)
    CACHE_FILE = os.path.join(profile, 'dns_cache.json')
else:
    CACHE_FILE = 'dns_cache.json'

if sys.version_info[0] == 2:
    import urllib2 as urlrequest
else:
    import urllib.request as urlrequest

class DNSOverride(object):
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DNSOverride, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.doh_host = "cloudflare-dns.com"
        self.doh_url = "https://1.1.1.1/dns-query"
        self.cache_file = CACHE_FILE
        self.ttl = 3600  # 1 hora
        
        # Carrega o cache do arquivo
        self.cache = self._load_cache()
        
        self.original_getaddrinfo = socket.getaddrinfo
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED

        socket.getaddrinfo = self._getaddrinfo_override
        if xbmc: xbmc.log("[CustomDNS] DNS com Cache Persistente Ativado", xbmc.LOGINFO)

    def _load_cache(self):
        """Carrega o cache do arquivo JSON"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    current_time = time.time()
                    # Filtra apenas o que não expirou
                    return {k: v for k, v in data.items() if v.get('expires', 0) > current_time}
        except:
            pass
        return {}

    def _save_cache(self):
        """Salva o cache atual no arquivo JSON"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except:
            pass

    def _build_dns_query(self, domain):
        tid = random.randint(0, 65535)
        header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
        qname = b"".join([struct.pack("B", len(p)) + p.encode('utf-8') for p in domain.split('.') if p]) + b"\x00"
        return header + qname + struct.pack(">HH", 1, 1), tid

    def resolve_via_cloudflare(self, domain):
        agora = time.time()
        
        # Cache Hit
        if domain in self.cache:
            if self.cache[domain]['expires'] > agora:
                return self.cache[domain]['ip']

        if domain == self.doh_host: return "1.1.1.1"

        query_data, tid = self._build_dns_query(domain)
        try:
            req = urlrequest.Request(self.doh_url, data=query_data)
            req.add_header('Host', self.doh_host)
            req.add_header('Content-Type', 'application/dns-message')
            req.add_header('Accept', 'application/dns-message')
            
            if sys.version_info[0] == 2:
                response = urlrequest.urlopen(req, timeout=1.5)
            else:
                response = urlrequest.urlopen(req, timeout=1.5, context=self.ssl_context)
            data = response.read()
            
            # Extração simples do IP da resposta DNS
            ip = socket.inet_ntoa(data[-4:])
            if ip and "." in ip:
                self.cache[domain] = {
                    'ip': ip,
                    'expires': agora + self.ttl
                }
                self._save_cache() # Salva no arquivo
                return ip
        except:
            pass
        return None

    def _getaddrinfo_override(self, host, port, *args, **kwargs):
        if host is None:
            return self.original_getaddrinfo(host, port, *args, **kwargs)

        host_name = host
        if sys.version_info[0] == 3 and isinstance(host_name, bytes):
            try:
                host_name = host_name.decode('utf-8', 'ignore')
            except:
                return self.original_getaddrinfo(host, port, *args, **kwargs)

        if not isinstance(host_name, str):
            return self.original_getaddrinfo(host, port, *args, **kwargs)

        if host_name in ['localhost', '127.0.0.1'] or host_name.endswith('.local'):
            return self.original_getaddrinfo(host, port, *args, **kwargs)

        ip = self.resolve_via_cloudflare(host_name)
        if ip:
            # Preserva family/type/proto/flags solicitados pelo chamador.
            return self.original_getaddrinfo(ip, port, *args, **kwargs)

        return self.original_getaddrinfo(host, port, *args, **kwargs)

# Inicia o serviço
dns_client = DNSOverride()
