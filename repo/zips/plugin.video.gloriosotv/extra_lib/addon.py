# -*- coding: utf-8 -*-
try:
    from .helper import *
    from . import hlsretry, tsdownloader, server
except ImportError:
    from helper import *
    import hlsretry
    import tsdownloader
    import server
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
        name = 'GLORIOSO TV - HLSRETRY - ' + name
    else:
        name = 'GLORIOSO TV - HLSRETRY'
    url = unquote_plus(url)
    url = convert_to_m3u8(url)
    url = 'http://%s:%s/?url=%s'%(str(hlsretry.HOST_NAME),str(hlsretry.PORT_NUMBER),quote(url))
    hlsretry.XtreamProxy().start()
    li=xbmcgui.ListItem(name)
    iconimage = iconimage if iconimage else ''
    li.setArt({"icon": "DefaultVideo.png", "thumb": iconimage})
    set_video_info(li, title=name, plot=description)
    xbmc.Player().play(item=url, listitem=li)

def player_tsdownloader(name,url,iconimage,description):
    if name:
        name = 'GLORIOSO TV - TSDOWNLOADER - ' + name
    else:
        name = 'GLORIOSO TV - TSDOWNLOADER'
    url = unquote_plus(url)
    url = url.replace('live/', '').replace('.m3u8', '')
    url = 'http://%s:%s/?url=%s'%(str(tsdownloader.HOST_NAME),str(tsdownloader.PORT_NUMBER),quote(url))
    tsdownloader.XtreamProxy().start() 
    li=xbmcgui.ListItem(name)
    iconimage = iconimage if iconimage else ''
    li.setArt({"icon": "DefaultVideo.png", "thumb": iconimage})
    set_video_info(li, title=name, plot=description)
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
        name = 'GLORIOSO TV'
    name = name + ' - Proxy 2'
    try:
        liz = xbmcgui.ListItem(name)
        liz.setPath(url_to_play)
        if iconImage:
            liz.setArt({"icon": iconImage, "thumb": iconImage})
        else:
            liz.setArt({"icon": addonIcon, "thumb": addonIcon})
        set_video_info(liz, title=name)
        if not supports_infotag():
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
    name = params.get('name', 'GLORIOSO TV')
    url = params.get('url', '')
    description = params.get('description', '')
    if not url:
        dialog('GLORIOSO TV PLAYER')
        return

    stream_type = (stream_type or '').upper()
    if stream_type == 'HLSRETRY':
        player_hlsretry(name, url, iconimage, description)
        return
    if stream_type == 'TSDOWNLOADER':
        player_tsdownloader(name, url, iconimage, description)
        return
    if stream_type in ('SERVER2', 'SERVER_2', 'PROXY2'):
        proxy2_player(url, name, iconimage)
        return

    op = select('SELECT PLAYER', ['PROXY - HLSRETRY', 'PROXY - TSDOWNLOADER', 'PROXY - SERVER 2'])
    if op == 0:
        player_hlsretry(name, url, iconimage, description)
    elif op == 1:
        player_tsdownloader(name, url, iconimage, description)
    elif op == 2:
        proxy2_player(url, name, iconimage)
                
