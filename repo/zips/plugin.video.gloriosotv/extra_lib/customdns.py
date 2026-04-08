# -*- coding: utf-8 -*-
import socket
import random
import struct
import sys
import logging
import requests
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

# Configura logging para depuração
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

ORIGINAL_GETADDRINFO = socket.getaddrinfo
DNS_CACHE = {}
SOCKET_PATCHED = False


def log_customdns(level, message):
    logging.log(level, "[customdns] {0}".format(message))

class DNSOverride(object):
    def __init__(self, dns_server="1.1.1.1"):
        global SOCKET_PATCHED
        self.dns_server = dns_server # Servidor DNS padrão
        self.doh_servers = [
            "https://dohfire.alwaysdata.net/dns-query",
            "https://1.1.1.1/dns-query",
        ]
        self.doh_hosts = set()
        for doh_url in self.doh_servers:
            try:
                host = urlparse(doh_url).hostname
                if host:
                    self.doh_hosts.add(host)
            except Exception:
                pass # Ignora exceções
        self.PY2 = sys.version_info[0] == 2
        self.original_getaddrinfo = ORIGINAL_GETADDRINFO
        self.cache = DNS_CACHE
        self.debug_mode = False  # Modo de depuração ativado

        # Ativa override apenas uma vez para evitar encadeamento e perda de cache
        if not SOCKET_PATCHED:
            socket.getaddrinfo = self._resolver
            SOCKET_PATCHED = True

    def bchr(self, val):
        return chr(val) if self.PY2 else bytes([val]) # Retorna caractere ou byte

    def bjoin(self, parts):
        return b"".join(parts)

    def to_bytes(self, val):
        if self.PY2:
            return val if isinstance(val, str) else val.encode("utf-8")
        return val if isinstance(val, bytes) else val.encode("utf-8")
    
    def is_valid_ipv4(self, ip):
        try:
            socket.inet_aton(ip) # Tenta converter para IPv4
            return True
        except socket.error:
            return False    

    def resolve_doh(self, domain):
        if domain in self.doh_hosts:
            log_customdns(logging.DEBUG, "Bypass DoH para host do resolvedor: {0}".format(domain))
            return None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/dns-json"
        }
        params = {
            "name": domain,
            "type": "A"
        }

        for url in self.doh_servers:
            try: # Tenta resolver via DoH
                log_customdns(logging.DEBUG, "Consultando {0} via DoH {1}".format(domain, url))
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code != 200:
                    log_customdns(
                        logging.WARNING,
                        "DoH retornou HTTP {0} para {1} em {2}".format(response.status_code, domain, url)
                    )
                    if response.status_code == 429:
                        break
                    continue

                data = response.json()
                if data.get("Status") == 0 and "Answer" in data:
                    for answer in data["Answer"]:
                        ip = answer.get("data") # IP resolvido
                        if self.is_valid_ipv4(ip):
                            self.cache[domain] = ip
                            log_customdns(logging.DEBUG, "Resolved {0} to {1} via DoH".format(domain, ip))
                            return ip

                log_customdns(
                    logging.WARNING,
                    "DoH sem resposta valida para {0} em {1} (Status={2})".format(
                        domain, url, data.get("Status", "desconhecido")
                    )
                )
            except Exception as e:
                log_customdns(logging.WARNING, "Falha DoH para {0} em {1}: {2}".format(domain, url, e))

        return None

    def resolve(self, domain):
        if domain in self.cache:
            log_customdns(logging.DEBUG, "Cache hit for {0}: {1}".format(domain, self.cache[domain]))
            return self.cache[domain]

        ip = self.resolve_doh(domain)
        if ip:
            return ip

        def build_query(domain):
            tid = random.randint(0, 65535)
            header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0) # Empacota o cabeçalho
            qname_parts = []
            for part in domain.split('.'):
                if not part:
                    continue
                qname_parts.append(self.bchr(len(part)))
                qname_parts.append(self.to_bytes(part))
            qname_parts.append(self.bchr(0))
            qname = self.bjoin(qname_parts)
            question = qname + struct.pack(">HH", 1, 1)  # A, IN
            return header + question, tid

        def parse_response(data, tid):
            if len(data) < 12:
                log_customdns(logging.ERROR, "Resposta DNS muito curta") # Erro de resposta curta
                return None
            if struct.unpack(">H", data[:2])[0] != tid:
                log_customdns(logging.ERROR, "ID da transacao DNS nao corresponde")
                return None
            answers = struct.unpack(">H", data[6:8])[0]
            i = 12
            while i < len(data) and (ord(data[i]) if self.PY2 else data[i]) != 0:
                i += 1
            i += 5
            for _ in range(answers): # Itera sobre as respostas
                if i + 10 >= len(data):
                    log_customdns(logging.ERROR, "Resposta DNS invalida: truncada")
                    return None
                i += 2  # Pular name
                type_, class_, ttl, rdlen = struct.unpack(">HHIH", data[i:i+10])
                i += 10
                if type_ == 1 and class_ == 1 and rdlen == 4:  # A record, IN class
                    ip = ".".join(str(ord(c)) if self.PY2 else str(c) for c in data[i:i+4]) # Converte para IP
                    self.cache[domain] = ip
                    log_customdns(logging.DEBUG, "Resolved {0} to {1}".format(domain, ip))
                    return ip
                i += rdlen
            log_customdns(logging.WARNING, "Nenhum registro A encontrado para {0}".format(domain))
            return None

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(5)  # Aumentado para 5 segundos
            query, tid = build_query(domain) # Constrói a query
            log_customdns(logging.DEBUG, "Consultando {0} via DNS {1}:53".format(domain, self.dns_server))
            s.sendto(query, (self.dns_server, 53))
            data, _ = s.recvfrom(512)
            s.close()
            return parse_response(data, tid)
        except socket.timeout:
            log_customdns(logging.ERROR, "Timeout ao consultar DNS para {0}".format(domain))
            return None
        except Exception as e:
            log_customdns(logging.ERROR, "Erro ao resolver {0}: {1}".format(domain, e))
            return None

    def _resolver(self, host, port, *args, **kwargs):
        try:
            # Se já for um IP válido, retorna direto
            if self.is_valid_ipv4(host):
                log_customdns(logging.DEBUG, "Bypass DNS: {0} ja e um IP".format(host))
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (host, port))]

            if host in self.doh_hosts:
                log_customdns(logging.DEBUG, "Host DoH {0} usando getaddrinfo original".format(host))
                return self.original_getaddrinfo(host, port, *args, **kwargs)

            ip = self.resolve(host)
            if ip:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
            log_customdns(logging.WARNING, "Falha ao resolver {0}, usando getaddrinfo original".format(host))
            if not self.debug_mode:
                return self.original_getaddrinfo(host, port, *args, **kwargs)
        except Exception as e:
            log_customdns(logging.ERROR, "Erro no resolver para {0}: {1}".format(host, e))
        if not self.debug_mode:
            return self.original_getaddrinfo(host, port, *args, **kwargs)

# Inicialização forçada do Proxy
# Deve ser feita após a definição da classe DNSOverride para garantir que o patch do socket.getaddrinfo já esteja ativo.
try:
    from extra_lib.proxy import proxyOverride
    proxyOverride()
except Exception:
    log_customdns(logging.ERROR, "Falha ao iniciar proxyOverride no customdns.py")
