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

import os

from resources.libs.common import directory
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common.config import CONFIG


class MaintenanceMenu:

    def get_listing(self):
        directory.add_dir('[B]Ferramentas de Limpeza[/B]', {'mode': 'maint', 'name': 'clean'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)
        directory.add_dir('[B]Ferramentas de Addon[/B]', {'mode': 'maint', 'name': 'addon'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)
        directory.add_dir('[B]Ferramentas de Log[/B]', {'mode': 'maint', 'name': 'logging'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)
        directory.add_dir('[B]Manutencao Diversa[/B]', {'mode': 'maint', 'name': 'misc'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)
        directory.add_dir('[B]Backup/Restauracao[/B]', {'mode': 'maint', 'name': 'backup'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)
        directory.add_dir('[B]Ajustes/Correcoes do Sistema[/B]', {'mode': 'maint', 'name': 'tweaks'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)

    def clean_menu(self):
        from resources.libs import clear
        from resources.libs.common import tools

        on = '[B][COLOR springgreen]ON[/COLOR][/B]'
        off = '[B][COLOR red]OFF[/COLOR][/B]'

        autoclean = 'true' if CONFIG.AUTOCLEANUP == 'true' else 'false'
        cache = 'true' if CONFIG.AUTOCACHE == 'true' else 'false'
        packages = 'true' if CONFIG.AUTOPACKAGES == 'true' else 'false'
        thumbs = 'true' if CONFIG.AUTOTHUMBS == 'true' else 'false'
        includevid = 'true' if CONFIG.INCLUDEVIDEO == 'true' else 'false'
        includeall = 'true' if CONFIG.INCLUDEALL == 'true' else 'false'

        sizepack = tools.get_size(CONFIG.PACKAGES)
        sizethumb = tools.get_size(CONFIG.THUMBNAILS)
        archive = tools.get_size(CONFIG.ARCHIVE_CACHE)
        sizecache = (clear.get_cache_size()) - archive
        totalsize = sizepack + sizethumb + sizecache

        directory.add_file(
            'Limpeza Total: [COLOR springgreen][B]{0}[/B][/COLOR]'.format(tools.convert_size(totalsize)), {'mode': 'fullclean'},
            icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Limpar Cache: [COLOR springgreen][B]{0}[/B][/COLOR]'.format(tools.convert_size(sizecache)),
                           {'mode': 'clearcache'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        if xbmc.getCondVisibility('System.HasAddon(script.module.urlresolver)') or xbmc.getCondVisibility(
                'System.HasAddon(script.module.resolveurl)'):
            directory.add_file('Limpar Caches do Resolver', {'mode': 'clearfunctioncache'}, icon=CONFIG.ICONMAINT,
                               themeit=CONFIG.THEME3)
        directory.add_file('Limpar Pacotes: [COLOR springgreen][B]{0}[/B][/COLOR]'.format(tools.convert_size(sizepack)),
                           {'mode': 'clearpackages'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file(
            'Limpar Thumbnails: [COLOR springgreen][B]{0}[/B][/COLOR]'.format(tools.convert_size(sizethumb)),
            {'mode': 'clearthumb'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        if os.path.exists(CONFIG.ARCHIVE_CACHE):
            directory.add_file('Limpar Archive_Cache: [COLOR springgreen][B]{0}[/B][/COLOR]'.format(
                tools.convert_size(archive)), {'mode': 'cleararchive'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Limpar Thumbnails Antigas', {'mode': 'oldThumbs'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Limpar Logs de Crash', {'mode': 'clearcrash'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Purgar Bancos de Dados', {'mode': 'purgedb'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Reinicio Limpo', {'mode': 'freshstart'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)

        directory.add_file('Limpeza Automatica', fanart=CONFIG.ADDON_FANART, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME1)
        directory.add_file('Limpeza Automatica na Inicializacao: {0}'.format(autoclean.replace('true', on).replace('false', off)),
                           {'mode': 'togglesetting', 'name': 'autoclean'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        if autoclean == 'true':
            directory.add_file(
                '--- Frequencia da Limpeza Automatica: [B][COLOR springgreen]{0}[/COLOR][/B]'.format(
                    CONFIG.CLEANFREQ[CONFIG.AUTOFREQ]),
                {'mode': 'changefreq'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            directory.add_file(
                '--- Limpar Cache na Inicializacao: {0}'.format(cache.replace('true', on).replace('false', off)),
                {'mode': 'togglesetting', 'name': 'clearcache'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            directory.add_file(
                '--- Limpar Pacotes na Inicializacao: {0}'.format(packages.replace('true', on).replace('false', off)),
                {'mode': 'togglesetting', 'name': 'clearpackages'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            directory.add_file(
                '--- Limpar Thumbs antigas na Inicializacao: {0}'.format(thumbs.replace('true', on).replace('false', off)),
                {'mode': 'togglesetting', 'name': 'clearthumbs'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Limpar Cache de Video', fanart=CONFIG.ADDON_FANART, icon=CONFIG.ICONMAINT,
                           themeit=CONFIG.THEME1)
        directory.add_file(
            'Incluir Cache de Video ao Limpar Cache: {0}'.format(includevid.replace('true', on).replace('false', off)),
            {'mode': 'togglecache', 'name': 'includevideo'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)

        if includeall == 'true':
            includegaia = 'true'
            includeexodusredux = 'true'
            includethecrew = 'true'
            includeyoda = 'true'
            includevenom = 'true'
            includenumbers = 'true'
            includescrubs = 'true'
            includeseren = 'true'
        else:
            includeexodusredux = 'true' if CONFIG.INCLUDEEXODUSREDUX == 'true' else 'false'
            includegaia = 'true' if CONFIG.INCLUDEGAIA == 'true' else 'false'
            includethecrew = 'true' if CONFIG.INCLUDETHECREW == 'true' else 'false'
            includeyoda = 'true' if CONFIG.INCLUDEYODA == 'true' else 'false'
            includevenom = 'true' if CONFIG.INCLUDEVENOM == 'true' else 'false'
            includenumbers = 'true' if CONFIG.INCLUDENUMBERS == 'true' else 'false'
            includescrubs = 'true' if CONFIG.INCLUDESCRUBS == 'true' else 'false'
            includeseren = 'true' if CONFIG.INCLUDESEREN == 'true' else 'false'

        if includevid == 'true':
            directory.add_file(
                '--- Incluir Todos os Addons de Video: {0}'.format(includeall.replace('true', on).replace('false', off)),
                {'mode': 'togglecache', 'name': 'includeall'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.exodusredux)'):
                directory.add_file(
                    '--- Incluir Exodus Redux: {0}'.format(
                        includeexodusredux.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includeexodusredux'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.gaia)'):
                directory.add_file(
                    '--- Incluir Gaia: {0}'.format(includegaia.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includegaia'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.numbersbynumbers)'):
                directory.add_file(
                    '--- Incluir NuMb3r5: {0}'.format(includenumbers.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includenumbers'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.scrubsv2)'):
                directory.add_file(
                    '--- Incluir Scrubs v2: {0}'.format(includescrubs.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includescrubs'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.seren)'):
                directory.add_file(
                    '--- Incluir Seren: {0}'.format(includeseren.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includeseren'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.thecrew)'):
                directory.add_file(
                    '--- Incluir THE CREW: {0}'.format(includethecrew.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includethecrew'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.venom)'):
                directory.add_file(
                    '--- Incluir Venom: {0}'.format(includevenom.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includevenom'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.yoda)'):
                directory.add_file(
                    '--- Incluir Yoda: {0}'.format(includeyoda.replace('true', on).replace('false', off)),
                    {'mode': 'togglecache', 'name': 'includeyoda'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
            directory.add_file('--- Ativar Todos os Addons de Video', {'mode': 'togglecache', 'name': 'true'}, icon=CONFIG.ICONMAINT,
                               themeit=CONFIG.THEME3)
            directory.add_file('--- Desativar Todos os Addons de Video', {'mode': 'togglecache', 'name': 'false'}, icon=CONFIG.ICONMAINT,
                               themeit=CONFIG.THEME3)

    def addon_menu(self):
        directory.add_file('Remover Addons', {'mode': 'removeaddons'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_dir('Remover Dados de Addon', {'mode': 'removeaddondata'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_dir('Ativar/Desativar Addons', {'mode': 'enableaddons'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        # directory.add_file('Enable/Disable Adult Addons', 'toggleadult', icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Forcar atualizacao de todos os repositorios', {'mode': 'forceupdate'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Forcar atualizacao de todos os addons', {'mode': 'forceupdate', 'action': 'auto'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)

   
    def logging_menu(self):
        errors = int(logging.error_checking(count=True))
        errorsfound = str(errors) + ' Erro(s) Encontrado(s)' if errors > 0 else 'Nenhum Encontrado'
        wizlogsize = ': [COLOR red]Nao Encontrado[/COLOR]' if not os.path.exists(
            CONFIG.WIZLOG) else ": [COLOR springgreen]{0}[/COLOR]".format(
            tools.convert_size(os.path.getsize(CONFIG.WIZLOG)))
            
        directory.add_file('Alternar Log de Depuracao', {'mode': 'enabledebug'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Enviar Arquivo de Log', {'mode': 'uploadlog'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Ver Erros no Log: [COLOR springgreen][B]{0}[/B][/COLOR]'.format(errorsfound), {'mode': 'viewerrorlog'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        if errors > 0:
            directory.add_file('Ver Ultimo Erro no Log', {'mode': 'viewerrorlast'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Ver Arquivo de Log', {'mode': 'viewlog'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Ver Arquivo de Log do Wizard', {'mode': 'viewwizlog'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Limpar Arquivo de Log do Wizard: [COLOR springgreen][B]{0}[/B][/COLOR]'.format(wizlogsize), {'mode': 'clearwizlog'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
   
        
    def misc_menu(self):
        directory.add_file('Kodi 17 Fix', {'mode': 'kodi17fix'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_dir('Ferramentas de Rede', {'mode': 'nettools'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Alternar Fontes Desconhecidas', {'mode': 'unknownsources'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Alternar Atualizacoes de Addon', {'mode': 'toggleupdates'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Recarregar Skin', {'mode': 'forceskin'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Recarregar Perfil', {'mode': 'forceprofile'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Forcar Fechamento do Kodi', {'mode': 'forceclose'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)

    def backup_menu(self):
        directory.add_file('Limpar Pasta de Backup', {'mode': 'clearbackup'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Local do Backup: [COLOR {0}]{1}[/COLOR]'.format(CONFIG.COLOR2, CONFIG.MYBUILDS), {'mode': 'settings', 'name': 'Maintenance'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Backup]: Build', {'mode': 'backup', 'action': 'build'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Backup]: GuiFix', {'mode': 'backup', 'action': 'gui'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Backup]: Theme', {'mode': 'backup', 'action': 'theme'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Backup]: Addon Pack', {'mode': 'backup', 'action': 'addonpack'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Backup]: Addon_data', {'mode': 'backup', 'action': 'addondata'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Build Local', {'mode': 'restore', 'action': 'build'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: GuiFix Local', {'mode': 'restore', 'action': 'gui'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Tema Local', {'mode': 'restore', 'action': 'theme'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Pacote de Addon Local', {'mode': 'restore', 'action': 'addonpack'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Addon_data Local', {'mode': 'restore', 'action': 'addondata'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Build Externa', {'mode': 'restore', 'action': 'build', 'name': 'external'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: GuiFix Externa', {'mode': 'restore', 'action': 'gui', 'name': 'external'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Tema Externo', {'mode': 'restore', 'action': 'theme', 'name': 'external'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Pacote de Addon Externo', {'mode': 'restore', 'action': 'addonpack', 'name': 'external'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('[Restaurar]: Addon_data Externo', {'mode': 'restore', 'action': 'addondata', 'name': 'external'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)

    def tweaks_menu(self):
        directory.add_file('Verificar Fontes por links quebrados', {'mode': 'checksources'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Verificar Repositorios Quebrados', {'mode': 'checkrepos'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Remover nomes de arquivos nao-ASCII', {'mode': 'asciicheck'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        # directory.add_file('Toggle Passwords On Keyboard Entry', {'mode': 'togglepasswords'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_dir('Configurar advancedsettings.xml', {'mode': 'advancedsettings'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_file('Converter caminhos para special', {'mode': 'convertpath'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
        directory.add_dir('Informacoes do Sistema', {'mode': 'systeminfo'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
