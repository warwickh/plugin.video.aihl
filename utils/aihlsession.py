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

    def get_all_games(self, soup):
        all_games = soup.find_all("div", attrs={"class": "generic-rail-item"})
        return all_games

    def process_media(self, media_url):
        print("Getting %s"%media_url)
        res = self.retrieveContent(media_url)
        print(res)
        #print(res.text)    
        media_json=json.loads(res.text)
        m3u8_file = media_json["playlist"][0]["sources"][0]["file"]
        title = media_json["playlist"][0]["description"]
        filename = "strm/%s.strm"%title.replace(" ","_")
        with open(filename, "w") as f:
            f.write(m3u8_file)
            f.close()

    def process_game_page(self, game_url):
        res = self.retrieveContent("%s%s"%(self.base_url[:-1],game_url))
        game_soup = BeautifulSoup(res.text, "html.parser")
        media_data = game_soup.find(lambda tag:tag.name=="script" and "jwMediaId" in tag.text)    
        media_id = re.findall(r'jwMediaId: \"([^\"]*)",', str(media_data))[0]
        media_url = "https://cdn.jwplayer.com/v2/media/%s"%media_id
        self.process_media(media_url)

    def process_all_games(self):
        res = self.retrieveContent(self.base_url)
        #with open("main_page.txt", "w") as f:
        #    f.write(res.text)
        #    f.close()
        soup = BeautifulSoup(res.text, "html.parser")    
        all_games = self.get_all_games(soup)
        #print(all_games)
        for game in all_games:
            path = game.find("a")["href"]
            name = game.find("img")["alt"]
            #print("%s %s"%(name, path))
            filename = "%s.txt"%name.replace(" ","_")
            with open(filename, "w") as f:
                f.write(res.text)
                f.close()
            self.process_game_page(path)
        
def main():
    s = AihlSession()
    s.process_all_games()

if __name__ == "__main__":
    main()