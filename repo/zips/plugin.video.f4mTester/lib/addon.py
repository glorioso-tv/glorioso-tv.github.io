# -*- coding: utf-8 -*-
from lib.helper import *
from lib import hlsretry, tsdownloader, server
import threading
import time


def m3u8_to_ts(url):
    if '.m3u8' in url and '/live/' in url and int(url.count("/")) > 5:
        url = url.replace('/live', '').replace('.m3u8', '')
    return url


def basename(p):
    """Returns the final component of a pathname"""
    i = p.rfind('/') + 1
    return p[i:]
    
def convert_to_m3u8(url):
    if '|' in url:
        url = url.split('|')[0]
    elif '%7C' in url:
        url = url.split('%7C')[0]
    
    if not '.m3u8' in url and not '/hl' in url and int(url.count("/")) > 4 and not '.mp4' in url and not '.avi' in url:
        parsed_url = urlparse(url)
        try:
            # Captura o esquema (http) e o host (domínio:porta) automaticamente
            host_part1 = '%s://%s'%(parsed_url.scheme, parsed_url.netloc)
            host_part2 = url.split(host_part1)[1]
            
            # Se a URL não tiver /live (padrão Xtream), nós adicionamos
            # Se já tiver, mantemos a estrutura original
            if not '/live' in host_part2:
                url = host_part1 + '/live' + host_part2
            else:
                url = host_part1 + host_part2
                
            file = basename(url)
            if '.ts' in file:
                file_new = file.replace('.ts', '.m3u8')
                url = url.replace(file, file_new)
            else:
                # Adiciona o .m3u8 no final para que o HLSRETRY funcione
                url = url + '.m3u8'
        except:
            pass
    return url 

def player_hlsretry(name,url,iconimage,description):
    if name:
        name = 'F4MTESTER - HLSRETRY - ' + name
    else:
        name = 'F4MTESTER - HLSRETRY'
    url = unquote_plus(url)
    url = convert_to_m3u8(url)
    url = 'http://%s:%s/?url=%s'%(str(hlsretry.HOST_NAME),str(hlsretry.PORT_NUMBER),quote(url))
    hlsretry.XtreamProxy().start()
    li=xbmcgui.ListItem(name)
    iconimage = iconimage if iconimage else ''
    li.setArt({"icon": "DefaultVideo.png", "thumb": iconimage})
    if kversion > 19:
        info = li.getVideoInfoTag()
        info.setTitle(name)
        info.setPlot(description)
    else:
        li.setInfo(type="Video", infoLabels={"Title": name, "Plot": description})
    xbmc.Player().play(item=url, listitem=li)

def player_tsdownloader(name,url,iconimage,description):
    if name:
        name = 'F4MTESTER - TSDOWNLOADER - ' + name
    else:
        name = 'F4MTESTER - TSDOWNLOADER'
    url = unquote_plus(url)
    url = url.replace('live/', '').replace('.m3u8', '')
    url = 'http://%s:%s/?url=%s'%(str(tsdownloader.HOST_NAME),str(tsdownloader.PORT_NUMBER),quote(url))
    tsdownloader.XtreamProxy().start() 
    li=xbmcgui.ListItem(name)
    iconimage = iconimage if iconimage else ''
    li.setArt({"icon": "DefaultVideo.png", "thumb": iconimage})
    if kversion > 19:
        info = li.getVideoInfoTag()
        info.setTitle(name)
        info.setPlot(description)
    else:
        li.setInfo(type="Video", infoLabels={"Title": name, "Plot": description})
    xbmc.Player().play(item=url, listitem=li)           

class MyPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

def monitor():
    while xbmc.Player().isPlaying():
        time.sleep(1)
    server.req_shutdown()

def proxy2_thread(name,iconImage,url_to_play):
    if not name:
        name = 'F4mTester'
    name = name + ' - Proxy 2'
    try:
        liz = xbmcgui.ListItem(name)
        liz.setPath(url_to_play)
        if iconImage:
            liz.setArt({"icon": iconImage, "thumb": iconImage})
        else:
            liz.setArt({"icon": addonIcon, "thumb": addonIcon})
        if kversion > 19:
            info = liz.getVideoInfoTag()
            info.setTitle(name)
        else:                  
            liz.setInfo(type='video', infoLabels={'Title': name})
            liz.setMimeType("application/vnd.apple.mpegurl")
        liz.setContentLookup(False) 
        mplayer = MyPlayer()
        mplayer.play(url_to_play,liz)
    except:
        pass

def proxy2_player(url,name,iconImage):
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    url_to_play = server.prepare_url(url)
    infoDialog('ABRINDO PROXY...',iconimage='INFO', time=6000)
    server.mediaserver().start()
    t1 = threading.Thread(target=proxy2_thread, args=(name,iconImage,url_to_play))
    t1.start()
    count = 0
    while not xbmc.Player().isPlaying():
        count += 1
        time.sleep(1)
        if count == 12:
            break
    t2 = threading.Thread(target=monitor)
    t2.daemon = True
    t2.start()


#### run addon ####
def run(params):
    stream_type = params.get('streamtype', None)
    iconimage = params.get('iconImage', params.get('thumbnailImage', addonIcon))
    name = params.get('name', 'F4mTester')
    url = params.get('url', '')
    description = params.get('description', '')
    if not stream_type:
        dialog('F4MTESTER PLAYER')
    elif stream_type !=None:
        if url:
            op = select('SELECT PLAYER', ['PROXY - HLSRETRY', 'PROXY - TSDOWNLOADER', 'PROXY - SERVER 2'])
            if op == 0:
                player_hlsretry(name,url,iconimage,description)
            elif op == 1:
                player_tsdownloader(name,url,iconimage,description)
            elif op == 2:
                proxy2_player(url,name,iconimage)
                
