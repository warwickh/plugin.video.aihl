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
import requests 
from bs4 import BeautifulSoup 
import pickle
import datetime
import os
from urllib.parse import urlparse  
import csv
import re
import json
import yaml
class AihlSession:
    def __init__(self,
                 maxSessionTimeSeconds = 60 * 30,
                 config = "config.yml",
                 **kwargs):

        self.config_filename = config
        self.email = self.load_config()["aihl_login"]["email"],
        self.password = self.load_config()["aihl_login"]["password"],
        self.loginUrl = "https://aihl.tv/auth/login/"
        urlData = urlparse(self.loginUrl)
        self.base_url = "https://aihl.tv/"
        self.maxSessionTime = maxSessionTimeSeconds
        self.forceLogin = False    
        self.sessionFile = urlData.netloc + '_session.dat'
        self.userAgent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        self.loginTestString = "Sign Out"
        self.debug = self.load_config()["debug"]
        self.login(self.forceLogin, **kwargs)

    def load_config(self):
        config = None
        with open(self.config_filename, "r") as stream:
            try:
                config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        return config
        
    def modification_date(self, filename):
        t = os.path.getmtime(filename)
        return datetime.datetime.fromtimestamp(t)

    def login(self, forceLogin = False, **kwargs):
        wasReadFromCache = False
        if self.debug:
            print('loading or generating session...')
        if os.path.exists(self.sessionFile) and not forceLogin:
            time = self.modification_date(self.sessionFile)         

            # only load if file less than x minutes old
            lastModification = (datetime.datetime.now() - time).seconds
            if lastModification < self.maxSessionTime:
                with open(self.sessionFile, "rb") as f:
                    self.session = pickle.load(f)
                    wasReadFromCache = True
                    if self.debug:
                        print("loaded session from cache (last access %ds ago) "
                              % lastModification)
        if not wasReadFromCache:
            self.session = requests.Session()
            self.session.headers.update({'user-agent' : self.userAgent,'referer': '%s?next=/'%self.loginUrl})
            print(self.session.headers)
            print(self.session.get(self.loginUrl).cookies)       
            if 'csrftoken' in self.session.cookies:
                csrftoken = self.session.cookies['csrftoken']
            else:
                csrftoken = self.session.cookies['csrf']           
            self.loginData = dict(csrfmiddlewaretoken=csrftoken, next='/', email=self.email, password=self.password)
            print(self.loginData)
            res = self.session.post(self.loginUrl, data = self.loginData, **kwargs)
            #print(res.text)

            if self.debug:
                print('created new session with login' )
            #self.saveSessionToCache()

        res = self.session.get(self.base_url)
        #print(res.text)
        if res.text.lower().find(self.loginTestString.lower()) < 0:
            raise Exception("could not log into provided site '%s'"
                            " (did not find successful login string)" % self.loginUrl)
        else:
            self.saveSessionToCache()
            
    def saveSessionToCache(self):
        with open(self.sessionFile, "wb") as f:
            pickle.dump(self.session, f)
            if self.debug:
                print('updated session cache-file %s' % self.sessionFile)

    def retrieveContent(self, url, method = "get", postData = None, **kwargs):
        if method == 'get':
            res = self.session.get(url , **kwargs)
        else:
            res = self.session.post(url , data = postData, **kwargs)
        self.saveSessionToCache()            
        return res

    def get_all_games(self):
        games_dict = {}
        res = self.retrieveContent(self.base_url)
        soup = BeautifulSoup(res.text, "html.parser") 
        all_rounds = soup.find_all("div", attrs={"class": "generic-rail"})
        for game_round in all_rounds:
            current_label = game_round.find("div", attrs={"class": "generic-rail--caption"}).find("h4").text.strip()
            round_games = game_round.find_all("div", attrs={"class": "generic-rail-item"})
            round_games_list = []
            for game in round_games:
                path = "%s%s"%(self.base_url[:-1],game.find("a")["href"])
                #video = self.get_m3u8(path)
                name = game.find("img")["alt"]
                thumb = game.find("img")["src"]
                round_games_list.append({"name": name, "thumb": thumb, "video": path, "genre": "Sport"})#,"video": video} 
            games_dict[current_label] = round_games_list
        return games_dict
        
    def get_m3u8(self, game_url):
        #res = self.retrieveContent("%s%s"%(self.base_url[:-1],game_url))
        print(game_url)
        res = self.retrieveContent(game_url)
        game_soup = BeautifulSoup(res.text, "html.parser")
        media_data = game_soup.find(lambda tag:tag.name=="script" and "jwMediaId" in tag.text)    
        media_id = re.findall(r'jwMediaId: \"([^\"]*)",', str(media_data))[0]
        media_url = "https://cdn.jwplayer.com/v2/media/%s"%media_id
        res = self.retrieveContent(media_url)  
        media_json=json.loads(res.text)
        m3u8_path = media_json["playlist"][0]["sources"][0]["file"] 
        return m3u8_path  

    def get_rounds(self):
        games_dict = self.get_all_games()
        return games_dict.keys()

    def get_games_for_round(self, round_label):
        games_dict = self.get_all_games()
        return games_dict[round_label]
        
aihl_session = AihlSession()

_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])

def get_url(**kwargs):
    return '{}?{}'.format(_URL, urlencode(kwargs))

def get_categories():
    return aihl_session.get_rounds()

def get_videos(category):
    return aihl_session.get_games_for_round(category)

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
