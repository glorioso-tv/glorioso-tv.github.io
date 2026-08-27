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
LEGACY_TEMPLATE = os.path.join(ADVANCED_DIR, 'advancedsettings_kodi18.9E20.xml')


def _profile_info(profile):
    if profile == 'kodi21':
        return KODI21_TEMPLATE, 'Kodi 21.3'
    if profile == 'legacy':
        return LEGACY_TEMPLATE, 'Kodi 18.9 e 20'
    return None, None

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
    directory.add_file('advancedsettings.xml: {0}'.format(status), icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('advancedsettings_kodi21_3.xml',
                       {'mode': 'advancedset', 'name': 'kodi21'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)
    directory.add_file('advancedsettings_kodi18.9E20.xml',
                       {'mode': 'advancedset', 'name': 'legacy'}, icon=CONFIG.ICONMAINT, themeit=CONFIG.THEME3)


def apply(profile='kodi21'):
    dialog = xbmcgui.Dialog()

    template, label = _profile_info(profile)
    overwrite = True
    if os.path.exists(ADVANCED_FILE):
        overwrite = dialog.yesno(CONFIG.ADDONTITLE,
                                 '[COLOR {0}]advancedsettings.xml ja existe. Sobrescrever com perfil {1}?[/COLOR]'.format(CONFIG.COLOR2, label),
                                 yeslabel='[B][COLOR springgreen]Sobrescrever[/COLOR][/B]',
                                 nolabel='[B][COLOR red]Cancelar[/COLOR][/B]')
    if not overwrite:
        return

    if not template:
        dialog.ok(CONFIG.ADDONTITLE, '[COLOR {0}]Perfil de advancedsettings invalido[/COLOR]'.format(CONFIG.COLOR2))
        return

    ok = _write_template(template)
    result_label = label

    if ok:
        logging.log_notify(CONFIG.ADDONTITLE, '[COLOR {0}]advancedsettings aplicado: {1}[/COLOR]'.format(CONFIG.COLOR2, result_label))
        dialog.ok(CONFIG.ADDONTITLE,
                  '[COLOR {0}]Configuracao aplicada com sucesso.[/COLOR]'.format(CONFIG.COLOR2) + '\n' +
                  '[COLOR {0}]Perfil detectado: {1}[/COLOR]'.format(CONFIG.COLOR2, result_label) + '\n' +
                  '[COLOR {0}]Reinicie o Kodi para carregar o advancedsettings.xml.[/COLOR]'.format(CONFIG.COLOR2))
    else:
        dialog.ok(CONFIG.ADDONTITLE, '[COLOR {0}]Falha ao aplicar advancedsettings.xml[/COLOR]'.format(CONFIG.COLOR2))
