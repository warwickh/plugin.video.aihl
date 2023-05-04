# Module: main
# Author: warwickh
# Created on: 03.05.2023
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
"""
AIHL.TV video plugin that is compatible with Kodi 19.x "Matrix" and above
"""
import sys
from urllib.parse import urlencode, parse_qsl
import xbmcgui
import xbmcplugin
import os
import xbmcaddon
import xbmcvfs

connection = None

addon = xbmcaddon.Addon('plugin.video.aihl')

_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])

sys.path.append(xbmcvfs.translatePath(os.path.join(addon.getAddonInfo("path"), "lib")))
profile_dir = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
if not os.path.exists(profile_dir):
    os.mkdir(profile_dir)

from aihlsession import aihlsession

def popup(text, time=5000, image=None):
    title = addon.getAddonInfo('name')
    icon = addon.getAddonInfo('icon')
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (title, text, time, icon))

def get_connection():
    global connection
    if connection==None:
        connected = False
        email=addon.getSetting('email') 
        password=addon.getSetting('password')
        debug = True#addon.getSetting('debug')
        try:
            connection = aihlsession.AihlSession(
                email=email,
                password=password,
                debug = debug,
            )
            connected = connection.check_connected()
        except:
            pass
        if connected==False:
            popup('Connection error')
            return False
    
    return connection
    
def get_url(**kwargs):
    return '{}?{}'.format(_URL, urlencode(kwargs))

def get_categories():
    connection = get_connection()
    if connection==False:
        return []
    return connection.get_rounds()

def get_videos(category):
    connection = get_connection()
    if connection==False:
        return []
    return connection.get_games_for_round(category)

def list_categories():
    xbmcplugin.setPluginCategory(_HANDLE, 'My Video Collection')
    xbmcplugin.setContent(_HANDLE, 'videos')
    categories = get_categories()
    for category in categories:
        list_item = xbmcgui.ListItem(label=category)
        list_item.setArt({'thumb': 'icon.png'})
        list_item.setInfo('video', {'title': category,
                                    'genre': category,
                                    'mediatype': 'video'})
        url = get_url(action='listing', category=category)
        is_folder = True
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(_HANDLE)

def list_videos(category):
    xbmcplugin.setPluginCategory(_HANDLE, category)
    xbmcplugin.setContent(_HANDLE, 'videos')
    videos = get_videos(category)
    for video in videos:
        list_item = xbmcgui.ListItem(label=video['name'])
        list_item.setInfo('video', {'title': video['name'],
                                    'genre': video['genre'],
                                    'mediatype': 'video'})
        list_item.setArt({'thumb': video['thumb'], 'icon': video['thumb'], 'fanart': video['thumb']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play', video=video['video'])
        is_folder = False
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(_HANDLE)

def play_video(path):
    m3u8_path = aihl_session.get_m3u8(path)
    play_item = xbmcgui.ListItem(path=m3u8_path)
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            list_videos(params['category'])
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        list_categories()

if __name__ == '__main__':
    router(sys.argv[2][1:])
