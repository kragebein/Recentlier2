import json
import os
import pickle
import asyncio

from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class Config:
    read:bool = False
    username:str = 'changeme'
    client_secret:str = 'changeme'
    client_id:str = 'changeme'
    scope: str = [
            "playlist-read-private",
            "user-follow-read",
            "playlist-modify-private"
            ],
    callback: str = "http://127.0.0.1:8080"
    playlist_name: str = 'Recentlier2'
    playlist_size:int = 50
    output: bool = True
    verbose: bool = False


    def __init__(self) -> None:
        if not self.read:
            ''' Initialize the table if not already initialized'''
            self.load()


    def load(self) -> dataclass:
        ''' Loads the config into class, and returns the class'''
        if os.path.exists('config.json'):
            with open('config.json', 'r') as configfile:
                self.data = json.loads(configfile.read())
                self.username = self.data['username']
                self.client_secret = self.data['spotify']['client_secret']
                self.client_id = self.data['spotify']['client_id']
                self.scope = self.data['spotify']['scope']
                self.callback = self.data['spotify']['callback']
                self.playlist_name = self.data['playlist']['name']
                self.playlist_size = self.data['playlist']['size']
                self.output = self.data['output']['on']
                self.verbose = self.data['output']['verbose']

                return self
        else:
            self.write()

    def write(self) -> None:
        ''' Dumps the current config to config.json '''
        with open('config.json', 'w') as configfile:
            configfile.write(json.dumps({
                            "username": self.username,

                            "spotify": {
                                "_comment": "Spotify Credentials",
                                "client_id": self.client_id,
                                "client_secret": self.client_secret,
                                "scope": self.scope,
                                "callback": self.callback
                                },
                            "playlist": {
                                "_comment": "Playlist Information",
                                "name": self.playlist_name,
                                "size": self.playlist_size
                                },
                            "output": {
                                "on": self.output,
                                "verbose": self.verbose
                            }

                        }))

def log(n):
    ''' Print while logging'''
    now = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    now = f'[{now}] '
    print(now + str(n))
    with open('recentlier.log', 'a') as log:
        log.write(now+str(n)+'\n') 


class Cache:

    def __init__(self, obj):

        self.obj = obj
        
    async def write(self) -> None:
        ''' pickles and dumps the data '''
        data = [self.obj.Artists, self.obj.Albums, self.obj.Tracks]
        try:
            with open('cache.db', 'wb') as handle:
                log(f'Wrote {str(len(self.obj.Artists) + len(self.obj.Albums) + len(self.obj.Tracks))} objects to cache')
                pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except KeyboardInterrupt:
            log('Currently writing data to file, cant exit now.')
        


    async def load(self) -> list:
        ''' unpickles and returns the data from cache'''
        data = ([], [], [])
        if os.path.exists('cache.db'):
            try:
                with open('cache.db', 'rb') as handle:
                    data = pickle.load(handle)
                if len(data[0]) > 0 and len(data[1]) > 0 and len(data[2]) > 0:
                    log('Cache loaded successfully.')
                else:
                    log(f'Cache partially loaded, found {str(len(data[0]) + len(data[1]) + len(data[2]))} objects')
            except Exception as R:
                log(f'Couldnt load data from Cache -> Error {R}')
        else:
            log('Unable to load cache. (no cache found)')

        return [data[0], data[1], data[2]]


class ProgressBar:
    
    def __init__(self, end, progress):
        self.end = end
        self.now = progress.progress

    def calculate(self, place):
        ''' Calculates at what percentage we are'''
        return str(self.now/self.end * 100).split()[0][:4]

    def progress(self, place):
        print(f'\rCurrent job is at {self.calculate(place)}%', flush=True, end='')

    def done(self):
        print('\n')

class RecentError(BaseException):
    pass
