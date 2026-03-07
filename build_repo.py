# -*- coding: utf-8 -*-
import os
import hashlib
import zipfile
import re

class GeradorDeRepositorio:
    """
    Gera os arquivos addons.xml e addons.xml.md5 para um repositório Kodi.
    
    Este script varre o diretório 'repo/zips', encontra todos os arquivos .zip de addons,
    extrai a informação de 'addon.xml' de cada um e cria um arquivo 'addons.xml'
    principal. Ele também gera o checksum MD5 correspondente.
    """

    def __init__(self):
        """
        Construtor da classe. Define os caminhos e inicia o processo de geração.
        """
        # Caminho para a pasta que contém os zips dos addons
        self.caminho_zips = os.path.join("repo", "zips")
        # Caminho para o arquivo addons.xml que será gerado
        self.caminho_addons_xml = os.path.join("repo", "addons.xml")
        # Caminho para o arquivo de checksum MD5
        self.caminho_addons_xml_md5 = os.path.join("repo", "addons.xml.md5")

        self._compactar_addons()
        self._gerar_arquivo_addons()
        self._gerar_arquivo_md5()
        print("\nArquivos do repositório gerados com sucesso!")

    def _gerar_arquivo_addons(self):
        """
        Varre os arquivos .zip em busca de addon.xml e gera o arquivo addons.xml.
        """
        addons = []
        
        if not os.path.exists(self.caminho_zips):
            print(f"AVISO: O diretório de zips '{self.caminho_zips}' não foi encontrado.")
            return

        print(f"Procurando por addons em '{self.caminho_zips}'...")
        # Percorre todas as subpastas em busca de arquivos .zip
        for root, _, files in os.walk(self.caminho_zips):
            for file in files:
                if not file.endswith(".zip"):
                    continue
                
                caminho_zip = os.path.join(root, file)
                try:
                    with zipfile.ZipFile(caminho_zip, 'r') as addon_zip:
                        # Procura pelo arquivo addon.xml dentro do zip.
                        # Geralmente está em uma subpasta, ex: 'plugin.video.gloriosotv/addon.xml'
                        for info_zip in addon_zip.infolist():
                            # Garante que é um arquivo addon.xml e não uma pasta
                            if info_zip.filename.endswith('addon.xml') and not info_zip.is_dir():
                                # Verifica se o addon.xml está na raiz de uma pasta dentro do zip
                                partes = info_zip.filename.split('/')
                                if len(partes) == 2 and partes[1] == 'addon.xml':
                                    conteudo = addon_zip.read(info_zip.filename).decode('utf-8')
                                    # Correção automática: Remove erro de digitação conhecido e garante XML limpo
                                    conteudo = conteudo.replace('</requires>>', '</requires>')

                                    # Limpeza robusta: Encontra a tag <addon e pega tudo a partir dela
                                    # Isso garante que <?xml ... ?> e qualquer lixo anterior seja removido
                                    pos = conteudo.find('<addon')
                                    if pos >= 0:
                                        conteudo = conteudo[pos:]
                                    else:
                                        conteudo = re.sub(r'<\?xml.*?\?>', '', conteudo, flags=re.DOTALL).strip()
                                    addons.append(conteudo)
                                    print(f"  - Adicionado: {partes[0]} (de {file})")
                                    # Encontrou o addon.xml principal, vai para o próximo zip
                                    break
                except Exception as e:
                    print(f"ERRO: Falha ao processar o arquivo {caminho_zip}: {e}")

        if not addons:
            print("Nenhum addon encontrado. O arquivo 'addons.xml' será gerado vazio.")
        
        # Monta o conteúdo final do arquivo addons.xml
        xml_final = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
        xml_final += "\n".join(addons)
        xml_final += "\n</addons>"

        # Escreve o arquivo
        with open(self.caminho_addons_xml, "w", encoding="utf-8") as f:
            f.write(xml_final)
        print(f"\n'{self.caminho_addons_xml}' criado com {len(addons)} addon(s).")

    def _compactar_addons(self):
        """
        Compacta as pastas dos addons em arquivos .zip, removendo os antigos.
        """
        if not os.path.exists(self.caminho_zips):
            return

        print("Verificando addons para compactação...")
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
                        
                        # Remove zips antigos e cria o novo
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
        """
        Gera o hash MD5 para o arquivo addons.xml.
        """
        try:
            with open(self.caminho_addons_xml, 'rb') as f:
                m = hashlib.md5(f.read()).hexdigest()
            
            with open(self.caminho_addons_xml_md5, "w", encoding="utf-8") as f:
                f.write(m)
            print(f"'{self.caminho_addons_xml_md5}' criado com o hash: {m}")
        except FileNotFoundError:
            print(f"ERRO: '{self.caminho_addons_xml}' não encontrado. Não foi possível gerar o arquivo MD5.")
        except Exception as e:
            print(f"ERRO: Ocorreu um erro ao gerar o arquivo MD5: {e}")

if __name__ == "__main__":
    GeradorDeRepositorio()