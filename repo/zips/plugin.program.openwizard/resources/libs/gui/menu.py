################################################################################
#      Copyright (C) 2019 drinfernoo                                           #
#                                                                              #
#  This Program is free software; you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by        #
#  the Free Software Foundation; either version 2, or (at your option)         #
#  any later version.                                                          #
#                                                                              #
#  This Program is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of              #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                #
#  GNU General Public License for more details.                                #
#                                                                              #
#  You should have received a copy of the GNU General Public License           #
#  along with XBMC; see the file COPYING.  If not, write to                    #
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.       #
#  http://www.gnu.org/copyleft/gpl.html                                        #
################################################################################

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import glob
import os
import re

try:  # Python 3
    from urllib.parse import quote_plus
    from urllib.request import urlretrieve
except ImportError:  # Python 2
    from urllib import quote_plus
    from urllib import urlretrieve

from resources.libs.common import directory
from resources.libs.common.config import CONFIG


###########################
#      Menu Items         #
###########################

def check_for_fm():
    if not xbmc.getCondVisibility('System.HasAddon(script.kodi.android.update)'):
        from resources.libs.gui import addon_menu
        addon_menu.install_from_kodi('script.kodi.android.update')
    
    try:
        updater = xbmcaddon.Addon('script.kodi.android.update')
    except RuntimeError as e:
        return False
        
    fm = int(updater.getSetting('File_Manager'))
    apps = xbmcvfs.listdir('androidapp://sources/apps/')[1]
    
    if fm == 0 and 'com.android.documentsui' not in apps:
        dialog = xbmcgui.Dialog()
        choose = dialog.yesno(CONFIG.ADDONTITLE, 'Parece que seu dispositivo nao tem gerenciador de arquivos padrao. Deseja definir um agora?')
        if not choose:
            dialog.ok(CONFIG.ADDONTITLE, 'Se um APK for baixado mas nao abrir para instalar, tente mudar o gerenciador de arquivos em "Configuracoes de Instalacao" do {}.'.format(CONFIG.ADDONTITLE))
        else:
            from resources.libs import install
            install.choose_file_manager()
            
    return True


def apk_menu(url=None):
    from resources.libs.common import logging
    from resources.libs.common import tools

    if check_for_fm():
        directory.add_dir('APKs Oficiais do Kodi', {'mode': 'kodiapk'}, icon=CONFIG.ICONAPK, themeit=CONFIG.THEME1)
        directory.add_separator()

    response = tools.open_url(CONFIG.APKFILE)
    url_response = tools.open_url(url)

    if response:
        TEMPAPKFILE = tools.clean_text(url_response.text if url else response.text)

        if TEMPAPKFILE:
            match = re.compile('name="(.+?)".+?ection="(.+?)".+?rl="(.+?)".+?con="(.+?)".+?anart="(.+?)".+?dult="(.+?)".+?escription="(.+?)"').findall(TEMPAPKFILE)
            if len(match) > 0:
                x = 0
                for aname, section, url, icon, fanart, adult, description in match:
                    if not CONFIG.SHOWADULT == 'true' and adult.lower() == 'yes':
                        continue
                    if section.lower() == 'yes':
                        x += 1
                        directory.add_dir("[B]{0}[/B]".format(aname), {'mode': 'apk', 'name': aname, 'url': url}, description=description, icon=icon, fanart=fanart, themeit=CONFIG.THEME3)
                    else:
                        x += 1
                        directory.add_file(aname, {'mode': 'apkinstall', 'name': aname, 'url': url}, description=description, icon=icon, fanart=fanart, themeit=CONFIG.THEME2)
                    if x == 0:
                        directory.add_file("Nenhum addon adicionado a este menu ainda!", themeit=CONFIG.THEME2)
            else:
                logging.log("[APK Menu] ERROR: Invalid Format.", level=xbmc.LOGERROR)
        else:
            logging.log("[APK Menu] ERROR: URL for apk list not working.", level=xbmc.LOGERROR)
            directory.add_file('URL do arquivo txt invalida', themeit=CONFIG.THEME3)
            directory.add_file('{0}'.format(CONFIG.APKFILE), themeit=CONFIG.THEME3)
    else:
        logging.log("[APK Menu] No APK list added.")


def youtube_menu(url=None):
    from resources.libs.common import logging
    from resources.libs.common import tools

    response = tools.open_url(CONFIG.YOUTUBEFILE)
    url_response = tools.open_url(url)

    if response:
        TEMPYOUTUBEFILE = url_response.text if url else response.text

        if TEMPYOUTUBEFILE:
            link = TEMPYOUTUBEFILE.replace('\n', '').replace('\r', '').replace('\t', '')
            match = re.compile('name="(.+?)".+?ection="(.+?)".+?rl="(.+?)".+?con="(.+?)".+?anart="(.+?)".+?escription="(.+?)"').findall(link)
            if len(match) > 0:
                for name, section, url, icon, fanart, description in match:
                    if section.lower() == "yes":
                        directory.add_dir("[B]{0}[/B]".format(name), {'mode': 'youtube', 'name': name, 'url': url}, description=description, icon=icon, fanart=fanart, themeit=CONFIG.THEME3)
                    else:
                        directory.add_file(name, {'mode': 'viewVideo', 'url': url}, description=description, icon=icon, fanart=fanart, themeit=CONFIG.THEME2)
            else:
                logging.log("[YouTube Menu] ERROR: Invalid Format.")
        else:
            logging.log("[YouTube Menu] ERROR: URL for YouTube list not working.")
            directory.add_file('URL do arquivo txt invalida', themeit=CONFIG.THEME3)
            directory.add_file('{0}'.format(CONFIG.YOUTUBEFILE), themeit=CONFIG.THEME3)
    else:
        logging.log("[YouTube Menu] No YouTube list added.")

#########################################NET TOOLS#############################################


def net_tools():
    directory.add_dir('Teste de Velocidade', {'mode': 'speedtest'}, icon=CONFIG.ICONSPEED, themeit=CONFIG.THEME1)
    if CONFIG.HIDESPACERS == 'No':
        directory.add_separator()
    directory.add_dir('Ver Endereco IP e MAC', {'mode': 'viewIP'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)


def view_ip():
    from resources.libs import speedtest

    mac, inter_ip, ip, city, state, country, isp = speedtest.net_info()
    directory.add_file('[COLOR {0}]MAC:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, mac), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]IP Interno: [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, inter_ip), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]IP Externo:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, ip), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Cidade:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, city), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Estado:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, state), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Pais:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, country), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]ISP:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, isp), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)


def speed_test():
    from datetime import date

    directory.add_file('Executar Teste de Velocidade', {'mode': 'speedtest'}, icon=CONFIG.ICONSPEED, themeit=CONFIG.THEME3)
    if os.path.exists(CONFIG.SPEEDTEST):
        speedimg = glob.glob(os.path.join(CONFIG.SPEEDTEST, '*.png'))
        speedimg.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        if len(speedimg) > 0:
            directory.add_file('Limpar Resultados', {'mode': 'clearspeedtest'}, icon=CONFIG.ICONSPEED, themeit=CONFIG.THEME3)
            directory.add_separator('Execucoes Anteriores', icon=CONFIG.ICONSPEED, themeit=CONFIG.THEME3)
            for item in speedimg:
                created = date.fromtimestamp(os.path.getmtime(item)).strftime('%m/%d/%Y %H:%M:%S')
                img = item.replace(os.path.join(CONFIG.SPEEDTEST, ''), '')
                directory.add_file('[B]{0}[/B]: [I]Executado {1}[/I]'.format(img, created), {'mode': 'viewspeedtest', 'name': img}, icon=CONFIG.ICONSPEED, themeit=CONFIG.THEME3)


def clear_speed_test():
    from resources.libs.common import tools

    speedimg = glob.glob(os.path.join(CONFIG.SPEEDTEST, '*.png'))
    for file in speedimg:
        tools.remove_file(file)


def view_speed_test(img=None):
    from resources.libs.gui import window

    img = os.path.join(CONFIG.SPEEDTEST, img)
    window.show_speed_test(img)


def run_speed_test():
    from resources.libs.common import logging
    from resources.libs import speedtest

    try:
        found = speedtest.speedtest()
        if not os.path.exists(CONFIG.SPEEDTEST):
            os.makedirs(CONFIG.SPEEDTEST)
        urlsplits = found[0].split('/')
        dest = os.path.join(CONFIG.SPEEDTEST, urlsplits[-1])
        urlretrieve(found[0], dest)
        view_speed_test(urlsplits[-1])
    except Exception as e:
        logging.log("[Teste de Velocidade] Error Running Teste de Velocidade: {0}".format(e), level=xbmc.LOGDEBUG)
        pass


def system_info():
    from resources.libs.common import logging
    from resources.libs.common import tools
    from resources.libs import speedtest

    infoLabel = ['System.FriendlyName', 'System.BuildVersion', 'System.CpuUsage', 'System.ScreenMode',
                 'Network.IPAddress', 'Network.MacAddress', 'System.Uptime', 'System.TotalUptime', 'System.FreeSpace',
                 'System.UsedSpace', 'System.TotalSpace', 'System.Memory(free)', 'System.Memory(used)',
                 'System.Memory(total)']
    data = []
    x = 0
    for info in infoLabel:
        temp = tools.get_info_label(info)
        y = 0
        while temp == "Busy" and y < 10:
            temp = tools.get_info_label(info)
            y += 1
            logging.log("{0} sleep {1}".format(info, str(y)))
            xbmc.sleep(200)
        data.append(temp)
        x += 1
    storage_free = data[8] if 'Una' in data[8] else tools.convert_size(int(float(data[8][:-8])) * 1024 * 1024)
    storage_used = data[9] if 'Una' in data[9] else tools.convert_size(int(float(data[9][:-8])) * 1024 * 1024)
    storage_total = data[10] if 'Una' in data[10] else tools.convert_size(int(float(data[10][:-8])) * 1024 * 1024)
    ram_free = tools.convert_size(int(float(data[11][:-2])) * 1024 * 1024)
    ram_used = tools.convert_size(int(float(data[12][:-2])) * 1024 * 1024)
    ram_total = tools.convert_size(int(float(data[13][:-2])) * 1024 * 1024)

    picture = []
    music = []
    video = []
    programs = []
    repos = []
    scripts = []
    skins = []

    fold = glob.glob(os.path.join(CONFIG.ADDONS, '*/'))
    for folder in sorted(fold, key = lambda x: x):
        foldername = os.path.split(folder[:-1])[1]
        if foldername == 'packages': continue
        xml = os.path.join(folder, 'addon.xml')
        if os.path.exists(xml):
            prov = re.compile("<provides>(.+?)</provides>").findall(tools.read_from_file(xml))
            if len(prov) == 0:
                if foldername.startswith('skin'):
                    skins.append(foldername)
                elif foldername.startswith('repo'):
                    repos.append(foldername)
                else:
                    scripts.append(foldername)
            elif not (prov[0]).find('executable') == -1:
                programs.append(foldername)
            elif not (prov[0]).find('video') == -1:
                video.append(foldername)
            elif not (prov[0]).find('audio') == -1:
                music.append(foldername)
            elif not (prov[0]).find('image') == -1:
                picture.append(foldername)

    directory.add_file('[B]Informacoes da Central de Midia:[/B]', icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Nome:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, data[0]), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('[COLOR {0}]Versao:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, data[1]), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('[COLOR {0}]Plataforma:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, tools.platform().title()), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('[COLOR {0}]Uso de CPU:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, data[2]), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('[COLOR {0}]Modo de Tela:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, data[3]), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)

    directory.add_file('[B]Tempo Ligado:[/B]', icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Tempo Ligado Atual:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, data[6]), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Tempo Ligado Total:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, data[7]), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)

    directory.add_file('[B]Armazenamento Local:[/B]', icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Armazenamento Usado:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, storage_used), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Armazenamento Livre:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, storage_free), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Armazenamento Total:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, storage_total), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)

    directory.add_file('[B]Uso de RAM:[/B]', icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Memoria Usada:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, ram_free), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Memoria Livre:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, ram_used), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Memoria Total:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, ram_total), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)

    mac, inter_ip, ip, city, state, country, isp = speedtest.net_info()
    directory.add_file('[B]Rede:[/B]', icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Mac:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, mac), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]IP Interno: [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, inter_ip), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]IP Externo:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, ip), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Cidade:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, city), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Estado:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, state), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Pais:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, country), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]ISP:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, isp), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)

    totalcount = len(picture) + len(music) + len(video) + len(programs) + len(scripts) + len(skins) + len(repos)
    directory.add_file('[B]Addons([COLOR {0}]{1}[/COLOR]):[/B]'.format(CONFIG.COLOR1, totalcount), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Addons de Video:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, str(len(video))), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Addons de Programas:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, str(len(programs))), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Addons de Musica:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, str(len(music))), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Addons de Imagem:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, str(len(picture))), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Repositorios:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, str(len(repos))), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Skins:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, str(len(skins))), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)
    directory.add_file('[COLOR {0}]Scripts/Modulos:[/COLOR] [COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR1, CONFIG.COLOR2, str(len(scripts))), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME2)


def save_menu():
    on = '[COLOR springgreen]ON[/COLOR]'
    off = '[COLOR red]OFF[/COLOR]'

    trakt = 'true' if CONFIG.KEEPTRAKT == 'true' else 'false'
    debrid = 'true' if CONFIG.KEEPDEBRID == 'true' else 'false'
    login = 'true' if CONFIG.KEEPLOGIN == 'true' else 'false'
    sources = 'true' if CONFIG.KEEPSOURCES == 'true' else 'false'
    profiles = 'true' if CONFIG.KEEPPROFILES == 'true' else 'false'
    playercore = 'true' if CONFIG.KEEPPLAYERCORE == 'true' else 'false'
    guisettings = 'true' if CONFIG.KEEPGUISETTINGS == 'true' else 'false'
    favourites = 'true' if CONFIG.KEEPFAVS == 'true' else 'false'
    repos = 'true' if CONFIG.KEEPREPOS == 'true' else 'false'
    super = 'true' if CONFIG.KEEPSUPER == 'true' else 'false'
    whitelist = 'true' if CONFIG.KEEPWHITELIST == 'true' else 'false'

    directory.add_dir('Manter Dados do Trakt', {'mode': 'trakt'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME1)
    directory.add_dir('Manter Debrid', {'mode': 'realdebrid'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME1)
    directory.add_dir('Manter Informacoes de Login', {'mode': 'login'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME1)
    directory.add_file('Importar Dados Salvos', {'mode': 'managedata', 'name': 'import'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Exportar Dados Salvos', {'mode': 'managedata', 'name': 'export'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('- Clique para alternar configuracoes -', themeit=CONFIG.THEME3)
    directory.add_file('Salvar Trakt: {0}'.format(trakt.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keeptrakt'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME1)
    directory.add_file('Salvar Debrid: {0}'.format(debrid.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepdebrid'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME1)
    directory.add_file('Salvar Informacoes de Login: {0}'.format(login.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keeplogin'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME1)
    directory.add_file('Manter \'Sources.xml\': {0}'.format(sources.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepsources'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Manter \'Profiles.xml\': {0}'.format(profiles.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepprofiles'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Manter \'playercorefactory.xml\': {0}'.format(playercore.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepplayercore'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Manter \'guisettings.xml\': {0}'.format(guisettings.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepguiseettings'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Manter \'Favourites.xml\': {0}'.format(favourites.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepfavourites'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Manter Super Favourites: {0}'.format(super.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepsuper'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Manter Repositorios Instalados: {0}'.format(repos.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keeprepos'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    directory.add_file('Manter minha \'WhiteList\': {0}'.format(whitelist.replace('true', on).replace('false', off)), {'mode': 'togglesetting', 'name': 'keepwhitelist'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
    if whitelist == 'true':
        directory.add_file('Editar minha Whitelist', {'mode': 'whitelist', 'name': 'edit'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
        directory.add_file('Ver minha Whitelist', {'mode': 'whitelist', 'name': 'view'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
        directory.add_file('Limpar minha Whitelist', {'mode': 'whitelist', 'name': 'clear'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
        directory.add_file('Importar minha Whitelist', {'mode': 'whitelist', 'name': 'import'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)
        directory.add_file('Exportar minha Whitelist', {'mode': 'whitelist', 'name': 'export'}, icon=CONFIG.ICONSAVE, themeit=CONFIG.THEME1)


def trakt_menu():
    from resources.libs import traktit

    keep_trakt = '[COLOR springgreen]ON[/COLOR]' if CONFIG.KEEPTRAKT == 'true' else '[COLOR red]OFF[/COLOR]'
    last = str(CONFIG.TRAKTSAVE) if not CONFIG.TRAKTSAVE == '' else 'Os dados do Trakt ainda nao foram salvos.'
    directory.add_file('[I]Cadastre uma conta GRATIS em https://www.trakt.tv/[/I]', icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)
    directory.add_file('Salvar Dados do Trakt: {0}'.format(keep_trakt), {'mode': 'togglesetting', 'name': 'keeptrakt'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)
    if CONFIG.KEEPTRAKT == 'true':
        directory.add_file('Ultimo Salvamento: {0}'.format(str(last)), icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)
    directory.add_separator(icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)

    for trakt in traktit.ORDER:
        if xbmc.getCondVisibility('System.HasAddon({0})'.format(traktit.TRAKTID[trakt]['plugin'])):
            name = traktit.TRAKTID[trakt]['name']
            path = traktit.TRAKTID[trakt]['path']
            saved = traktit.TRAKTID[trakt]['saved']
            file = traktit.TRAKTID[trakt]['file']
            user = CONFIG.get_setting(saved)
            auser = traktit.trakt_user(trakt)
            icon = traktit.TRAKTID[trakt]['icon'] if os.path.exists(path) else CONFIG.ICONTRAKT
            fanart = traktit.TRAKTID[trakt]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
            menu = create_addon_data_menu('Trakt', trakt)
            menu2 = create_save_data_menu('Trakt', trakt)
            menu.append((CONFIG.THEME2.format('Configuracoes de {0}'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=trakt)'.format(CONFIG.ADDON_ID, trakt)))

            directory.add_file('[+]-> {0}'.format(name), icon=icon, fanart=fanart, themeit=CONFIG.THEME3)
            if not os.path.exists(path):
                directory.add_file('[COLOR red]Dados do Addon: Nao Instalado[/COLOR]', icon=icon, fanart=fanart, menu=menu)
            elif not auser:
                directory.add_file('[COLOR red]Dados do Addon: Nao Registrado[/COLOR]', {'mode': 'authtrakt', 'name': trakt}, icon=icon, fanart=fanart, menu=menu)
            else:
                directory.add_file('[COLOR springgreen]Dados do Addon: {0}[/COLOR]'.format(auser), {'mode': 'authtrakt', 'name': trakt}, icon=icon, fanart=fanart, menu=menu)
            if user == "":
                if os.path.exists(file):
                    directory.add_file('[COLOR red]Dados Salvos: Arquivo encontrado (Importar Dados)[/COLOR]', {'mode': 'importtrakt', 'name': trakt}, icon=icon, fanart=fanart, menu=menu2)
                else:
                    directory.add_file('[COLOR red]Dados Salvos: Nao Salvo[/COLOR]', {'mode': 'savetrakt', 'name': trakt}, icon=icon, fanart=fanart, menu=menu2)
            else:
                directory.add_file('[COLOR springgreen]Dados Salvos: {0}[/COLOR]'.format(user), icon=icon, fanart=fanart, menu=menu2)

    directory.add_separator()
    directory.add_file('Salvar Todos os Dados do Trakt', {'mode': 'savetrakt', 'name': 'all'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)
    directory.add_file('Recuperar Todos os Dados Salvos do Trakt', {'mode': 'restoretrakt', 'name': 'all'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)
    directory.add_file('Importar Dados do Trakt', {'mode': 'importtrakt', 'name': 'all'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)
    directory.add_file('Limpar Todos os Dados de Trakt dos Addons', {'mode': 'addontrakt', 'name': 'all'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)
    directory.add_file('Limpar Todos os Dados Salvos do Trakt', {'mode': 'cleartrakt', 'name': 'all'}, icon=CONFIG.ICONTRAKT, themeit=CONFIG.THEME3)


def debrid_menu():
    from resources.libs import debridit

    keep_debrid = '[COLOR springgreen]ON[/COLOR]' if CONFIG.KEEPDEBRID == 'true' else '[COLOR red]OFF[/COLOR]'
    last = str(CONFIG.DEBRIDSAVE) if not CONFIG.DEBRIDSAVE == '' else 'As autorizacoes Debrid ainda nao foram salvas.'
    directory.add_file('[I]https://www.real-debrid.com/ e um servico PAGO.[/I]', icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    directory.add_file('[I]https://www.premiumize.me/ e um servico PAGO.[/I]', icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    directory.add_file('Salvar Dados de Debrid: {0}'.format(keep_debrid), {'mode': 'togglesetting', 'name': 'keepdebrid'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    if CONFIG.KEEPDEBRID == 'true':
        directory.add_file('Ultimo Salvamento: {0}'.format(str(last)), icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    directory.add_separator(icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)

    for debrid in debridit.ORDER:
        if xbmc.getCondVisibility('System.HasAddon({0})'.format(debridit.DEBRIDID[debrid]['plugin'])):
            name = debridit.DEBRIDID[debrid]['name']
            path = debridit.DEBRIDID[debrid]['path']
            saved = debridit.DEBRIDID[debrid]['saved']
            file = debridit.DEBRIDID[debrid]['file']
            user = CONFIG.get_setting(saved)
            auser = debridit.debrid_user(debrid)
            icon = debridit.DEBRIDID[debrid]['icon'] if os.path.exists(path) else CONFIG.ICONDEBRID
            fanart = debridit.DEBRIDID[debrid]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
            menu = create_addon_data_menu('Debrid', debrid)
            menu2 = create_save_data_menu('Debrid', debrid)
            menu.append((CONFIG.THEME2.format('Configuracoes de {0}'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=debrid)'.format(CONFIG.ADDON_ID, debrid)))

            directory.add_file('[+]-> {0}'.format(name), icon=icon, fanart=fanart, themeit=CONFIG.THEME3)
            if not os.path.exists(path):
                directory.add_file('[COLOR red]Dados do Addon: Nao Instalado[/COLOR]', icon=icon, fanart=fanart, menu=menu)
            elif not auser:
                directory.add_file('[COLOR red]Dados do Addon: Nao Registrado[/COLOR]', {'mode': 'authdebrid', 'name': debrid}, icon=icon, fanart=fanart, menu=menu)
            else:
                directory.add_file('[COLOR springgreen]Dados do Addon: {0}[/COLOR]'.format(auser), {'mode': 'authdebrid', 'name': debrid}, icon=icon, fanart=fanart, menu=menu)
            if user == "":
                if os.path.exists(file):
                    directory.add_file('[COLOR red]Dados Salvos: Arquivo encontrado (Importar Dados)[/COLOR]', {'mode': 'importdebrid', 'name': debrid}, icon=icon, fanart=fanart, menu=menu2)
                else:
                    directory.add_file('[COLOR red]Dados Salvos: Nao Salvo[/COLOR]', {'mode': 'savedebrid', 'name': debrid}, icon=icon, fanart=fanart, menu=menu2)
            else:
                directory.add_file('[COLOR springgreen]Dados Salvos: {0}[/COLOR]'.format(user), icon=icon, fanart=fanart, menu=menu2)

    directory.add_separator(themeit=CONFIG.THEME3)
    directory.add_file('Salvar Todos os Dados de Debrid', {'mode': 'savedebrid', 'name': 'all'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    directory.add_file('Recuperar Todos os Dados Salvos de Debrid', {'mode': 'restoredebrid', 'name': 'all'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    directory.add_file('Importar Dados de Debrid', {'mode': 'importdebrid', 'name': 'all'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    directory.add_file('Limpar Todos os Dados de Debrid dos Addons', {'mode': 'addondebrid', 'name': 'all'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)
    directory.add_file('Limpar Todos os Dados Salvos de Debrid', {'mode': 'cleardebrid', 'name': 'all'}, icon=CONFIG.ICONDEBRID, themeit=CONFIG.THEME3)


def login_menu():
    from resources.libs import loginit

    keep_login = '[COLOR springgreen]ON[/COLOR]' if CONFIG.KEEPLOGIN == 'true' else '[COLOR red]OFF[/COLOR]'
    last = str(CONFIG.LOGINSAVE) if not CONFIG.LOGINSAVE == '' else 'Os dados de login ainda nao foram salvos.'
    directory.add_file('[I]Varios desses addons sao servicos PAGOS.[/I]', icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)
    directory.add_file('Salvar Chaves de API: {0}'.format(keep_login), {'mode': 'togglesetting', 'name': 'keeplogin'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)
    if CONFIG.KEEPLOGIN == 'true':
        directory.add_file('Ultimo Salvamento: {0}'.format(str(last)), icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)
    directory.add_separator(icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)

    for login in loginit.ORDER:
        if xbmc.getCondVisibility('System.HasAddon({0})'.format(loginit.LOGINID[login]['plugin'])):
            name = loginit.LOGINID[login]['name']
            path = loginit.LOGINID[login]['path']
            saved = loginit.LOGINID[login]['saved']
            file = loginit.LOGINID[login]['file']
            user = CONFIG.get_setting(saved)
            auser = loginit.login_user(login)
            icon = loginit.LOGINID[login]['icon'] if os.path.exists(path) else CONFIG.ICONLOGIN
            fanart = loginit.LOGINID[login]['fanart'] if os.path.exists(path) else CONFIG.ADDON_FANART
            menu = create_addon_data_menu('Login', login)
            menu2 = create_save_data_menu('Login', login)
            menu.append((CONFIG.THEME2.format('Configuracoes de {0}'.format(name)), 'RunPlugin(plugin://{0}/?mode=opensettings&name={1}&url=login)'.format(CONFIG.ADDON_ID, login)))

            directory.add_file('[+]-> {0}'.format(name), icon=icon, fanart=fanart, themeit=CONFIG.THEME3)
            if not os.path.exists(path):
                directory.add_file('[COLOR red]Dados do Addon: Nao Instalado[/COLOR]', icon=icon, fanart=fanart, menu=menu)
            elif not auser:
                directory.add_file('[COLOR red]Dados do Addon: Nao Registrado[/COLOR]', {'mode': 'authlogin', 'name': login}, icon=icon, fanart=fanart, menu=menu)
            else:
                directory.add_file('[COLOR springgreen]Dados do Addon: {0}[/COLOR]'.format(auser), {'mode': 'authlogin', 'name': login}, icon=icon, fanart=fanart, menu=menu)
            if user == "":
                if os.path.exists(file):
                    directory.add_file('[COLOR red]Dados Salvos: Arquivo encontrado (Importar Dados)[/COLOR]', {'mode': 'importlogin', 'name': login}, icon=icon, fanart=fanart, menu=menu2)
                else:
                    directory.add_file('[COLOR red]Dados Salvos: Nao Salvo[/COLOR]', {'mode': 'savelogin', 'name': login}, icon=icon, fanart=fanart, menu=menu2)
            else:
                directory.add_file('[COLOR springgreen]Dados Salvos: {0}[/COLOR]'.format(user), icon=icon, fanart=fanart, menu=menu2)

    directory.add_separator(themeit=CONFIG.THEME3)
    directory.add_file('Salvar Todas as Informacoes de Login', {'mode': 'savelogin', 'name': 'all'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)
    directory.add_file('Recuperar Todas as Informacoes de Login salvas', {'mode': 'restorelogin', 'name': 'all'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)
    directory.add_file('Importar Informacoes de Login', {'mode': 'importlogin', 'name': 'all'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)
    directory.add_file('Limpar Todas as Informacoes de Login dos Addons', {'mode': 'addonlogin', 'name': 'all'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)
    directory.add_file('Limpar Todas as Informacoes de Login salvas', {'mode': 'clearlogin', 'name': 'all'}, icon=CONFIG.ICONLOGIN, themeit=CONFIG.THEME3)


def enable_addons(all=False):
    from resources.libs.common import tools
    
    from xml.etree import ElementTree

    fold = glob.glob(os.path.join(CONFIG.ADDONS, '*/'))
    addonnames = []
    addonids = []
    for folder in sorted(fold, key=lambda x: x):
        foldername = os.path.split(folder[:-1])[1]
        if foldername in CONFIG.EXCLUDES:
            continue
        elif foldername in CONFIG.DEFAULTPLUGINS:
            continue
        elif foldername == 'packages':
            continue
        xml = os.path.join(folder, 'addon.xml')
        if os.path.exists(xml):
            root = ElementTree.parse(xml).getroot()
            addonid = root.get('id')
            addonname = root.get('name')
            addonids.append(addonid)
            addonnames.append(addonname)
    if not all:
        if len(addonids) == 0:
            directory.add_file("Nenhum addon encontrado para ativar ou desativar.", icon=CONFIG.ICONMAINT)
        else:
            directory.add_file("[I][B][COLOR red]!!Aviso: Desativar alguns addons pode causar problemas!![/COLOR][/B][/I]", icon=CONFIG.ICONMAINT)
            directory.add_dir('Ativar Todos os Addons', {'mode': 'enableall'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            for i in range(0, len(addonids)):
                folder = os.path.join(CONFIG.ADDONS, addonids[i])
                icon = os.path.join(folder, 'icon.png') if os.path.exists(os.path.join(folder, 'icon.png')) else CONFIG.ADDON_ICON
                fanart = os.path.join(folder, 'fanart.jpg') if os.path.exists(os.path.join(folder, 'fanart.jpg')) else CONFIG.ADDON_FANART
                if tools.get_addon_info(addonids[i], 'name'):
                    state = "[COLOR springgreen][Ativado][/COLOR]"
                    goto = "false"
                else:
                    state = "[COLOR red][Desativado][/COLOR]"
                    goto = "true"

                directory.add_file("{0} {1}".format(state, addonnames[i]), {'mode': 'toggleaddon', 'name': addonids[i], 'url': goto}, icon=icon, fanart=fanart)
    else:
        from resources.libs import db
        for addonid in addonids:
            db.toggle_addon(addonid, 'true')
        xbmc.executebuiltin('Container.Refresh()')


def remove_addon_data_menu():
    if os.path.exists(CONFIG.ADDON_DATA):
        directory.add_file('[COLOR red][B][REMOVER][/B][/COLOR] Todo o Addon_Data', {'mode': 'removedata', 'name': 'all'}, themeit=CONFIG.THEME2)
        directory.add_file('[COLOR red][B][REMOVER][/B][/COLOR] Todo o Addon_Data de Addons nao instalados', {'mode': 'removedata', 'name': 'uninstalled'}, themeit=CONFIG.THEME2)
        directory.add_file('[COLOR red][B][REMOVER][/B][/COLOR] Todas as Pastas Vazias em Addon_Data', {'mode': 'removedata', 'name': 'empty'}, themeit=CONFIG.THEME2)
        directory.add_file('[COLOR red][B][REMOVER][/B][/COLOR] {0} Addon_Data'.format(CONFIG.ADDONTITLE), {'mode': 'resetaddon'}, themeit=CONFIG.THEME2)
        directory.add_separator(themeit=CONFIG.THEME3)
        fold = glob.glob(os.path.join(CONFIG.ADDON_DATA, '*/'))
        for folder in sorted(fold, key = lambda x: x):
            foldername = folder.replace(CONFIG.ADDON_DATA, '').replace('\\', '').replace('/', '')
            icon = os.path.join(folder.replace(CONFIG.ADDON_DATA, CONFIG.ADDONS), 'icon.png')
            fanart = os.path.join(folder.replace(CONFIG.ADDON_DATA, CONFIG.ADDONS), 'fanart.png')
            folderdisplay = foldername
            replace = {'audio.': '[COLOR orange][AUDIO] [/COLOR]', 'metadata.': '[COLOR cyan][METADATA] [/COLOR]',
                       'module.': '[COLOR orange][MODULE] [/COLOR]', 'plugin.': '[COLOR blue][PLUGIN] [/COLOR]',
                       'program.': '[COLOR orange][PROGRAM] [/COLOR]', 'repository.': '[COLOR gold][REPO] [/COLOR]',
                       'script.': '[COLOR springgreen][SCRIPT] [/COLOR]',
                       'service.': '[COLOR springgreen][SERVICE] [/COLOR]', 'skin.': '[COLOR dodgerblue][SKIN] [/COLOR]',
                       'video.': '[COLOR orange][VIDEO] [/COLOR]', 'weather.': '[COLOR yellow][WEATHER] [/COLOR]'}
            for rep in replace:
                folderdisplay = folderdisplay.replace(rep, replace[rep])
            if foldername in CONFIG.EXCLUDES:
                folderdisplay = '[COLOR springgreen][B][PROTEGIDO][/B][/COLOR] {0}'.format(folderdisplay)
            else:
                folderdisplay = '[COLOR red][B][REMOVER][/B][/COLOR] {0}'.format(folderdisplay)
            directory.add_file(' {0}'.format(folderdisplay), {'mode': 'removedata', 'name': foldername}, icon=icon, fanart=fanart, themeit=CONFIG.THEME2)
    else:
        directory.add_file('Nenhuma pasta de dados de addon encontrada.', themeit=CONFIG.THEME3)


def change_freq():
    from resources.libs.common import logging

    dialog = xbmcgui.Dialog()

    change = dialog.select("[COLOR {0}]Com que frequencia deseja Limpeza Automatica na Inicializacao?[/COLOR]".format(CONFIG.COLOR2), CONFIG.CLEANFREQ)
    if not change == -1:
        CONFIG.set_setting('autocleanfreq', str(change))
        logging.log_notify('[COLOR {0}]Limpeza Automatica[/COLOR]'.format(CONFIG.COLOR1),
                           '[COLOR {0}]Frequencia Agora {1}[/COLOR]'.format(CONFIG.COLOR2, CONFIG.CLEANFREQ[change]))


def developer():
    directory.add_file('Criar QR Code', {'mode': 'createqr'}, themeit=CONFIG.THEME1)
    directory.add_file('Testar Notificacoes', {'mode': 'testnotify'}, themeit=CONFIG.THEME1)
    directory.add_file('Testar Atualizacao', {'mode': 'testupdate'}, themeit=CONFIG.THEME1)
    directory.add_file('Testar Aviso de Build', {'mode': 'testbuildprompt'}, themeit=CONFIG.THEME1)
    directory.add_file('Testar Configuracoes de Salvar Dados', {'mode': 'testsavedata'}, themeit=CONFIG.THEME1)
    directory.add_file('Testar Deteccao de Binarios', {'mode': 'binarycheck'}, themeit=CONFIG.THEME1)


###########################
#      Misc Functions     #
###########################


def create_addon_data_menu(add='', name=''):
    menu_items = []

    add2 = quote_plus(add.lower().replace(' ', ''))
    add3 = add.replace('Debrid', 'Real Debrid')
    name2 = quote_plus(name.lower().replace(' ', ''))
    name = name.replace('url', 'URL Resolver')
    menu_items.append((CONFIG.THEME2.format(name.title()), ' '))
    menu_items.append((CONFIG.THEME3.format('Salvar Dados de {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=save{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Restaurar Dados de {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=restore{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Limpar Dados de {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=clear{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))

    menu_items.append((CONFIG.THEME2.format('Configuracoes do {0}'.format(CONFIG.ADDONTITLE)), 'RunPlugin(plugin://{0}/?mode=settings)'.format(CONFIG.ADDON_ID)))

    return menu_items


def create_save_data_menu(add='', name=''):
    menu_items = []

    add2 = quote_plus(add.lower().replace(' ', ''))
    add3 = add.replace('Debrid', 'Real Debrid')
    name2 = quote_plus(name.lower().replace(' ', ''))
    name = name.replace('url', 'URL Resolver')
    menu_items.append((CONFIG.THEME2.format(name.title()), ' '))
    menu_items.append((CONFIG.THEME3.format('Registrar {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=auth{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Salvar Dados de {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=save{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Restaurar Dados de {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=restore{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Importar Dados de {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=import{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))
    menu_items.append((CONFIG.THEME3.format('Limpar Dados de Addon {0}'.format(add3)), 'RunPlugin(plugin://{0}/?mode=addon{1}&name={2})'.format(CONFIG.ADDON_ID, add2, name2)))

    menu_items.append((CONFIG.THEME2.format('Configuracoes do {0}'.format(CONFIG.ADDONTITLE)), 'RunPlugin(plugin://{0}/?mode=settings)'.format(CONFIG.ADDON_ID)))

    return menu_items
