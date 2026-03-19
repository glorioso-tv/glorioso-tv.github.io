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

import os

import xbmc
import xbmcgui
import xbmcvfs

from resources.libs.common import directory
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs.common.config import CONFIG


ADVANCED_DIR = os.path.join(CONFIG.PLUGIN, 'resources', 'advancedsettings')
ADVANCED_FILE = os.path.join(CONFIG.USERDATA, 'advancedsettings.xml')
KODI21_TEMPLATE = os.path.join(ADVANCED_DIR, 'advancedsettings_kodi21_3.xml')
LEGACY_TEMPLATE = os.path.join(ADVANCED_DIR, 'advancedsettings_kodi20_or_older.xml')


def _safe_ram_mb():
    try:
        return int(CONFIG.RAM)
    except Exception:
        return 2048


def _device_tier():
    ram_mb = _safe_ram_mb()
    is_android = xbmc.getCondVisibility('System.Platform.Android')
    is_windows = xbmc.getCondVisibility('System.Platform.Windows')
    is_linux = xbmc.getCondVisibility('System.Platform.Linux')
    is_osx = xbmc.getCondVisibility('System.Platform.OSX')

    # Heuristica pragmatica para diferenciar TV Box fraca vs hardware forte.
    if is_android and ram_mb <= 3072:
        return 'fraco'
    if ram_mb <= 2048:
        return 'fraco'
    if ram_mb <= 4096:
        return 'medio'
    if is_windows or is_linux or is_osx:
        return 'forte'
    return 'medio'


def _network_values(tier):
    if tier == 'fraco':
        return {
            'curlclienttimeout': 20,
            'curllowspeedtime': 30,
            'curlretries': 2,
            'disablehttp2': 'true',
            'disableipv6': 'true'
        }
    if tier == 'forte':
        return {
            'curlclienttimeout': 15,
            'curllowspeedtime': 15,
            'curlretries': 2,
            'disablehttp2': 'false',
            'disableipv6': 'false'
        }
    return {
        'curlclienttimeout': 20,
        'curllowspeedtime': 20,
        'curlretries': 2,
        'disablehttp2': 'false',
        'disableipv6': 'false'
    }


def _legacy_cache_values(tier):
    if tier == 'fraco':
        return {'memorysize': 104857600, 'readfactor': 4.0}
    if tier == 'forte':
        return {'memorysize': 262144000, 'readfactor': 8.0}
    return {'memorysize': 157286400, 'readfactor': 6.0}


def _build_best_content():
    tier = _device_tier()
    network = _network_values(tier)

    lines = ['<advancedsettings>']
    if CONFIG.KODIV < 21:
        cache = _legacy_cache_values(tier)
        lines.extend([
            '    <cache>',
            '        <buffermode>1</buffermode>',
            '        <memorysize>{0}</memorysize>'.format(cache['memorysize']),
            '        <readfactor>{0}</readfactor>'.format(cache['readfactor']),
            '    </cache>',
            ''
        ])
    lines.extend([
        '    <network>',
        '        <curlclienttimeout>{0}</curlclienttimeout>'.format(network['curlclienttimeout']),
        '        <curllowspeedtime>{0}</curllowspeedtime>'.format(network['curllowspeedtime']),
        '        <curlretries>{0}</curlretries>'.format(network['curlretries']),
        '        <disablehttp2>{0}</disablehttp2>'.format(network['disablehttp2']),
        '        <disableipv6>{0}</disableipv6>'.format(network['disableipv6']),
        '    </network>',
        '</advancedsettings>'
    ])
    return '\n'.join(lines) + '\n', tier


def _profile_info(profile):
    if profile == 'kodi21':
        return KODI21_TEMPLATE, 'Kodi 21.3+'
    if profile == 'legacy':
        return LEGACY_TEMPLATE, 'Kodi 20 ou anterior'
    return None, 'Automatico Inteligente'


def _write_template(src):
    if not os.path.exists(src):
        xbmcgui.Dialog().ok(CONFIG.ADDONTITLE, 'Template nao encontrado:' + '\n' + src)
        return False

    copied = xbmcvfs.copy(src, ADVANCED_FILE)
    if copied:
        return True

    try:
        tools.write_to_file(ADVANCED_FILE, tools.read_from_file(src))
        return True
    except Exception as e:
        logging.log('[AdvancedSettings] Falha ao escrever arquivo: {0}'.format(e))
        return False


def menu():
    exists = os.path.exists(ADVANCED_FILE)
    status = '[COLOR springgreen]Instalado[/COLOR]' if exists else '[COLOR red]Nao instalado[/COLOR]'
    tier = _device_tier()
    tier_label = tier.capitalize()
    directory.add_file('advancedsettings.xml: {0}'.format(status), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('Gerar Melhor Automatico ({0})'.format(tier_label),
                       {'mode': 'advancedset', 'name': 'auto'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('Configurar para Kodi 21.3+',
                       {'mode': 'advancedset', 'name': 'kodi21'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('Configurar para Kodi 20 ou anterior',
                       {'mode': 'advancedset', 'name': 'legacy'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('Remover advancedsettings.xml',
                       {'mode': 'advancedset', 'name': 'remove'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)


def apply(profile='auto'):
    dialog = xbmcgui.Dialog()

    if profile == 'remove':
        if not os.path.exists(ADVANCED_FILE):
            logging.log_notify(CONFIG.ADDONTITLE, '[COLOR {0}]advancedsettings.xml nao existe[/COLOR]'.format(CONFIG.COLOR2))
            return

        if dialog.yesno(CONFIG.ADDONTITLE,
                        '[COLOR {0}]Deseja remover o advancedsettings.xml atual?[/COLOR]'.format(CONFIG.COLOR2),
                        yeslabel='[B][COLOR springgreen]Remover[/COLOR][/B]',
                        nolabel='[B][COLOR red]Cancelar[/COLOR][/B]'):
            tools.remove_file(ADVANCED_FILE)
            logging.log_notify(CONFIG.ADDONTITLE, '[COLOR {0}]advancedsettings.xml removido[/COLOR]'.format(CONFIG.COLOR2))
        return

    template, label = _profile_info(profile)
    overwrite = True
    if os.path.exists(ADVANCED_FILE):
        overwrite = dialog.yesno(CONFIG.ADDONTITLE,
                                 '[COLOR {0}]advancedsettings.xml ja existe. Sobrescrever com perfil {1}?[/COLOR]'.format(CONFIG.COLOR2, label),
                                 yeslabel='[B][COLOR springgreen]Sobrescrever[/COLOR][/B]',
                                 nolabel='[B][COLOR red]Cancelar[/COLOR][/B]')
    if not overwrite:
        return

    if template:
        ok = _write_template(template)
        result_label = label
    else:
        content, tier = _build_best_content()
        try:
            tools.write_to_file(ADVANCED_FILE, content)
            ok = True
            result_label = 'Automatico Inteligente ({0})'.format(tier)
        except Exception as e:
            logging.log('[AdvancedSettings] Falha ao gerar arquivo: {0}'.format(e))
            ok = False
            result_label = label

    if ok:
        logging.log_notify(CONFIG.ADDONTITLE, '[COLOR {0}]advancedsettings aplicado: {1}[/COLOR]'.format(CONFIG.COLOR2, result_label))
        dialog.ok(CONFIG.ADDONTITLE,
                  '[COLOR {0}]Configuracao aplicada com sucesso.[/COLOR]'.format(CONFIG.COLOR2) + '\n' +
                  '[COLOR {0}]Perfil detectado: {1}[/COLOR]'.format(CONFIG.COLOR2, result_label) + '\n' +
                  '[COLOR {0}]Reinicie o Kodi para carregar o advancedsettings.xml.[/COLOR]'.format(CONFIG.COLOR2))
    else:
        dialog.ok(CONFIG.ADDONTITLE, '[COLOR {0}]Falha ao aplicar advancedsettings.xml[/COLOR]'.format(CONFIG.COLOR2))
