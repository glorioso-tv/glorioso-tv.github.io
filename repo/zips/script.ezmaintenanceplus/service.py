import xbmc, xbmcaddon, xbmcgui, xbmcplugin, os, sys, xbmcvfs, glob
import shutil
import urllib
import re
import time
from resources.lib.modules.backtothefuture import PY2
from resources.lib.modules import maintenance

# Code to map the old translatePath
if PY2:
    translatePath = xbmc.translatePath
    loglevel = xbmc.LOGNOTICE
else:
    translatePath = xbmcvfs.translatePath
    loglevel = xbmc.LOGINFO

AddonID ='script.ezmaintenanceplus'
packagesdir    =  translatePath(os.path.join('special://home/addons/packages',''))
thumbnails    =  translatePath('special://home/userdata/Thumbnails')
dialog = xbmcgui.Dialog()
setting = xbmcaddon.Addon().getSetting
iconpath = translatePath(os.path.join('special://home/addons/' + AddonID,'icon.png'))
# if setting('autoclean') == 'true':
    # control.clearCache()

def run_startup_maintenance():
    """Wait for Kodi and clean disposable data once per start."""
    if setting('startup.cache') != 'true':
        return
    if monitor.waitForAbort(30):
        return
    maintenance.clearCache(mode='silent')
    if setting('startup.packages') == 'true':
        maintenance.purgePackages(mode='silent')
    if setting('startup.thumbnails') == 'true':
        maintenance.deleteThumbnails(mode='silent')
    if setting('notify_mode') == 'true':
        xbmc.executebuiltin('Notification(%s, %s, %s, %s)' % ('Manutenção', 'Limpeza automática concluída', '3000', iconpath))

class Monitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)
        maintenance.logMaintenance("Monitor init")
        maintenance.determineNextMaintenance()

    def onSettingsChanged(self):
        maintenance.logMaintenance("onSettingsChanged")
        maintenance.determineNextMaintenance()

if __name__ == '__main__':

    monitor = Monitor()
    run_startup_maintenance()

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(10):
            # Abort was requested while waiting. We should exit
            break
        maintenance.logMaintenance("monitor loop")
        if not xbmc.Player().isPlayingVideo():
            nextMaintenance = maintenance.getNextMaintenance()
            maintenance.logMaintenance("time.time() = %s, nextMaintenance = %s" % (str(time.time()), str(nextMaintenance)))
            if nextMaintenance > 0 and time.time() >= nextMaintenance:
                xbmc.log("ezmaintenanceplus: AutoClean started", level=loglevel)
                maintenance.clearCache()
                if setting('startup.packages') == 'true':
                    maintenance.purgePackages(mode='silent')
                if setting('startup.thumbnails') == 'true':
                    maintenance.deleteThumbnails(mode='silent')
                xbmc.log("ezmaintenanceplus: AutoClean done", level=loglevel)
                maintenance.determineNextMaintenance()
                #xbmc.executebuiltin('Notification(%s, %s, %s, %s)' % ('Maintenance' , 'Clean Completed' , '3000', iconpath))

    del monitor

