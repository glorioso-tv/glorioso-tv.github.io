# -*- coding: utf-8 -*-
from kodi_six import xbmc

PlayerBase = xbmc.Player if isinstance(getattr(xbmc, 'Player', None), type) else object

class MyXBMCPlayer(PlayerBase):
    def __init__(self, *args, **kwargs):
        if PlayerBase is not object:
            try:
                super(MyXBMCPlayer, self).__init__(*args, **kwargs)
            except Exception:
                pass
        self.is_active = True
        self.urlplayed = False
        self.pdialogue = None

    def onPlayBackStarted(self):
        if (self.pdialogue):
            self.pdialogue.close()
        self.urlplayed = True

    def onPlayBackEnded(self):
        self.is_active = False

    def onPlayBackStopped(self):
        self.is_active = False
