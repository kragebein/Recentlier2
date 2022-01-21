import json
import os
import pickle
import sys
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Config:
    username:str = 'changeme'
    client_secret:str = 'changeme'
    client_id:str = 'changeme'
    scope = ["playlist-read-private", 
            "user-follow-read",
            "playlist-modify-private",
            "playlist-modify-public" 
            ]
    callback: str = "http://127.0.0.1:8080"
    playlist_name: str = 'Recentlier2'
    playlist_size:int = 50
    playlist_id: str = None
    output: bool = True
    verbose: bool = False


    def __init__(self) -> None:
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
                self.playlist_id = self.data['playlist']['id']
                self.output = self.data['output']['on']
                self.verbose = self.data['output']['verbose']

                return self
        else:
            self.write()
            log('Please update config.json')
            sys.exit(0)

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
                                "size": self.playlist_size,
                                "id": self.playlist_id
                                },
                            "output": {
                                "on": self.output,
                                "verbose": self.verbose
                            }

                        }, indent=2))
        log(f'Updated config.json.')

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
        data = [self.obj.Artists, self.obj.Albums, self.obj.Tracks, self.obj.playlist.playlist]
        try:
            with open('cache.db', 'wb') as handle:
                log(f'Wrote {str(len(self.obj.Artists) + len(self.obj.Albums) + len(self.obj.Tracks))} objects to cache')
                pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except KeyboardInterrupt:
            log('Currently writing data to file, cant exit now.')
        


    async def load(self, main) -> None:
        ''' unpickles and returns the data from cache'''
        data = ([], [], [], [])
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

        main.Artists = data[0]
        main.Albums = data[1]
        main.Tracks = data[2]
        main.playlist.playlist = data[3]


class ProgressBar:
    
    def __init__(self, end):
        self.end = end
        self.now = 0

    def calculate(self):
        ''' Calculates at what percentage we are'''
        self.now += 1
        return str(self.now/self.end * 100).split()[0][:4]

    def progress(self):
        print(f'\r{self.calculate()}% ', flush=True, end='')

    def done(self):
        print('\r', flush=True, end='')

class Flags:

    def __init__(self, obj):
        self.main = obj
        self.run_tracks = False
        self.update_playlist = False
        
    async def check(self, what, data):

        if what == 'artists':

            if len(data) > len(self.main.Artists):
                log(f'Artists found: {str(len(data))} (new: {str(len(data) - len(self.main.Artists))})')
                self.main.Artists = data
                self.run_tracks = True

            elif len(data) ==  len(self.main.Artists):
                log(f'Artists found: {str(len(data))}')

            elif len(data) < len(self.main.Artists):
                len(f'Artists found: {str(len(data))} (removed: {str(len(self.main.Artists) - len(data))})')
                self.main.Artists = data
                self.run_tracks = True

        elif what == 'albums':

            if len(data) > len(self.main.Albums):
                log(f'Albums found: {str(len(data))} (new: {str(len(data) - len(self.main.Albums))})')
                self.main.Albums = data
                self.run_tracks = True
                await self.main.cache.write()

            elif len(data) ==  len(self.main.Albums):
                log(f'Albums found: {str(len(data))} (Nothing to update)')
                self.run_tracks = False

            elif len(data) < len(self.main.Albums):
                len(f'Artists found: {str(len(data))} (removed: {str(len(self.main.Albums) - len(data))})')
                self.main.Albums = data
                self.run_tracks = True
                await self.main.cache.write()

        elif what == 'tracks':
            
            if len(data) > len(self.main.Tracks):
                log(f'Tracks found: {str(len(data))} (new: {str(len(data) - len(self.main.Tracks))})')
                self.main.Tracks = data
                self.update_playlist = True
                await self.main.cache.write()

            elif len(data) ==  len(self.main.Tracks):
                log(f'Tracks found: {str(len(data))}')

            elif len(data) < len(self.main.Tracks):
                len(f'Tracks found: {str(len(data))} (removed: {str(len(self.main.Tracks) - len(data))})')
                self.main.Tracks = data
                self.update_playlist = True
                await self.main.cache.write()



class RecentError(BaseException):
    pass
