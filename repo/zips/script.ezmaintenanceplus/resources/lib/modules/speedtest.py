#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import urllib.request
import xml.etree.ElementTree as ET

try:
    import xbmc
    import xbmcgui
    KODI = True
except ImportError:
    xbmc = None
    xbmcgui = None
    KODI = False


def testar_velocidade():
    # Cabeçalhos completos para simular um navegador real e evitar o Erro 403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    dp = None
    if KODI:
        dp = xbmcgui.DialogProgress()
        dp.create('Speedtest (Ookla)', 'Buscando servidores oficiais do Speedtest (Ookla)...')

    print("Buscando servidores oficiais do Speedtest (Ookla)...")

    # 1. Obtém a lista de servidores usando o subdomínio 'c.' que é aberto para APIs
    url_servidor = None
    cidade = ""
    pais = ""
    host = ""

    urls_servidores = [
        "http://c.speedtest.net/speedtest-servers-static.php",
        "https://c.speedtest.net/speedtest-servers-static.php",
        "http://www.speedtest.net/speedtest-servers-static.php"
    ]

    for url_lista in urls_servidores:
        try:
            req = urllib.request.Request(url_lista, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                tree = ET.fromstring(resp.read())
                servidor = tree.find(".//server")
                if servidor is not None:
                    url_servidor = servidor.attrib['url']
                    host = servidor.attrib.get('host', '')
                    cidade = servidor.attrib.get('name', '')
                    pais = servidor.attrib.get('country', '')
                    print(f"Servidor selecionado: {cidade} - {pais} ({host})")
                    break
        except Exception:
            continue

    if not url_servidor:
        erro_msg = "Erro ao obter servidor do Speedtest."
        print(erro_msg)
        if dp:
            dp.close()
        if KODI:
            xbmcgui.Dialog().ok("Speedtest", erro_msg)
        return None

    base_url = url_servidor.rsplit('/', 1)[0]

    # 2. Medindo Latência / Ping
    print("Medindo ping no servidor Ookla...")
    if dp:
        if dp.iscanceled():
            dp.close()
            return None
        dp.update(25, f"Medindo ping no servidor Ookla...\nServidor: {cidade} - {pais}")

    pings = []
    for _ in range(5):
        if dp and dp.iscanceled():
            dp.close()
            return None
        inicio = time.time()
        try:
            req = urllib.request.Request(f"{base_url}/latency.txt", headers=headers)
            with urllib.request.urlopen(req, timeout=3):
                pings.append((time.time() - inicio) * 1000)
        except Exception:
            pass

    ping_medio = sum(pings) / len(pings) if pings else 0

    # 3. Medindo Download
    print("Testando velocidade de download...")
    if dp:
        if dp.iscanceled():
            dp.close()
            return None
        dp.update(50, f"Testando velocidade de download...\nPing: {ping_medio:.2f} ms")

    download_speed = 0
    try:
        url_dl = f"{base_url}/random3500x3500.jpg"
        inicio = time.time()
        req = urllib.request.Request(url_dl, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resposta:
            dados = resposta.read()
            tempo_total = max(time.time() - inicio, 0.001)
            tamanho_bits = len(dados) * 8
            download_speed = (tamanho_bits / 1_000_000) / tempo_total
    except Exception as e:
        print(f"Erro no teste de download: {e}")

    # 4. Medindo Upload
    print("Testando velocidade de upload...")
    if dp:
        if dp.iscanceled():
            dp.close()
            return None
        dp.update(75, f"Testando velocidade de upload...\nDownload: {download_speed:.2f} Mbps")

    upload_speed = 0
    try:
        payload = b'0' * (10 * 1024 * 1024)
        url_ul = f"{base_url}/upload.php"

        inicio = time.time()
        req = urllib.request.Request(url_ul, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=25) as resposta:
            tempo_total = max(time.time() - inicio, 0.001)
            tamanho_bits = len(payload) * 8
            upload_speed = (tamanho_bits / 1_000_000) / tempo_total
    except Exception as e:
        print(f"Erro no teste de upload: {e}")

    if dp:
        dp.close()

    # Exibição dos resultados
    print("\n" + "="*35)
    print("   RESULTADO OFICIAL SPEEDTEST   ")
    print("="*35)
    print(f"Ping:     {ping_medio:.2f} ms")
    print(f"Download: {download_speed:.2f} Mbps")
    print(f"Upload:   {upload_speed:.2f} Mbps")
    print("="*35)

    if KODI:
        dialog_texto = (
            f"Servidor: {cidade} - {pais} ({host})\n\n"
            f"Ping:     {ping_medio:.2f} ms\n"
            f"Download: {download_speed:.2f} Mbps\n"
            f"Upload:   {upload_speed:.2f} Mbps"
        )
        xbmcgui.Dialog().ok("Resultado Speedtest", dialog_texto)

    return {
        'ping': ping_medio,
        'download': download_speed,
        'upload': upload_speed,
        'server': f"{cidade} - {pais} ({host})"
    }


def main():
    return testar_velocidade()


def shell():
    return testar_velocidade()


if __name__ == "__main__":
    testar_velocidade()
