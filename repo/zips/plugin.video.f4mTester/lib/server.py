import six
import logging

# set up basic logging; Kodi add-ons can inspect stdout/stderr or use the xbmc log
logging.basicConfig(level=logging.DEBUG)

# try importing xbmc once so we can log exceptions later
try:
    from kodi_six import xbmc
except ImportError:
    xbmc = None

try:
    from urllib.parse import urlparse, parse_qs, quote, unquote, quote_plus, unquote_plus, urlencode #python 3
except ImportError:    
    from urlparse import urlparse, parse_qs #python 2
    from urllib import quote, unquote, quote_plus, unquote_plus, urlencode
if six.PY3:
    from http.server import HTTPServer
    from http.server import BaseHTTPRequestHandler
    from http.server import SimpleHTTPRequestHandler
else:
    from BaseHTTPServer import BaseHTTPRequestHandler
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import HTTPServer
import threading
import requests
import time
import socket
import json
import random
import re
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

# --- SISTEMA DE DNS (DoH) ---
# DNS Primario: 1.1.1.1
# DNS Secundario: 1.0.0.1

DNS_CACHE = {}
ORIGINAL_GETADDRINFO = socket.getaddrinfo
# protect global state when the handler runs on multiple threads
GLOBAL_LOCK = threading.Lock()

def is_ip(host):
    try:
        socket.inet_aton(host)
        return True
    except Exception:
        pass
    if ':' in host:
        return True
    return False

def custom_dns_lookup(hostname):
    if hostname in DNS_CACHE:
        return DNS_CACHE[hostname]
    
    found_ip = None
    dns_servers = ["https://1.1.1.1/dns-query"]
    
    for url in dns_servers:
        try:
            params = {'name': hostname, 'type': 'A'}
            headers = {'accept': 'application/dns-json'}
            r = requests.get(url, params=params, headers=headers, timeout=2, verify=False)
            data = r.json()
            if 'Answer' in data:
                for answer in data['Answer']:
                    if answer['type'] == 1: # A record
                        found_ip = answer['data']
                        break
            if found_ip:
                break
        except Exception:
            pass
            
    if found_ip:
        DNS_CACHE[hostname] = found_ip
        return found_ip
    return None

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    # only intercept lookups for IPv4 or unspecified families; otherwise defer
    if not host or is_ip(host):
        return ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
    # honour explicit IPv6 requests
    if getattr(socket, 'AF_INET6', None) and family == socket.AF_INET6:
        return ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
    # if the caller asked for a particular family other than AF_INET/AF_UNSPEC, leave it alone
    if family not in (0, socket.AF_INET, getattr(socket, 'AF_UNSPEC', 0)):
        return ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)

    resolved_ip = custom_dns_lookup(host)
    
    if resolved_ip:
        socktype = type if type != 0 else socket.SOCK_STREAM
        protocol = proto if proto != 0 else socket.IPPROTO_TCP
        return [(socket.AF_INET, socktype, protocol, '', (resolved_ip, port))]
    
    return ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo
# ----------------------------

# --- SISTEMA DE IP FAKE ---
def generate_fake_ip():
    """Gera um endereço IP público aleatório e plausível."""
    # Evita faixas obviamente privadas para o primeiro octeto
    first_octet = random.choice([i for i in range(1, 255) if i not in [10, 127, 172, 192]])
    return "{}.{}.{}.{}".format(first_octet, random.randint(0, 255), random.randint(0, 255), random.randint(1, 254))

def get_random_ua():
    """Gera um User-Agent aleatorio para parecer trafego de navegador comum e dificultar fingerprinting."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)
# --------------------------

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


HOST_NAME = '127.0.0.1'
PORT_NUMBER = 55334

GLOBAL_HEADERS = {}
GLOBAL_URL = ''
M3U8_URL = ''
TS_URL = ''
URL_TOKEN = ''
URL_NORMAL = ''
HTTPS_PORT = False
STOP_SERVER = False
AES_KEY = None
AES_IV = None
AES_METHOD = None
MEDIA_SEQUENCE = 0
URL_REFERER = ''
MAX_CPU = 98

API_INSTANCE = None

class API:
    def __init__(self, dns, user, pwd, ext):
        self.base_api = f"{dns}/player_api.php?username={user}&password={pwd}"
        self.play_url = f"{dns}/live/{user}/{pwd}/"
        self.ext = ext

        # Proactively resolve the server's hostname to warm up the DNS cache.
        # This can help speed up subsequent requests by avoiding DNS lookup delays.
        try:
            hostname = urlparse(dns).hostname
            if hostname and not is_ip(hostname):
                # This will use our custom DoH resolver and cache the result in DNS_CACHE.
                custom_dns_lookup(hostname)
        except Exception as e:
            # Log a warning if the proactive lookup fails, but don't crash.
            logging.warning("API: Failed to proactively resolve DNS for %s: %s", dns, e)



class handler(SimpleHTTPRequestHandler):
    def cpu(self):
        try:
            from kodi_six import xbmc
            cpu_percent = xbmc.getInfoLabel("System.CpuUsage")
            cpu_percent = int(str(cpu_percent).replace('%', ''))
        except Exception:
            cpu_percent = 0
        return int(cpu_percent)
    
    def playing(self):
        try:
            from kodi_six import xbmc
            if not xbmc.Player().isPlaying():
                return False
            return True
        except Exception:
            return True

    def _parse_xtream_url(self, url):
        """Parses an Xtream Codes URL to extract components."""
        # Matches http(s)://host:port/live/user/pass/anything
        match = re.match(r'(https?://[^/]+)/live/([^/]+)/([^/]+)/(.+)', url)
        if match:
            dns, user, pwd, stream_part = match.groups()
            # Determine extension from the stream part
            ext = '.ts' if '.ts' in stream_part else '.m3u8'
            return {'dns': dns, 'user': user, 'pwd': pwd, 'ext': ext}
        return None

   
    def basename(self,p):
        """Returns the final component of a pathname"""
        i = p.rfind('/') + 1
        return p[i:] 
    
    def check_stream(self,url,headers):
        try:
            with requests.head(url,headers=headers,timeout=3, verify=False) as r:
                return r.status_code == 200
        except Exception:
            return False

    @staticmethod
    def get_origin(url,headers):
        origin = ''
        if int(url.count(':')) == 2:
            try:
                with requests.get(url,headers=headers,verify=False,timeout=1) as r:
                    r_parse = urlparse(r.url)
                    if 'https' in url or ':443' in url:
                        origin = "https://" + r_parse.netloc
                    else:
                        origin = "http://" + r_parse.netloc
            except Exception:
                pass
        return origin
    
    def get_headers(self, url):
        """Return a headers dict for the given url and update the global cache.

        This replaces the previous behaviour of mutating GLOBAL_HEADERS directly.
        """
        global GLOBAL_HEADERS
        # try to extract the real url parameter if this was passed as a query string
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            if 'url' in qs:
                url = qs['url'][0]
        except Exception as e:
            logging.debug("get_headers: failed parsing url %s: %s", url, e)

        ip_fake = generate_fake_ip()
        ua_fake = get_random_ua()
        data = {
            'User-Agent': ua_fake,
            'Connection': 'keep-alive',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'X-Forwarded-For': ip_fake,
            'X-Real-IP': ip_fake,
            'Client-IP': ip_fake
        }

        if '|' in url or '&' in url or 'h123' in url:
            def _extract(param_name):
                try:
                    val = url.split(param_name + '=')[1].split('&')[0]
                    return unquote_plus(val)
                except Exception:
                    return None

            referer = _extract('Referer')
            origin = _extract('Origin')
            cookie = _extract('Cookie')
            user_agent = _extract('User-Agent')

            if referer:
                data['Referer'] = referer
            if cookie:
                data['Cookie'] = cookie
            if origin:
                data['Origin'] = origin
            if user_agent:
                data['User-Agent'] = user_agent

            if referer or origin or cookie:  # Original logic doesn't include user_agent here
                GLOBAL_HEADERS = data
        if not GLOBAL_HEADERS:
            with GLOBAL_LOCK:
                GLOBAL_HEADERS = data

        return data
    
    def append_headers(self,headers):
        return '|%s' % '&'.join(['%s=%s' % (key, headers[key]) for key in headers])    
    
    def convert_to_m3u8(self,url):
        if '|' in url:
            url = url.split('|')[0]
        elif '&h123' in url:
            url = url.split('&h123')[0]
        # if '&' in url:
        #     url = url.split('&')[0]
        if not '.m3u8' in url and not '/hl' in url and int(url.count(":")) == 2 and int(url.count("/")) > 4:
            parsed_url = urlparse(url)
            try:
                host_part1 = '%s://%s'%(parsed_url.scheme,parsed_url.netloc)
                host_part2 = url.split(host_part1)[1]
                url = host_part1 + '/live' + host_part2
                file = self.basename(url)
                if '.ts' in file:
                    file_new = file.replace('.ts', '.m3u8')
                    url = url.replace(file, file_new)
                else:
                    file_new = file + '.m3u8'
                    url = url.replace(file, file_new)
            except Exception:
                pass
        return url
    
    def convert_to_ts(self,url):
        if '|' in url:
            url = url.split('|')[0]
        elif '&h123' in url:
            url = url.split('&h123')[0]        
        if '.m3u8' in url and '/live/' in url and int(url.count("/")) > 5:
            url = url.replace('/live', '').replace('.m3u8', '')
        return url
    
    def detect_xtream_codes(self,url):
        if not '.m3u8' in url and not '/hl' in url and int(url.count(":")) == 2 and int(url.count("/")) > 4 or '.m3u8' in url and '/live/' in url and int(url.count("/")) > 5:
            return True
        else:
            return False

    
    def ts(self,url,headers,head=False):
        global GLOBAL_URL
        global GLOBAL_HEADERS
        global STOP_SERVER
        global API_INSTANCE
        global AES_KEY
        global AES_IV
        global AES_METHOD
        global MEDIA_SEQUENCE
        if not headers:
            headers = GLOBAL_HEADERS
        
        if not url.startswith('http'):
            with GLOBAL_LOCK:
                if API_INSTANCE:
                    # Use the more reliable API base URL to construct the full path
                    if url.startswith('/'):
                        url = url[1:]
                    url = API_INSTANCE.play_url + url
                elif GLOBAL_URL:
                    # Fallback to the old, more fragile logic
                    url = GLOBAL_URL + url
        # url = url.replace('esportes4/', '')
        if head:
            try:
                with requests.head(url, headers=headers,verify=False):
                    pass
            except Exception:
                pass
            return

        for i in range(30):
            i = i + 1
            if STOP_SERVER:
                break
            # if self.cpu() >= MAX_CPU:
            #     self.send_response(200)
            #     self.end_headers()
            #     def shutdown(server):
            #         server.shutdown()
            #     t = threading.Thread(target=shutdown, args=(self.server, ))
            #     t.start()
            #     break
            # if i > 6:
            #     if not self.playing():
            #         self.send_response(200)
            #         self.end_headers()
            #         def shutdown(server):
            #             server.shutdown()
            #         t = threading.Thread(target=shutdown, args=(self.server, ))
            #         t.start()
            #         break
            if not STOP_SERVER:  
                try:
                    with requests.get(url, headers=headers, stream=True, verify=False) as r:
                        if r.status_code == 200:                            
                            content_to_send = r.content
                            if _dec and AES_KEY:
                                try:
                                    current_iv = AES_IV
                                    if current_iv is None:
                                        seq_num_match = re.search(r'(\d+)\.ts', url)
                                        if seq_num_match:
                                            segment_sequence = int(seq_num_match.group(1))
                                            current_iv = num_to_iv(segment_sequence)
                                        else:
                                            logging.debug("Could not determine segment sequence number for IV from URL.")
                                            current_iv = None
                                    
                                    if current_iv:
                                        logging.debug("Decrypting segment with key and IV")
                                        decryptor = get_aes_decryptor(AES_KEY, current_iv, AES_METHOD)
                                        decrypted_content = decryptor.decrypt(content_to_send)

                                        pad_len = decrypted_content[-1]
                                        if six.PY2 and isinstance(pad_len, str): pad_len = ord(pad_len)
                                        if pad_len > 0 and pad_len <= 16:
                                            if decrypted_content[-pad_len:] == bytes([pad_len]) * pad_len:
                                                content_to_send = decrypted_content[:-pad_len]
                                            else:
                                                content_to_send = decrypted_content
                                        else:
                                            content_to_send = decrypted_content
                                    else:
                                        logging.debug("No IV for decryption, sending encrypted segment.")
                                except Exception as e:
                                    logging.debug("AES decryption failed: %s" % e)

                            self.send_response(200)
                            self.send_header('Content-type','video/mp2t')
                            self.end_headers()
                            try:
                                self.wfile.write(content_to_send)
                            except Exception:
                                pass # Client disconnected

                    break
                except Exception:
                    time.sleep(0.5)
            if STOP_SERVER:
                break                           
            # if head_ts(url,headers):                                    
            #     try:
            #         r = requests.get(url, headers=headers, stream=True, verify=False)
            #         if r.status_code == 200:
            #             self.send_response(200)
            #             self.send_header('Content-type','video/mp2t')
            #             self.end_headers()
            #             for chunk in r.iter_content(300000):                           
            #                 try:
            #                     self.wfile.write(chunk)
            #                 except:
            #                     pass
            #                 if not self.playing():
            #                     fechar_server()
            #                     break
            #         r.close()
            #         break
            #     except:
            #         pass
            if i == 15:
                self.send_response(404)
                self.end_headers()
                # def shutdown(server):
                #     server.shutdown()
                # t = threading.Thread(target=shutdown, args=(self.server, ))
                # t.start()                
                break
    
    def m3u8(self,url,headers,head=False):
        #print('acessando a url: ',url)
        global GLOBAL_URL
        global MAX_CPU
        global HTTPS_PORT
        global URL_TOKEN
        global URL_NORMAL
        global URL_REFERER
        global AES_KEY
        global AES_IV
        global AES_METHOD
        global MEDIA_SEQUENCE
        global STOP_SERVER
        # if not URL_REFERER:
        #     URL_REFERER = url
        # if URL_REFERER and 'token' in url:
        #     headers.update({'Referer': URL_REFERER})
        if not 'token' in url:
            URL_NORMAL = url
        if URL_TOKEN:
            url = URL_TOKEN
        elif URL_NORMAL:
            url = URL_NORMAL
        if head:
            try:
                with requests.head(url,headers=headers,verify=False):
                    pass
            except Exception:
                pass
            return
        
        for i in range(20):
            i = i + 1
            if STOP_SERVER:                    
                break

            if i > 5:
                if self.cpu() >= MAX_CPU:
                    self.send_response(200)
                    self.end_headers()
                    STOP_SERVER = True
                    def shutdown(server):
                        server.shutdown()
                        try:
                            server.server_close()
                        except Exception:
                            pass                        
                    t = threading.Thread(target=shutdown, args=(self.server, ))
                    t.start()
                    break
            # if i > 3:
            #     if not self.playing():
            #         self.send_response(200)
            #         self.end_headers()
            #         def shutdown(server):
            #             server.shutdown()
            #         t = threading.Thread(target=shutdown, args=(self.server, ))
            #         t.start()
            #         break
            if not STOP_SERVER:
                try:
                    with requests.get(url, headers=headers,timeout=4, verify=False) as r:
                        last_url = r.url
                        # if 'token' in url:
                        #     URL_TOKEN = ''                  
                        # elif not URL_TOKEN and 'token' in last_url:
                        #     URL_TOKEN = last_url
                        r_parse = urlparse(last_url)
                        if HTTPS_PORT:
                            base_url = "https://" + r_parse.netloc
                        else:
                            base_url = "http://" + r_parse.netloc
                        if r.status_code == 200:
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                            self.end_headers()
                            text_ = r.text
                            if _dec and '#EXT-X-KEY' in text_:
                                key_match = re.search(r'#EXT-X-KEY:METHOD=(AES-128),URI="([^"]+)"(?:,IV=([^ \n]+))?', text_)
                                if key_match:
                                    AES_METHOD = key_match.group(1)
                                    key_uri = key_match.group(2)
                                    iv_hex = key_match.group(3)

                                    if iv_hex:
                                        AES_IV = binascii.unhexlify(iv_hex.replace('0x', ''))
                                    else:
                                        AES_IV = None

                                    if not key_uri.startswith('http'):
                                        base_uri = url.rsplit('/', 1)[0]
                                        key_url = base_uri + '/' + key_uri
                                    else:
                                        key_url = key_uri

                                    try:
                                        if 'ply-key' in key_url:
                                            ply_key = key_url.split('ply-key=')[1]
                                            key_url = decode_custom_uri(ply_key, key_uri)

                                        key_res = requests.get(key_url, headers=headers, timeout=4, verify=False)
                                        if key_res.status_code == 200:
                                            key_data = key_res.content
                                            try:
                                                AES_KEY = process_hex_key(key_data.decode())
                                            except (ValueError, TypeError):
                                                AES_KEY = key_data[:16]
                                            logging.debug('AES Key fetched successfully.')
                                        else:
                                            logging.debug('Failed to fetch AES key: status %s' % key_res.status_code)
                                            AES_KEY = None
                                    except Exception as e:
                                        logging.debug('Error fetching AES key: %s' % e)
                                        AES_KEY = None

                                seq_match = re.search(r'#EXT-X-MEDIA-SEQUENCE:(\d+)', text_)
                                if seq_match:
                                    MEDIA_SEQUENCE = int(seq_match.group(1))

                            if '.html' in text_ and 'http' in text_:
                                text_ = text_.replace('http', 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/?url=http')
                            elif 'chunklist_' in text_ and not 'http' in text_:
                                file = self.basename(url)
                                base_url = url.replace(file, '')
                                if base_url.endswith('/'):
                                    base_url = base_url[:-1]
                                text_ = text_.replace('chunklist_', 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/?url='+base_url+'/chunklist_')
                            elif 'media_' in text_ and '.ts' in text_ and not 'http' in text_:
                                file = self.basename(url)
                                base_url = url.replace(file, '')
                                if base_url.endswith('/'):
                                    base_url = base_url[:-1]
                                text_ = text_.replace('media_', 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/?url='+base_url+'/media_')
                            elif not '/hl' in text_ and not 'http' in text_:
                                file = self.basename(last_url)
                                base_url = last_url.replace(file, '')
                                GLOBAL_URL = base_url
                            elif '/hl' in text_ and not 'http' in text_:
                                text_ = text_.replace('/hl', 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/?url='+base_url+'/hl')
                            else:
                                text_ = text_.replace('http', 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/?url=http')
                            self.wfile.write(text_.encode("utf-8"))
                    break
                except Exception:
                    pass
            if STOP_SERVER:
                break
            time.sleep(3)           
            if i == 8: # 24 segundos
                self.send_response(404)
                self.end_headers()
                STOP_SERVER = True
                def shutdown(server):
                    server.shutdown()
                    try:
                        server.server_close()
                    except Exception:
                        pass
                t = threading.Thread(target=shutdown, args=(self.server, ))
                t.start()      
                break

    def _process_request(self, head=False):
        global GLOBAL_HEADERS, GLOBAL_URL, M3U8_URL, TS_URL, HTTPS_PORT, URL_REFERER, STOP_SERVER, API_INSTANCE, AES_KEY
        
        if STOP_SERVER:
            return

        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        url = qs.get('url', [''])[0]

        try:
            url = unquote_plus(url)
        except Exception:
            pass
        try:
            url = unquote(url)
        except Exception:
            pass

        if self.path == '/check':
            self.send_response(200)
            self.end_headers()
            return
        elif self.path == '/stop':
            self.send_response(200)
            self.end_headers()
            STOP_SERVER = True
            with GLOBAL_LOCK:
                AES_KEY = None
                API_INSTANCE = None
            def shutdown(server):
                server.shutdown()
                try:
                    server.server_close()
                except Exception:
                    pass                    
            t = threading.Thread(target=shutdown, args=(self.server, ))
            t.start()
            return

        if url:
            # always refresh headers based on the requested url; get_headers returns the dict
            headers = self.get_headers(url)
            with GLOBAL_LOCK:
                GLOBAL_HEADERS = headers
            m3u8_url = self.convert_to_m3u8(url)
            url = m3u8_url

            # New integration logic
            xtream_info = self._parse_xtream_url(url)
            if xtream_info:
                with GLOBAL_LOCK:
                    API_INSTANCE = API(xtream_info['dns'], xtream_info['user'], xtream_info['pwd'], xtream_info['ext'])

            if ':443' in m3u8_url or 'https://' in m3u8_url:
                HTTPS_PORT = True

        if url.startswith('http') and '/hl' in url and '.m3u8' in url:
            self.m3u8(url, GLOBAL_HEADERS, head=head)
        elif not url.startswith('http') and '.m3u8' in self.path:
            path_url = self.path[1:] if self.path.startswith('/') else self.path
            full_url = GLOBAL_URL + path_url
            self.m3u8(full_url, GLOBAL_HEADERS, head=head)
        elif 'http' not in url and '/hl' not in url and '.ts' in self.path:
            print('nao http, nao /hl e .ts')
            self.ts(self.path, GLOBAL_HEADERS, head=head)
        elif url.endswith(".ts") or ('/hl' in url and not url.endswith(".ts") and not url.endswith(".m3u8")):
            self.ts(url, GLOBAL_HEADERS, head=head)
        elif url.endswith(".html"):
            self.ts(url, GLOBAL_HEADERS, head=head)
        elif '.m3u8' in url:
            self.m3u8(url, GLOBAL_HEADERS, head=head)

    def do_HEAD(self):
        self._process_request(head=True)

    def do_GET(self):
        self._process_request(head=False)


def serve_forever(httpd):
    try:
        httpd.serve_forever()
    finally:
        try:
            httpd.server_close()
        except Exception:
            pass


class mediaserver:
    def __init__(self):
        try:
            self.httpd = HTTPServer(('', PORT_NUMBER), handler)
            self.server_instance = True
        except Exception:
            self.server_instance = False
        if self.server_instance:
            try:
                self.server = threading.Thread(target=serve_forever, args=(self.httpd, ))
                self.server.daemon = True
                self.server_thread = True
            except Exception:
                self.server_thread = False
        else:
            self.server_thread = False

    
    def in_use(self):
        url = 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/check'
        use = False
        try:
            with requests.head(url,timeout=1) as r:
                if r.status_code == 200:
                    use = True
        except Exception:
            pass
        return use 

    def start(self):
        if not self.in_use():
            if self.server_thread:
                self.server.start()
                time.sleep(4)

    def stop(self):
        if self.server_instance:
            self.httpd.shutdown()
            try:
                self.httpd.server_close()
            except Exception:
                pass

def prepare_url(url):
    try:
        url = unquote_plus(url)
    except Exception:
        pass
    try:
        url = unquote(url)
    except Exception:
        pass
    url = url.replace('|', '&h123=true&')
    url = quote_plus(url)
    url = 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/?url=' + url
    return url

def req_shutdown():
    url = 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/stop'
    try:
        with requests.get(url,timeout=2):
            pass
    except Exception:
        pass

def check_server():
    url = 'http://'+HOST_NAME+':'+str(PORT_NUMBER)+'/check'
    status = False
    try:
        with requests.get(url,timeout=3) as r:
            if r.status_code == 200:
                status = True
    except Exception:
        pass
    return status

def thread_stop():
    t = threading.Thread(target=req_shutdown)
    t.start()


# try:
#     mediaserver().start()
# except KeyboardInterrupt:
#     mediaserver().stop()
