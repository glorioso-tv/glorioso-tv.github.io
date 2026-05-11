# -*- coding: utf-8 -*-
# Author: Lord Grey
# Created : 01.03.2019
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import re
import xbmcgui
import xbmcplugin
import resources.lib.helper as helper


def get_categories(url='https://www.xvideos.com'):
    '''Parses the Xvideos homepage and returns available category links.'''
    hardcoded = 'https://www.xvideos.com'
    categories = []
    soup = helper.get_soup(url)
    cat_list = soup.find('ul', id='main-cats-sub-list')
    if not cat_list:
        return categories

    for a in cat_list.find_all('a', href=True):
        href = a['href']
        title = a.text.strip()
        if not href.startswith('/'):
            continue
        if not (href.startswith('/c/') or href.startswith('/gay') or href.startswith('/shemale')):
            continue

        if href.startswith('/'):
            href = hardcoded + href

        categories.append({'title': title, 'link': href})

    return categories


def get_vids(url, category='none'):
    '''crawls a given url form xvideos.com for videos
    and returns them as a list of dicts
    if a catergory is given it will be added to the dict
    '''
    hardcoded = 'https://xvideos.com'
    video_info = []
    videos = []
    soup = helper.get_soup(url)
    videos = soup.find_all("div", class_="thumb-block")
    if not videos:
        videos = soup.find_all("article", class_="thumb-block")

    page = '1'
    pagination = soup.find("div", class_="pagination")
    if pagination:
        page_lis = pagination.find_all('li')
        if page_lis:
            last_item = page_lis[-1]
            if last_item.a and last_item.a.text.strip().lower() == "next":
                prev_item = page_lis[-2] if len(page_lis) > 1 else last_item
                page = prev_item.a.text.strip() if prev_item.a else page
            else:
                page = last_item.a.text.strip() if last_item.a else last_item.text.strip()

    for info in videos:
        inside = info.find("div", class_="thumb-inside") or info
        under = info.find("div", class_="thumb-under") or info
        title_tag = under.find("a", href=True)
        title = title_tag.get('title') if title_tag and title_tag.get('title') else title_tag.text.strip() if title_tag else 'Untitled'
        img = inside.find('img')
        if img:
            thumb = img.get('data-src') or img.get('data-lazy-src') or img.get('data-original') or img.get('src')
        else:
            thumb = None
        res_tag = inside.find(class_="video-hd-mark") or inside.find("span", class_="thumb-info")
        duration_tag = under.find("span", class_="duration")
        duration = helper.convert_duration(duration_tag.text) if duration_tag else 0

        views = None
        views_tag = under.find("span", class_="sprfluous")
        if views_tag:
            views = views_tag.next_sibling
        if not views and duration_tag:
            next_sibling = duration_tag.next_sibling
            views = next_sibling.strip() if next_sibling and isinstance(next_sibling, str) else None

        if views:
            views = views.strip()
            if views.startswith('•'):
                views = views[1:].strip()
        else:
            views = '0'

        try:
            uploader = under.find("span", class_="name").text.strip()
        except AttributeError:
            uploader = "Unknown"

        res = res_tag.text.strip() if res_tag else None

        video_info.append(
            dict([
                ('title', title),
                ('link', hardcoded + title_tag.get('href') if title_tag else url),
                ('duration', duration),
                ('thumb', thumb),
                ('res', res),
                ('views', views),
                ('uploader', uploader),
                ('category', category),
                ('page', page)
            ]))

    return video_info


def play_video(_handle, video):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    soup = helper.get_soup(video)
    m3u_link = None

    for script in soup.find_all('script'):
        text = script.string or script.text
        if not text:
            continue

        match = re.search(r"setVideoHLS\(\s*['\"]([^'\"]+)['\"]\s*\)", text)
        if match:
            m3u_link = match.group(1)
            break

    if not m3u_link:
        match = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', soup.text)
        if match:
            m3u_link = match.group(1)

    if not m3u_link:
        match = re.search(r"setVideoUrl(?:Low|High)\(\s*['\"]([^'\"]+)['\"]\s*\)", soup.text)
        if match:
            m3u_link = match.group(1)

    if not m3u_link:
        raise RuntimeError('Unable to find playable stream URL on Xvideos page')

    play_item = xbmcgui.ListItem(path=m3u_link)
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

