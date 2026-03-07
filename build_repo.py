# -*- coding: utf-8 -*-
import os
import hashlib
import zipfile
import re

class GeradorDeRepositorio:
    """
    Gera os arquivos addons.xml e addons.xml.md5 para um repositório Kodi.
    """

    def __init__(self):
        # Define o caminho base usando a localização deste script
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.caminho_zips = os.path.join(self.base_dir, "repo", "zips")
        self.caminho_addons_xml = os.path.join(self.base_dir, "repo", "addons.xml")
        self.caminho_addons_xml_md5 = os.path.join(self.base_dir, "repo", "addons.xml.md5")

        print(f"Diretório base: {self.base_dir}")
        
        self._compactar_addons()
        self._gerar_arquivo_addons()
        self._gerar_arquivo_md5()
        print("\nArquivos do repositório gerados com sucesso!")

    def _gerar_arquivo_addons(self):
        addons = []
        
        if not os.path.exists(self.caminho_zips):
            print(f"ERRO CRÍTICO: A pasta '{self.caminho_zips}' não existe!")
            return

        print(f"Lendo addons em '{self.caminho_zips}'...")
        for root, _, files in os.walk(self.caminho_zips):
            for file in files:
                if not file.endswith(".zip"):
                    continue
                
                caminho_zip = os.path.join(root, file)
                try:
                    with zipfile.ZipFile(caminho_zip, 'r') as addon_zip:
                        for info_zip in addon_zip.infolist():
                            if info_zip.filename.endswith('addon.xml') and not info_zip.is_dir():
                                partes = info_zip.filename.split('/')
                                if len(partes) == 2 and partes[1] == 'addon.xml':
                                    conteudo = addon_zip.read(info_zip.filename).decode('utf-8')
                                    
                                    # 1. Corrige erro de digitação específico
                                    conteudo = conteudo.replace('</requires>>', '</requires>')

                                    # 2. Limpeza Agressiva: Pega tudo a partir da primeira tag <addon
                                    # Isso remove <?xml ...?> e qualquer comentário inicial
                                    match = re.search(r'(<addon\s+[^>]+>)', conteudo)
                                    if match:
                                        start_pos = match.start()
                                        conteudo = conteudo[start_pos:]
                                    else:
                                        # Fallback: remove apenas o cabeçalho XML se não achar o padrão acima
                                        conteudo = re.sub(r'<\?xml.*?\?>', '', conteudo, flags=re.DOTALL).strip()

                                    addons.append(conteudo)
                                    print(f"  [OK] Processado: {partes[0]}")
                                    break
                except Exception as e:
                    print(f"  [ERRO] Falha em {file}: {e}")

        if not addons:
            print("AVISO: Nenhum addon foi encontrado nos zips!")
        
        xml_final = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
        xml_final += "\n".join(addons)
        xml_final += "\n</addons>"

        with open(self.caminho_addons_xml, "w", encoding="utf-8") as f:
            f.write(xml_final)
        print(f"\nArquivo 'addons.xml' salvo com {len(addons)} addons.")

    def _compactar_addons(self):
        if not os.path.exists(self.caminho_zips):
            return

        print("\nVerificando pastas para criar novos ZIPs...")
        for nome_addon in os.listdir(self.caminho_zips):
            caminho_addon = os.path.join(self.caminho_zips, nome_addon)
            
            if os.path.isdir(caminho_addon) and "addon.xml" in os.listdir(caminho_addon):
                try:
                    with open(os.path.join(caminho_addon, "addon.xml"), "r", encoding="utf-8") as f:
                        xml_content = f.read()
                    
                    id_match = re.search(r'<addon[^>]+id="([^"]+)"', xml_content)
                    ver_match = re.search(r'<addon[^>]+version="([^"]+)"', xml_content)
                    
                    if id_match and ver_match:
                        addon_id = id_match.group(1)
                        version = ver_match.group(1)
                        zip_name = f"{addon_id}-{version}.zip"
                        zip_path = os.path.join(caminho_addon, zip_name)
                        
                        # Remove zips antigos da pasta para evitar confusão
                        for file in os.listdir(caminho_addon):
                            if file.endswith(".zip") and file != zip_name:
                                os.remove(os.path.join(caminho_addon, file))
                                print(f"  - Removido zip antigo: {file}")
                        
                        print(f"  - Compactando {addon_id} v{version}...")
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for root, dirs, files in os.walk(caminho_addon):
                                for file in files:
                                    if file.endswith(".zip"): continue
                                    file_path = os.path.join(root, file)
                                    rel_path = os.path.relpath(file_path, self.caminho_zips)
                                    zf.write(file_path, rel_path)
                except Exception as e:
                    print(f"ERRO ao compactar {nome_addon}: {e}")

    def _gerar_arquivo_md5(self):
        try:
            with open(self.caminho_addons_xml, 'rb') as f:
                m = hashlib.md5(f.read()).hexdigest()
            
            with open(self.caminho_addons_xml_md5, "w", encoding="utf-8") as f:
                f.write(m)
            print(f"MD5 gerado: {m}")
        except Exception as e:
            print(f"ERRO no MD5: {e}")

if __name__ == "__main__":
    GeradorDeRepositorio()