# -*- coding: utf-8 -*-
#
# Servidor Proxy SOCKS5 com Resolução DNS-over-HTTPS (DoH) via Cloudflare
#
# Este script usa o protocolo SOCKS5 e resolve nomes de domínio através do
# serviço DoH da Cloudflare (https://cloudflare-dns.com/dns-query), que é
# altamente confiável e rápido, resolvendo problemas de timeout.
#
# Compatível com Kodi 19 (Python 3.8), 20 e 21.3.
# Dependência: requests (script.module.requests, já declarado no addon.xml).
# Execução: python3 proxy.py
#
# DEBUG HABILITADO PARA RASTREAR QUEDAS DE CONEXÃO.

import socket
import threading
import sys
import os
try:
    import requests # Disponível no Kodi via script.module.requests
except ImportError:
    requests = None
import json
import struct
import select # Para controle de timeout no socket
import ipaddress
from datetime import datetime

# --- Configurações do SOCKS5 ---
HOST = '0.0.0.0'
PORT = 1080  # Porta padrão para SOCKS5
BUFFER_SIZE = 4096
VERSION = 0x05 # Versão SOCKS 5
CUSTOM_DNS = 'https://cloudflare-dns.com/dns-query'

# Timeout de 20.0 segundos para o DoH
DOH_TIMEOUT = 20.0

def log(message):
    """Log com timestamp. Dentro do Kodi vai para o kodi.log com o
    prefixo [customdns]; fora do Kodi cai no print normal."""
    line = f"[customdns] [{datetime.now().strftime('%H:%M:%S')}] {message}"
    try:
        import xbmc
        level = getattr(xbmc, 'LOGINFO', 1) # 1 = LOGINFO (LOGNOTICE não existe mais no Kodi 21.3/Py3.13)
        xbmc.log(line, level)
    except ImportError:
        print(line)

def resolve_via_doh(domain):
    """Resolve o nome de domínio usando o DNS-over-HTTPS da Cloudflare."""
    log(f"[DOH INÍCIO] Tentando resolver: {domain}")
    try:
        headers = {'Accept': 'application/dns-json'}
        params = {'name': domain, 'type': 'A'}
        data = None
        
        if requests is not None:
            response = requests.get(CUSTOM_DNS, headers=headers, params=params, timeout=DOH_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        else:
            # Fallback com urllib (stdlib do Kodi 19 ao 21.3)
            from urllib.parse import urlencode
            try:
                from urllib.request import Request, urlopen
            except ImportError:
                from urllib2 import Request, urlopen
            url = CUSTOM_DNS + '?' + urlencode(params)
            req = Request(url, headers=headers)
            response = urlopen(req, timeout=DOH_TIMEOUT)
            data = json.loads(response.read().decode('utf-8'))
        
        if data.get('Status') == 0 and 'Answer' in data:
            for record in data['Answer']:
                if record['type'] == 1: # Tipo 1 é registro A (IPv4)
                    log(f"[DOH OK] {domain} -> {record['data']}")
                    return record['data'] 
        
        log(f"[DOH FALHA] Resposta sem registro A para {domain}. Status: {data.get('Status')}")
        return None
    
    except Exception as e:
        log(f"[ERRO DOH] Falha ao consultar Cloudflare para {domain}: {e}")
        return None

def handle_socks5_connection(client_socket, client_addr):
    """Lida com o handshake SOCKS5 e roteamento de dados."""
    dest_socket = None
    log(f"[HANDLER INÍCIO] Conexão de: {client_addr}")
    try:
        # 1. Negociação de Método (Apenas Sem Autenticação 0x00)
        client_socket.settimeout(5) # Timeout curto para o handshake
        
        # Leitura da versão e métodos
        data = client_socket.recv(BUFFER_SIZE)
        if not data or data[0] != VERSION:
            raise Exception("Versão SOCKS inválida ou dados incompletos.")
        log(f"[SOCKS1] Versão SOCKS5 e métodos recebidos.")

        methods = data[2:]
        if 0x00 not in methods:
            # Resposta: 0x05 (SOCKS5), 0xFF (Sem métodos aceitáveis)
            client_socket.sendall(b'\x05\xFF')
            raise Exception("Nenhum método de autenticação aceitável.")
        
        # Resposta: 0x05 (SOCKS5), 0x00 (Sem Autenticação aceito)
        client_socket.sendall(b'\x05\x00')
        log(f"[SOCKS1 OK] Sem autenticação aceita.")

        # 2. Requisição de Conexão
        data = client_socket.recv(BUFFER_SIZE)
        if not data or data[0] != VERSION or data[1] != 0x01: # 0x01 = Comando CONNECT
            raise Exception("Requisição SOCKS5 inválida ou comando não é CONNECT.")
        
        log(f"[SOCKS2] Comando CONNECT recebido.")

        addr_type = data[3]
        
        dest_addr = None
        dest_port = None

        if addr_type == 0x01: # IPv4
            dest_addr = socket.inet_ntoa(data[4:8])
            dest_port = struct.unpack('>H', data[8:10])[0]
            log(f"[DESTINO] IPv4: {dest_addr}:{dest_port}")

        elif addr_type == 0x03: # Nome de Domínio
            domain_len = data[4]
            domain = data[5:5+domain_len].decode('utf-8')
            dest_port = struct.unpack('>H', data[5+domain_len:7+domain_len])[0]
            
            # --- PONTO CRÍTICO: RESOLUÇÃO DOH ---
            log(f"[DESTINO] Domínio: {domain}:{dest_port}. Iniciando DoH.")
            dest_addr = resolve_via_doh(domain)
            
            if not dest_addr:
                # Falha na Resolução: Resposta 0x05 0x04 (Host inacessível)
                log(f"[SOCKS FALHA] Falha na resolução DOH para {domain}. Enviando 0x04.")
                client_socket.sendall(b'\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00')
                raise Exception(f"Falha na resolução DOH para {domain}.")

        elif addr_type == 0x04: # IPv6
            # O SOCKS5 não suporta IPv6 no nosso script simplificado.
            # Resposta 0x05 0x08 (Tipo de endereço não suportado)
            log("[SOCKS FALHA] Endereço IPv6 não suportado. Enviando 0x08.")
            client_socket.sendall(b'\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00')
            raise Exception("Endereço IPv6 não suportado.")
        else:
            # Resposta 0x05 0x08 (Tipo de endereço não suportado)
            log("[SOCKS FALHA] Tipo de endereço SOCKS5 desconhecido. Enviando 0x08.")
            client_socket.sendall(b'\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00')
            raise Exception("Tipo de endereço SOCKS5 desconhecido.")

        # 3. Conectar ao Destino
        dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Timeout de conexão de 20 segundos para maior robustez
        dest_socket.settimeout(20) 
        
        log(f"[CONECTANDO] Tentando conexão com {dest_addr}:{dest_port}")
        dest_socket.connect((dest_addr, dest_port))
        log(f"[CONECTADO SUCESSO] Conexão estabelecida com {dest_addr}:{dest_port}.")
        
        # Resposta de Sucesso: 0x05 0x00 (Sucesso)
        bind_addr = dest_socket.getsockname()[0]
        bind_port = dest_socket.getsockname()[1]
        reply = b'\x05\x00\x00\x01' + socket.inet_aton(bind_addr) + bind_port.to_bytes(2, 'big')
        client_socket.sendall(reply)
        log("[HANDSHAKE COMPLETO] Resposta SOCKS5 de sucesso enviada ao cliente. Iniciando túnel.")

        # 4. Inicia o Túnel de Dados
        tunnel_data_transfer(client_socket, dest_socket, client_addr)

    except socket.timeout:
        log(f"[ERRO HANDLER] Timeout de socket durante o handshake ou conexão com destino para {client_addr}.")
        # Tenta enviar falha SOCKS5 (0x06: TTL expirado/Timeout)
        try:
             client_socket.sendall(b'\x05\x06\x00\x01\x00\x00\x00\x00\x00\x00')
        except:
             pass
    except ConnectionResetError:
        log(f"[ERRO HANDLER] Cliente {client_addr} resetou a conexão durante o handshake.")
    except Exception as e:
        log(f"[ERRO GERAL NO HANDLER] Falha para {client_addr}: {e}")
        # Tenta enviar resposta de falha se ainda não tiver enviado (0x05: Connection refused)
        try:
            client_socket.sendall(b'\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00') 
        except:
            pass
    finally:
        client_socket.close()
        if dest_socket: dest_socket.close()
        log(f"[HANDLER FIM] Conexão encerrada para {client_addr}.")

def tunnel_data_transfer(source_socket, destination_socket, client_addr):
    """Transfere dados bidirecionalmente usando select com timeout."""
    # Define um timeout de inatividade para o túnel de dados (5 minutos)
    TIMEOUT = 300 
    
    inputs = [source_socket, destination_socket]
    
    log(f"[TÚNEL INICIADO] Transferência de dados iniciada para {client_addr}. Timeout de inatividade: {TIMEOUT}s.") 
    
    while inputs:
        try:
            # Espera que um socket esteja pronto para ler ou atinge o timeout
            readable, _, exceptional = select.select(inputs, [], inputs, TIMEOUT)
        except Exception as e:
            log(f"[ERRO SELECT] Falha no select para {client_addr}: {e}") 
            break 
        
        if exceptional:
             log(f"[ERRO EXCEPCIONAL] Exceção em um socket para {client_addr}. Encerrando.")
             break

        if not readable:
            log(f"[TÚNEL TIMEOUT] Inatividade de {TIMEOUT}s atingida para {client_addr}. Encerrando o túnel.") 
            break

        for sock in readable:
            try:
                data = sock.recv(BUFFER_SIZE)
                
                if not data:
                    # Conexão encerrada pelo outro lado (graceful close)
                    log(f"[TÚNEL FECHADO] Conexão encerrada pelo lado {'CLIENTE' if sock == source_socket else 'DESTINO'} para {client_addr}.") 
                    # Remove o socket fechado para o loop continuar com o outro, se ainda ativo
                    if sock in inputs: inputs.remove(sock)
                    
                else:
                    # Encaminha os dados
                    if sock == source_socket:
                        destination_socket.sendall(data)
                        # log(f"[DADOS] {len(data)} bytes -> DESTINO") # Descomente para log de tráfego
                    else:
                        source_socket.sendall(data)
                        # log(f"[DADOS] {len(data)} bytes -> CLIENTE") # Descomente para log de tráfego
            
            except ConnectionResetError:
                # O outro lado forçou o fechamento (abrupt close)
                log(f"[ERRO DE DADOS] Conexão resetada pelo lado {'CLIENTE' if sock == source_socket else 'DESTINO'} para {client_addr}.") 
                inputs.clear() # Limpa tudo para encerrar o túnel
                break
            
            except Exception as e:
                # Outro erro de leitura/escrita, encerra
                log(f"[ERRO DE DADOS GERAL] Falha na leitura/escrita de dados para {client_addr}: {e}") 
                inputs.clear() # Limpa tudo para encerrar o túnel
                break
    
    log(f"[TÚNEL ENCERRADO] Fim da transferência de dados para {client_addr}.")


def main(monitor=None):
    """Inicializa e executa o servidor proxy SOCKS5 principal.

    Se um monitor do Kodi (xbmc.Monitor) for passado, o servidor checa
    o abort a cada 1 segundo e encerra limpo quando o Kodi fechar.
    """
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(10)
        # Timeout no accept para poder checar o monitor do Kodi periodicamente
        server_socket.settimeout(1.0)
        log(f"Servidor Proxy SOCKS5 + DNS-over-HTTPS (DoH) Ativo em {HOST}:{PORT}")
        
        while True:
            if monitor is not None and monitor.abortRequested():
                log("Kodi esta encerrando. Finalizando o proxy SOCKS5.")
                break
            try:
                client_socket, addr = server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            log(f"[NOVA CONEXÃO] Aceita de {addr[0]}:{addr[1]}")
            client_handler = threading.Thread(target=handle_socks5_connection, args=(client_socket, addr))
            client_handler.daemon = True
            client_handler.start()

    except KeyboardInterrupt:
        log("Servidor encerrado por comando do usuário.")
    except Exception as e:
        log(f"Erro Fatal no Servidor Principal: {e}")
    finally:
        if server_socket is not None:
            try:
                server_socket.close()
            except Exception:
                pass
        log("Servidor Proxy SOCKS5 encerrado.")

if __name__ == '__main__':
    main()