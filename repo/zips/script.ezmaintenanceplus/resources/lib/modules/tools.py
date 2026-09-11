"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs,os,sys
import urllib
import re
import time
import zipfile
from math import trunc
from resources.lib.modules import control
from datetime import datetime
from resources.lib.modules.backtothefuture import unicode, PY2

if PY2:
    FancyURLopener = urllib.FancyURLopener
    translatePath = xbmc.translatePath
else:
    FancyURLopener = urllib.request.FancyURLopener
    translatePath = xbmcvfs.translatePath

dp           = xbmcgui.DialogProgress()
dialog       = xbmcgui.Dialog()
addonInfo    = xbmcaddon.Addon().getAddonInfo

AddonTitle="EZ Maintenance+"
AddonID ='script.ezmaintenanceplus'


def xml_data_advSettings():
    """Return the network settings supported by Kodi 21.x."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<advancedsettings version="1.0">
    <network>
        <curlclienttimeout>15</curlclienttimeout>
        <curllowspeedtime>20</curllowspeedtime>
        <curlretries>5</curlretries>
        <disablehttp2>true</disablehttp2>
        <disableipv6>false</disableipv6>
    </network>
</advancedsettings>"""

def advancedSettings():
    XML_FILE   =  translatePath(os.path.join('special://home/userdata' , 'advancedsettings.xml'))
    MEM        =  xbmc.getInfoLabel("System.Memory(total)")
    FREEMEM    =  xbmc.getInfoLabel("System.FreeMemory")
    BUFFER_F   = re.sub('[^0-9]','',FREEMEM) or '0'
    BUFFER_F   = int(BUFFER_F) / 3
    BUFFERSIZE = trunc(BUFFER_F * 1024 * 1024)

    choice = dialog.yesno(AddonTitle, 'O arquivo advancedsettings.xml será substituído por opções compatíveis com o Kodi 21.3.\n\nO tamanho do buffer agora é configurado na interface do Kodi.', yeslabel='Aplicar', nolabel='Cancelar')
    if choice == 1:
        with open(XML_FILE, "w") as f:
            f.write(xml_data_advSettings())
            dialog.ok(AddonTitle, 'Configurações aplicadas. Reinicie o Kodi para carregar o arquivo.')

    elif choice == 0:
        return


def open_Settings():
    open_Settings = xbmcaddon.Addon(id=AddonID).openSettings()

def _get_keyboard( default="", heading="", hidden=False, cancel="" ):
    """ shows a keyboard and returns a value """
    if cancel == "":
        cancel=default
    keyboard = xbmc.Keyboard( default, heading, hidden )
    keyboard.doModal()
    if ( keyboard.isConfirmed() ):
        return unicode( keyboard.getText())
    return cancel


##############################    END    #########################################