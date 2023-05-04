#!/usr/bin/env python3
"""

"""
import requests 
from bs4 import BeautifulSoup 
import pickle
import datetime
import os
from urllib.parse import urlparse  
import csv
import re
import json

class AihlSession:
    def __init__(self,
                 email=None,
                 password=None,
                 maxSessionTimeSeconds = 60 * 30,
                 agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
                 debug = False):
        self.email = email
        self.password = password
        self.loginUrl = "https://aihl.tv/auth/login/"
        urlData = urlparse(self.loginUrl)
        self.base_url = "https://aihl.tv/"
        self.maxSessionTime = maxSessionTimeSeconds  
        self.sessionFile = urlData.netloc + '_session.dat'
        self.userAgent = agent
        self.loginTestString = "Sign Out"
        self.debug = debug
        self.connected = False
        print("Email: %s"%email)
        print("Password: %s"%password)
        if email is None or password is None or email is "" or password is "":
            raise CredentialError('You must specify either a username/password '
                'combination or "useNetrc" must be either True or a string '
                'representing a path to a netrc file')
        self.login()
     
    def modification_date(self, filename):
        t = os.path.getmtime(filename)
        return datetime.datetime.fromtimestamp(t)

    def login(self, forceLogin = False):
        wasReadFromCache = False
        if self.debug:
            print('loading or generating session...')
        if os.path.exists(self.sessionFile):
            time = self.modification_date(self.sessionFile)         
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
            res = self.session.post(self.loginUrl, data = self.loginData)
            #print(res.text)

            if self.debug:
                print('created new session with login' )
            #self.saveSessionToCache()

        res = self.session.get(self.base_url)
        #print(res.text)
        if res.text.lower().find(self.loginTestString.lower()) < 0:
            self.connected = False
            raise Exception("could not log into provided site '%s'"
                            " (did not find successful login string)" % self.loginUrl)
        else:
            self.connected = True
            self.saveSessionToCache()
    
    def check_connected(self):
        return self.connected
    
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

"""        
def main():
    s = AihlSession()
    print(s.get_rounds())
    print(s.get_all_games())
    print(s.get_games_for_round('Round 3 Replays'))
    print(s.get_m3u8('https://aihl.tv/ice-hockey/aihl/round-3/28-april-rd-3-mustangs-v-ice/'))

if __name__ == "__main__":
    main()
"""
