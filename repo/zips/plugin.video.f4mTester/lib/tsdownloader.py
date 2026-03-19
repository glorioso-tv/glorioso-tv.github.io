# -*- coding: utf-8 -*-
import socket
import threading
import six
if six.PY3:
    from urllib.parse import urlparse, parse_qs, quote, unquote, unquote_plus, quote_plus
else:
    from urlparse import urlparse, parse_qs
    from urllib import quote, unquote, unquote_plus, quote_plus, quote
try:
    from lib.helper import log as log2
except ImportError:
    try:
        from helper import log as log2
    except ImportError:
        log2 = None
import os
import re
try:
    from doh_client import requests
except ImportError:
    import requests
import logging
import base64
import random
import binascii
import struct

_dec = False
try:
    from Cryptodome.Cipher import AES
    _dec = True
except ImportError:
    try:
        from Crypto.Cipher import AES
        _dec = True
    except ImportError:
        _dec = False

try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION = requests.Session()
try:
    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(['GET', 'HEAD']),
        raise_on_status=False,
    )
except TypeError:
    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=frozenset(['GET', 'HEAD']),
        raise_on_status=False,
    )
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry_strategy)
SESSION.mount('http://', adapter)
SESSION.mount('https://', adapter)

def get_local_ip():
    # retorna o IP local da interface, usado para tentar conectar ao proxy
    try:
        # Cria um socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception as e:
        local_ip = '127.0.0.1'
    finally:
        try:
            s.close()
        except:
            pass
    return local_ip

def log(msg):
    try:
        message = 'F4MTESTER-TS: %s' % msg
        logged = False
        try:
            import xbmc
            xbmc.log(message, xbmc.LOGINFO)
            logged = True
        except:
            pass
        if log2:
            try:
                log2(message)
                logged = True
            except:
                pass
        if not logged:
            logger.info(message)
    except:
        logger.info(msg)

def gerar_ip_brasileiro():
    primeiro_octeto = random.choice([177, 179, 186, 187, 189, 200, 201])
    ip = "%s.%s.%s.%s" % (
        primeiro_octeto,
        random.randint(1, 254),
        random.randint(1, 254),
        random.randint(1, 254),
    )
    return ip

def num_to_iv(n):
    # Converte o número da sequência em um IV de 16 bytes (padronizado para HLS)
    return struct.pack(">8xq", n)

def get_aes_decryptor(key_data, iv, method="AES-128"):
    if method != "AES-128":
        raise Exception("Apenas AES-128 é suportado")

    # Garante que o IV tenha 16 bytes
    if isinstance(iv, int):
        iv = num_to_iv(iv)
    elif isinstance(iv, bytes) and len(iv) < 16:
        iv = b"\x00" * (16 - len(iv)) + iv

    return AES.new(key_data, AES.MODE_CBC, iv)

def process_hex_key(hls_aes_key):
    # Converte chave em hexadecimal para binário (16 bytes)
    return binascii.unhexlify(hls_aes_key)[:16]

def decode_custom_uri(ply_key, key_uri):
    # Lógica de manipulação de string/base64 usada no script
    uri_part1 = base64.urlsafe_b64decode(ply_key)
    uri_part2 = base64.urlsafe_b64encode(key_uri.encode())
    return "https://www.plylive.me" + (uri_part1 + uri_part2).decode()


USE_FAKE_IP = True

# Segurança: limita bind a localhost por padrão.
HOST_NAME = '127.0.0.1'
PORT_NUMBER = 58550

url_proxy = 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/?url='


global HEADERS_BASE
global STOP_SERVER
HEADERS_BASE = {}
STOP_SERVER = False
HEADERS_BASE_LOCK = threading.Lock()

def request_with_tls(method, url, **kwargs):
    allow_insecure_fallback = kwargs.pop('allow_insecure_fallback', True)
    kwargs.setdefault('verify', True)
    try:
        return SESSION.request(method, url, **kwargs)
    except requests.exceptions.SSLError:
        if allow_insecure_fallback and kwargs.get('verify', True):
            kwargs['verify'] = False
            log('TLS verify falhou, fallback insecure para: %s' % url)
            return SESSION.request(method, url, **kwargs)
        raise

def request_get(url, **kwargs):
    return request_with_tls('GET', url, **kwargs)

def request_head(url, **kwargs):
    return request_with_tls('HEAD', url, **kwargs)

def iter_local_control_urls(path):
    hosts = [HOST_NAME, '127.0.0.1', 'localhost', get_local_ip()]
    seen = set()
    for host in hosts:
        if not host or host in seen:
            continue
        seen.add(host)
        yield 'http://%s:%s%s' % (host, PORT_NUMBER, path)

def request_local(path, method='GET', timeout=3):
    for url in iter_local_control_urls(path):
        try:
            if method == 'HEAD':
                return request_head(url, timeout=timeout, allow_insecure_fallback=False)
            return request_get(url, timeout=timeout, allow_insecure_fallback=False)
        except:
            pass
    return None

def get_headers_base():
    with HEADERS_BASE_LOCK:
        return HEADERS_BASE.copy()

def set_headers_base_if_empty(headers):
    global HEADERS_BASE
    with HEADERS_BASE_LOCK:
        if HEADERS_BASE == {}:
            HEADERS_BASE = headers.copy()

def reset_headers_base():
    global HEADERS_BASE
    with HEADERS_BASE_LOCK:
        HEADERS_BASE = {}

def dns_resolver_iptv(url,headers):
    url_parsed = urlparse(url)
    protocol = url_parsed.scheme
    port = str(url_parsed.port) if url_parsed.port else ('443' if protocol == 'https' else '')
    net = url_parsed.hostname
    if not net:
        return {'url': url, 'headers': headers}
    if port:
        host = protocol + '://' + net + ':' + port
    else:
        host = protocol + '://' + net
    ip_pattern = re.compile(r'^(https?://)?(\d{1,3}\.){3}\d{1,3}(:\d+)?(/.*)?$')
    tem_ip = bool(ip_pattern.match(net))
    if tem_ip:
        return {'url': url, 'headers': headers}
    else:     
        params = {
            "name": net,
            "type": "A",  # Tipo de consulta DNS (A, AAAA, etc.)
        }    
        try:
            r = request_get('https://1.1.1.1/dns-query',headers={"Accept": "application/dns-json"}, params=params, timeout=3, allow_insecure_fallback=False).json()
            ip_ = r['Answer'][-1].get('data', '')
        except:
            ip_ = net
        if ip_:
            ip = ip_
            if port:
                new_host = protocol + '://' + ip + ':' + port
            else:
                new_host = protocol + '://' + ip
            url_replace = url.replace(host, new_host)
            headers_ = {'Host': net}
            headers_.update(headers)
            req_info = {'url': url_replace, 'headers': headers_}
        else:
            req_info = {}
        return req_info


class XtreamCodes:
    def set_headers(self, url):
        """Examina a URL para extrair cabeçalhos e atribui a HEADERS_BASE se estiver vazio.
        A proteção com lock previne condições de corrida entre threads.
        """
        global HEADERS_BASE        
        headers_default = {'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18', 'Connection': 'keep-alive'}
        headers = {}
        if 'User-Agent' in url:
            try:
                user_agent = url.split('User-Agent=')[1]
                try:
                    user_agent = user_agent.split('&')[0]
                except:
                    pass
                try:
                    user_agent = unquote_plus(user_agent)
                except:
                    pass
                try:
                    user_agent = unquote(user_agent)
                except:
                    pass
                if 'Mozilla' in user_agent:
                    headers['User-Agent'] = user_agent
            except:
                pass
        if 'Referer' in url:
            try:
                referer = url.split('Referer=')[1]
                try:
                    referer = referer.split('&')[0]
                except:
                    pass
                try:
                    referer = unquote_plus(referer)
                except:
                    pass
                try:
                    referer = unquote(referer)
                except:
                    pass                
                headers['Referer'] = referer
            except:
                pass
        if 'Origin' in url:
            try:
                origin = url.split('Origin=')[1]
                try:
                    origin = origin.split('&')[0]
                except:
                    pass
                try:
                    origin = unquote_plus(origin)
                except:
                    pass
                try:
                    origin = unquote(origin)
                except:
                    pass                
                headers['Origin'] = origin
            except:
                pass
        #HEADERS_ = headers if headers else headers_default
        if headers != {}:
            headers.update({'Connection': 'keep-alive'})
            HEADERS_ = headers
        else:
            HEADERS_ = headers_default
        if USE_FAKE_IP:
            ip_fake = gerar_ip_brasileiro()
            HEADERS_.update({'X-Forwarded-For': ip_fake, 'X-Real-IP': ip_fake, 'Client-IP': ip_fake})
        set_headers_base_if_empty(HEADERS_)

    def send_ts(self, self_server, url):
        global HEADERS_BASE
        if url:
            self_server.send_header('Content-type','video/mp2t')
            self_server.end_headers() 
            try:
                for i in range(10):
                    count = i + 1
                    stop_user = False
                    headers_rot = get_headers_base()
                    if USE_FAKE_IP:
                        ip_fake = gerar_ip_brasileiro()
                        headers_rot.update({'X-Forwarded-For': ip_fake, 'X-Real-IP': ip_fake, 'Client-IP': ip_fake})
                    info = dns_resolver_iptv(url, headers_rot)
                    url = info.get('url', '')
                    header_ = info.get('headers', {})                    
                    r = request_get(url, headers=header_, allow_redirects=True, stream=True)
                    code = r.status_code
                    log('Status Code: %s' % str(code))
                    if code == 200:                    
                        error = False
                        try:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:                      
                                    try:
                                        self_server.conn.sendall(chunk)
                                    except Exception as e:
                                        log('send_ts sendall error: %s' % e)
                                        stop_user = True
                                        break
                        except Exception as e:
                            log('send_ts iter_content error: %s' % e)
                            error = True
                        if stop_user:
                            break
                        if not error:
                            break
                    else:
                        if stop_user:
                            break
                        elif count == 7:
                            break

            except Exception as e:
                log('send_ts exception: %s' % e)

    def parse_url(self,url):
        parsed_url = urlparse(url)
        scheme = parsed_url.scheme
        host = parsed_url.hostname
        port = parsed_url.port
    
        return scheme, host, port    



class ProxyHandler(XtreamCodes):
    def __init__(self, conn, addr, server):
        self.conn = conn
        self.addr = addr
        self.server = server
        self.path = ""
        self.request_method = ""

    def parse_request(self, request):
        parts = request.split(b' ')
        self.request_method = parts[0].decode()

    def parse_request2(self, request):
        parts = request.split(b' ')
        if len(parts) >= 2:
            self.path = parts[1].decode()

    def send_response(self, code, message=None):
        response = "HTTP/1.1 {} {}\r\n".format(code, message if message else "")
        self.conn.sendall(response.encode())

    def send_header(self, keyword, value):
        header = "{}: {}\r\n".format(keyword, value)
        self.conn.sendall(header.encode())

    def end_headers(self):
        self.conn.sendall(b"\r\n")

    def extract_header(self, request_data, header_name):
        header_lines = request_data.split(b'\r\n')
        for line in header_lines:
            if header_name in line:
                return line
        return None        

    def get_range(self, request_data, content_length):
        range_header = self.extract_header(request_data, b'Range:')
        max_end = content_length - 1 if content_length > 0 else 0
        if not range_header:
            return 0, max_end
        try:
            range_value = range_header.decode('utf-8', 'ignore')
            match = re.search(r'bytes=(\d*)-(\d*)', range_value)
            if not match:
                return 0, max_end
            start_str, end_str = match.groups()
            if not start_str and not end_str:
                return 0, max_end
            if not start_str:
                suffix = int(end_str)
                start = max(content_length - suffix, 0)
                end = max_end
            else:
                start = int(start_str)
                end = int(end_str) if end_str else max_end
            start = max(0, min(start, max_end))
            end = max(start, min(end, max_end))
            return start, end
        except:
            return 0, max_end       

    def stream_video(self, video_url, request_data):
        try:
            video_url = video_url.split('|')[0]
        except Exception:
            pass
        try:
            video_url = video_url.split('%7C')[0]
        except Exception:
            pass
        headers = get_headers_base()
        if USE_FAKE_IP:
            ip_fake = gerar_ip_brasileiro()
            headers.update({'X-Forwarded-For': ip_fake, 'X-Real-IP': ip_fake, 'Client-IP': ip_fake})
        try:
            response = request_head(video_url, headers=headers)
            if response.status_code == 200:
                content_length = int(response.headers.get('Content-Length', 0))
                start, end = self.get_range(request_data, content_length)
                #headers['Range'] = f'bytes={start}-{end}'  # Adicionando cabeçalho de intervalo
                headers['Range'] = 'bytes=%s-%s'%(str(start),str(end))  # Adicionando cabeçalho de intervalo
                response = request_get(video_url, headers=headers, stream=True)
                if response.status_code == 206 or response.status_code == 200:
                    self.send_partial_response(206, response.headers, content_length, response.iter_content(chunk_size=1024), start, end)
                else:
                    self.send_response(404)
            else:
                self.send_response(404)
        except Exception as e:
            #print("Error streaming video:", e)
            self.send_response(500)

    def send_partial_response(self, status_code, headers, content_length, content_generator, start, end):
        self.send_response(status_code)
        #self.send_header('Content-type','video/mp4')
        self.send_header("Accept-Ranges", "bytes")
        if start is not None:
            #self.send_header("Content-Range", f"bytes {start}-{end}/{content_length}")
            self.send_header("Content-Range", "bytes %s-%s/%s"%(str(start),str(end),str(content_length)))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()

        for chunk in content_generator:
            if STOP_SERVER:
                break
            try:
                self.conn.sendall(chunk)
            except:
                pass
                        

    def handle_request(self):
        global URL_BASE, LAST_URL, HEADERS_BASE, STOP_SERVER, CACHE_CHUNKS, CACHE_M3U8, DELAY_MODE
        global RESOLUTION, LAST_M3U8, PARAMS, URL_BASE_PARAMS, CHECK_URL_PARAMS, URL_BASE_STALKER, TOKEN_STALKER       
        
        request_data = self.conn.recv(1024)
        self.parse_request(request_data)
        self.parse_request2(request_data)
        
        if self.request_method == 'HEAD':
            self.send_response(200)
            pass
        elif self.path == "/stop":
            self.send_response(200)
            STOP_SERVER = True
            URL_BASE = ''; LAST_URL = ''; HEADERS_BASE = {}; CACHE_CHUNKS = []; CACHE_M3U8 = ''
            DELAY_MODE = True; LAST_M3U8 = ''; RESOLUTION = True; PARAMS = ''
            CHECK_URL_PARAMS = True; URL_BASE_STALKER = ''; TOKEN_STALKER = ''           
            self.server.stop_server()
        elif self.path == "/reset":
            self.send_response(200)
            URL_BASE = ''; LAST_URL = ''; HEADERS_BASE = {}; CACHE_CHUNKS = []; CACHE_M3U8 = ''
            DELAY_MODE = True; RESOLUTION = True; LAST_M3U8 = ''; PARAMS = ''
            URL_BASE_PARAMS = ''; CHECK_URL_PARAMS = True; URL_BASE_STALKER = ''; TOKEN_STALKER = ''
        elif self.path == '/check':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.conn.sendall(b"Hello, world!")
        else:
            url_path = unquote_plus(self.path)
            self.set_headers(url_path)
            url_parts = urlparse(url_path)
            query_params = parse_qs(url_parts.query)
            
            if 'url' in query_params:
                url = url_path.split('url=')[1]
                try:
                    url = base64.b64decode(url).decode('utf-8')
                except:
                    pass
                try:
                    url = url.split('|')[0]
                except:
                    pass
                try:
                    url = url.split('%7C')[0]
                except:
                    pass

                if re.search(r'/\w+/\w+/\d+$', url):
                    parsed_url = urlparse(url)
                    host_part = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)
                    url = host_part + '/live' + parsed_url.path + '.ts'
                
                if hasattr(self, 'convert_to_m3u8'):
                    url = self.convert_to_m3u8(url)
            else:
                url = url_path
                
            if '.m3u8' in url and '?' in url and not 'extension' in url:
                if not PARAMS:
                    try:
                        PARAMS = '?' + url.split('?')[1]
                    except:
                        pass
            
            if '/hl' in url and '.ts' in url:
                self.send_response(200)
                self.send_ts(self,url)            
            elif '/hl' in url and not '.ts' in url:
                self.send_response(200)
                self.send_ts(self,url)            
            elif 'm3u8' in url and not 'extension' in url and '/play/' in url and not '.m3u8' in url:
                self.send_response(200)
                self.send_m3u8_stalker(self,url)               
            elif 'm3u8' in url and 'extension' in url:
                self.send_response(200)
            elif '.ts' in url and URL_BASE_STALKER or 'hls' in url and URL_BASE_STALKER:
                self.send_response(200)
                self.send_ts_stalker(self,url)
            elif '.mp4' in url and not '.m3u8' in url and not '.ts' in url:
                self.stream_video(url, request_data)                    
            elif '.m3u8' in url:
                self.send_response(200)
                self.send_m3u8(self,url)
            elif '.ts' in url:
                self.send_response(200)
                self.send_ts(self,url)
            elif '/live/' in url and not '.ts' in url and not '.m3u8' in url:
                self.send_response(200)
                self.send_ts(self, url + '.ts')

        self.conn.close()

def monitor():
    try:
        try:
            from kodi_six import xbmc
        except:
            import xbmc
        monitor = xbmc.Monitor()
        while not monitor.waitForAbort(3):
            pass
        #log('Ecerrando proxy server')
        request_local('/stop', method='GET', timeout=4)
        #log('Proxy encerrado')
    except:
        pass 

class Server:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((HOST_NAME, PORT_NUMBER))
        self.server_socket.listen(10)
        self.server_socket.settimeout(1.0)
        log('TS server bind em %s:%s' % (HOST_NAME, PORT_NUMBER))

    def serve_forever(self):
        global STOP_SERVER
        while True:
            if STOP_SERVER:
                break
            try:
                conn, addr = self.server_socket.accept()
            except socket.timeout:
                continue
            except:
                break
            handler = ProxyHandler(conn, addr, self)
            t = threading.Thread(target=handler.handle_request)
            t.daemon = True
            t.start()

    def stop_server(self):
        self.server_socket.close()

def loop_server():
    server = Server()
    server.serve_forever()

class XtreamProxy:
    def reset(self):
        request_local('/reset', method='GET', timeout=3)

    def check_service(self):
        try:
            r = request_local('/check', method='HEAD', timeout=3)
            if r and r.status_code == 200:
                return True
            return False
        except:
            return False

    def start(self):
        global STOP_SERVER
        STOP_SERVER = False
        status = self.check_service()
        log('TS start check_service=%s' % str(status))
        if status == False:
            proxy_service = threading.Thread(target=loop_server)
            proxy_service.daemon = True
            proxy_service.start()
            monitor_service = threading.Thread(target=monitor)
            monitor_service.daemon = True
            monitor_service.start()
        else:
            self.reset()

# print('url proxy: ',url_proxy)
# XtreamProxy().start()
