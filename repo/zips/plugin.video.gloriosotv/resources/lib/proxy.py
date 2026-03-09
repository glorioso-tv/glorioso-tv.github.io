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

    def _tunnel_data(self, sock_from, sock_to, stop_event):
        try:
            while not stop_event.is_set():
                try:
                    data = sock_from.recv(8192)
                    if not data:
                        break
                    sock_to.sendall(data)
                except (socket.timeout, socket.error, OSError):
                    break
        finally:
            stop_event.set()

    def handle_connect(self, client_sock, target_host):
        remote_sock = None
        try:
            try:
                host, port_str = target_host.split(':')
                port = int(port_str)
            except ValueError:
                client_sock.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                return

            try:
                remote_sock = socket.create_connection((host, port), timeout=10)
            except Exception as e:
                if xbmc: xbmc.log("[Proxy] CONNECT failed to {}: {}".format(target_host, e), xbmc.LOGERROR)
                client_sock.sendall("HTTP/1.1 502 Bad Gateway\r\n\r\n".encode('utf-8'))
                return
            
            client_sock.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")

            stop_event = threading.Event()
            
            t1 = threading.Thread(target=self._tunnel_data, args=(client_sock, remote_sock, stop_event))
            t2 = threading.Thread(target=self._tunnel_data, args=(remote_sock, client_sock, stop_event))
            t1.daemon = True
            t2.daemon = True
            t1.start()
            t2.start()
            
            stop_event.wait()

        finally:
            if remote_sock:
                try: remote_sock.close()
                except: pass

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
            version = request_line[2] if len(request_line) > 2 else "HTTP/1.0"

            if method.upper() == 'CONNECT':
                self.handle_connect(client_sock, path)
                return

            current_host, host_header = "", ""
            for line in lines:
                if line.lower().startswith("host:"):
                    host_header = current_host = line.split(":", 1)[1].strip()
                    break
            if not current_host: current_host = "127.0.0.1:{}".format(PORT)

            if path.startswith('/proxy?url='):
                parsed = urlparse(path)
                params = parse_qs(parsed.query)
                target_url = unquote_plus(params.get('url', [''])[0])
            elif path.startswith('http://') or path.startswith('https://'):
                target_url = path
            else:
                if not host_header:
                    client_sock.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    return
                target_url = "http://{}{}".format(host_header, path)

            if not target_url:
                client_sock.sendall(b"HTTP/1.1 200 OK\r\n\r\nProxy Ativo")
                return

            req_headers = self.xtream.update_headers()
            hop_by_hop_headers = ['host', 'connection', 'proxy-connection', 'keep-alive', 'te', 'trailers', 'transfer-encoding', 'upgrade']
            for line in lines[1:]:
                if ": " in line:
                    k, v = line.split(": ", 1)
                    if k.lower() not in hop_by_hop_headers:
                        req_headers[k] = v
            
            try:
                r = self.session.request(method, target_url, headers=req_headers, stream=True, timeout=15, verify=False)
                c_type = r.headers.get("content-type", "").lower()
                is_m3u = "mpegurl" in c_type or ".m3u8" in target_url.lower() or ".m3u" in target_url.lower()

                if r.status_code in [200, 206] and is_m3u:
                    rewritten = self.rewrite_m3u8(r.text, target_url.rsplit('/', 1)[0], current_host)
                    response_body = rewritten.encode('utf-8')
                    response_headers = "{} 200 OK\r\nContent-Type: application/x-mpegURL\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\n\r\n".format(version, len(response_body))
                    client_sock.sendall(response_headers.encode('utf-8'))
                    client_sock.sendall(response_body)
                else:
                    response_line = "{} {} {}\r\n".format(version, r.status_code, r.reason or '')
                    client_sock.sendall(response_line.encode('utf-8'))
                    for k, v in r.headers.items():
                        if k.lower() not in hop_by_hop_headers and k.lower() != 'content-encoding':
                            client_sock.sendall("{}: {}\r\n".format(k, v).encode('utf-8'))
                    client_sock.sendall(b"Access-Control-Allow-Origin: *\r\n\r\n")
                    if method.upper() != 'HEAD':
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk: client_sock.sendall(chunk)
            except RequestException as e:
                if xbmc: xbmc.log("[Proxy] Request failed for {}: {}".format(target_url, e), xbmc.LOGERROR)
                client_sock.sendall("{} 502 Bad Gateway\r\n\r\n".format(version).encode('utf-8'))
            except Exception as e:
                if xbmc: xbmc.log("[Proxy] Generic error handling {}: {}".format(target_url, e), xbmc.LOGERROR)
                client_sock.sendall("{} 500 Internal Server Error\r\n\r\n".format(version).encode('utf-8'))
        except Exception:
            pass
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
