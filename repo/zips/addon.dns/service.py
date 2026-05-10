# -*- coding: utf-8 -*-
from proxyhttp import LISTEN_HOST, LISTEN_PORT, server
from set_proxy import set_kodi_proxy

set_kodi_proxy(LISTEN_HOST, LISTEN_PORT)
server()