# -*- coding: utf-8 -*-
import requests
import urllib3
import warnings
import binascii
import os
import re
import time
import threading
import socket
import json
import random # Necessário para gerar o IP aleatório
import six
from requests.exceptions import ConnectionError, RequestException
from six.moves.urllib.parse import unquote_plus, urljoin, urlparse, parse_qs, quote, quote_plus

# O proxy usa verify=False para compatibilidade com origens instaveis.
# Suprime apenas o warning associado para nao poluir o kodi.log.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)
try:
    requests.packages.urllib3.disable_warnings()  # compatibilidade com algumas builds do requests
except Exception:
    pass
try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning as requests_insecure_warning
    requests.packages.urllib3.disable_warnings(requests_insecure_warning)
    warnings.simplefilter('ignore', requests_insecure_warning)
except Exception:
    pass

try:
    import xbmc
except ImportError:
    xbmc = None

PORT = 8094
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
SHUTDOWN_EVENT = threading.Event()

# Variáveis globais para suporte à classe XtreamCodes
HEADERS_BASE = {}
NSPLAYER = False

def gerar_ip_brasileiro():
    # Ranges definidos para simular IPs brasileiros/privados conforme solicitado
    ranges = [
        (167772160, 184549375),   # 10.0.0.0 – 10.255.255.255
        (1879048192, 1884162559), # 112.0.0.0 – 112.63.255.255
        (2896692480, 2896702975), # 172.16.0.0 – 172.31.255.255
        (3232235520, 3232301055)  # 192.168.0.0 – 192.168.255.255
    ]

    faixa = random.choice(ranges)
    ip_numerico = random.randint(faixa[0], faixa[1])

    ip = ".".join([str((ip_numerico >> (i * 8)) & 0xFF) for i in range(4)[::-1]])
    return ip

class XtreamCodes:
    def update_headers(self):
        global HEADERS_BASE
        global NSPLAYER
        header = HEADERS_BASE.copy()
        # Define User-Agent padrão e configurações de conexão
        header.update({
            'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18', 
            'Accept-Encoding': 'gzip, deflate', 
            'Accept': '*/*', 
            'Connection': 'keep-alive'
        })
        
        # Se NSPLAYER estiver ativo, gera um User-Agent aleatório em hexadecimal
        if NSPLAYER == True:
            user_agent = binascii.b2a_hex(os.urandom(20))[:32]
            if six.PY3:
                user_agent = user_agent.decode('ascii', 'ignore')
            header['User-Agent'] = user_agent
            
        # Camuflagem de IP
        ip_fake = gerar_ip_brasileiro()
        header.update({
            'X-Forwarded-For': ip_fake, 
            'X-Real-IP': ip_fake, 
            'Client-IP': ip_fake
        })
        return header

class ProxyHandler:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.xtream = XtreamCodes() # Instancia a classe de camuflagem

    def rewrite_m3u8(self, content, base_url, host):
        def replace(match):
            url = match.group(0).strip()
            if url.startswith('#') or not url: return url
            
            if '\\/' in url:
                url = url.replace('\\/', '/')
            
            full_url = urljoin(base_url + '/', url)
            # O host agora é dinâmico para suportar o IP da rede
            return "http://{}/proxy?url={}".format(host, quote(full_url, safe=''))
            
        return re.sub(r'^(?![#\s]).+', replace, content, flags=re.MULTILINE)

    def handle(self, client_sock, addr):
        try:
            client_sock.settimeout(15)
            data = client_sock.recv(8192).decode('utf-8', errors='ignore')
            if not data: return

            lines = data.splitlines()
            if not lines: return
            
            request_line = lines[0].split(' ')
            if len(request_line) < 2: return
            method = request_line[0]
            path = request_line[1]
            
            # Pega o Host da requisição atual (pode ser 127.0.0.1 ou o IP da rede)
            current_host = ""
            for line in lines:
                if line.lower().startswith("host:"):
                    current_host = line.split(":", 1)[1].strip()
                    break
            if not current_host: current_host = "127.0.0.1:{}".format(PORT)

            if path.startswith('http'):
                target_url = path
            else:
                parsed = urlparse(path)
                params = parse_qs(parsed.query)
                target_url = unquote_plus(params.get('url', [''])[0])

            if not target_url:
                client_sock.sendall(b"HTTP/1.1 200 OK\r\n\r\nProxy Ativo")
                return

            if '\\u' in target_url:
                try: target_url = target_url.encode('utf-8').decode('unicode-escape')
                except: pass

            req_headers = self.xtream.update_headers()
            
            for line in lines[1:]:
                if ": " in line:
                    k, v = line.split(": ", 1)
                    if k.lower() not in ['host', 'connection', 'proxy-connection', 'user-agent']:
                        req_headers[k] = v
            
            try:
                r = self.session.request(method, target_url, headers=req_headers, stream=True, timeout=15, verify=False)
                
                if r.status_code in [200, 206]:
                    c_type = r.headers.get("content-type", "").lower()
                    
                    # Verificação unificada para m3u8 e m3u
                    if "mpegurl" in c_type or ".m3u8" in target_url.lower() or ".m3u" in target_url.lower():
                        rewritten = self.rewrite_m3u8(r.text, target_url.rsplit('/', 1)[0], current_host)
                        header = "HTTP/1.1 200 OK\r\nContent-Type: application/x-mpegURL\r\nAccess-Control-Allow-Origin: *\r\n\r\n"
                        client_sock.sendall(header.encode('utf-8') + rewritten.encode('utf-8'))
                    
                    else:
                        header = "HTTP/1.1 {} OK\r\n".format(r.status_code)
                        header += "Content-Type: {}\r\n".format(r.headers.get('Content-Type', 'application/octet-stream'))
                        header += "Access-Control-Allow-Origin: *\r\n\r\n"
                        client_sock.sendall(header.encode('utf-8'))
                        for chunk in r.iter_content(chunk_size=262144):
                            if chunk: client_sock.sendall(chunk)
                else:
                    reason = r.reason or "Upstream Error"
                    header = "HTTP/1.1 {} {}\r\n".format(r.status_code, reason)
                    header += "Content-Type: {}\r\n".format(r.headers.get('Content-Type', 'text/plain; charset=utf-8'))
                    header += "Access-Control-Allow-Origin: *\r\n\r\n"
                    client_sock.sendall(header.encode('utf-8'))
                    if r.content:
                        client_sock.sendall(r.content)
                return
            except Exception: pass
        except Exception: pass
        finally:
            try: client_sock.close()
            except: pass

def start_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # MUDANÇA IGUAL AO F4MTESTER: Escuta em todas as interfaces (0.0.0.0)
        server.bind(('0.0.0.0', PORT))
        server.listen(100)
        handler = ProxyHandler()
        
        if xbmc: xbmc.log("[Proxy] Servidor iniciado globalmente na porta {}".format(PORT), xbmc.LOGINFO)

        while not SHUTDOWN_EVENT.is_set():
            try:
                server.settimeout(2.0)
                try:
                    c, a = server.accept()
                except socket.timeout:
                    continue
                
                t = threading.Thread(target=handler.handle, args=(c, a))
                t.daemon = True
                t.start()
            except: break
    except Exception as e:
        if xbmc: xbmc.log("[Proxy] Erro ao subir porta: {}".format(e), xbmc.LOGERROR)
    finally:
        server.close()

class proxyOverride:
    def __init__(self, port=PORT):
        global PORT
        PORT = port
        if self._is_port_in_use():
            return

        self.thread = threading.Thread(target=start_proxy)
        self.thread.daemon = True
        self.thread.start()

    def _is_port_in_use(self):
        # Verifica localmente se a porta está ocupada
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            return s.connect_ex(('127.0.0.1', PORT)) == 0
        finally:
            s.close()
            
def get_proxy_url(url_capturada):
    if not isinstance(url_capturada, str):
        url_capturada = str(url_capturada)
    # Retorna localhost por segurança, mas o servidor agora aceita o IP da rede
    return "http://127.0.0.1:{}/proxy?url={}".format(PORT, quote_plus(url_capturada))

if __name__ == "__main__":
    start_proxy()
