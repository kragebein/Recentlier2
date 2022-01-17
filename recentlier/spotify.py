import spotipy
import sys

from spotipy import SpotifyException
from spotipy.util import prompt_for_user_token
from recentlier.tools import Config, log

global config
config = Config()

class Spotify:

    config = Config()
    token = None
    sp = None

    async def exceptionhandler(self, e: SpotifyException) -> bool:
        ''' Tries to handle exceptions '''
        if e.http_status == 401:
            # No token was provided.
            if e.msg.split('\n')[1] == ' No token provided':
                log(f'You need to update your config before running me.')
                sys.exit(0)
            if e.msg.split('\n')[1] == 'The access token expired':
                # Token expired.
                log('Access token expired.')
                del self.token
                await self.get_token()
            return True
        
        if e.http_status == 404:
            # The request ended in a 404.
            if e.msg.split('\n')[1] == ' non existing id':
                log('The request failed, and says this id doesnt exist in this context.')
                log(e.msg.split('\n')[0])
        # TODO:
        # Complete this method     
            
        print(e.http_status)
        print(e.reason)
        print(e.args)
        print(e.code)
        print(e.headers)
        print(e.msg)
        return False

    async def get_token(self) -> spotipy.client:
        ''' Retrieves a workable token '''
        token = prompt_for_user_token(
            username=config.username,
            scope=','.join(i for i in config.scope),
            client_secret=config.client_secret,
            client_id=config.client_id,
            redirect_uri=config.callback
        )
        if token:
            # Successfully retrieved token!
            self.token = token
            log('New token retrieved')
            return token
        else:
            log('Unable to retrieve token!')

            

    async def client(self) -> spotipy.Spotify:
        ''' Returns the spotify Client.'''
        if not self.token:
            await self.get_token()
        try:
            self.sp = spotipy.Spotify(auth=self.token)
        except SpotifyException as R:
            success = self.exceptionhandler(R)
            if success:
                self.client()
                return True
        return False

    async def next(self, *args, **kwargs) -> spotipy.Spotify.next:
        if not self.sp:
            await self.client()
        try:
            return self.sp.next(*args, **kwargs)
        except SpotifyException as R:
            success = await self.exceptionhandler(R)
            if success:
                self.next(*args, **kwargs)


    async def get_artists(self, *args, **kwargs) -> spotipy.Spotify.current_user_followed_artists:
        if not self.sp:
            await self.client()
        try:
            return self.sp.current_user_followed_artists(*args, **kwargs)
            
        except SpotifyException as R:
           success = await self.exceptionhandler(R)
           if success:
               self.get_artists(*args, **kwargs)


    async def artist_albums(self, *args, **kwargs) -> spotipy.Spotify.artist_albums:
        if not self.sp:
            await self.client()
        try:
            return self.sp.artist_albums(*args, **kwargs)
        except SpotifyException as R:
            success = await self.exceptionhandler(R)
            if success:
                self.artist_albums(*args, **kwargs)
    
    async def get_album(self, *args, **kwargs) -> spotipy.Spotify.album_tracks:
        if not self.sp:
            await self.client()
        try:
            return self.sp.album_tracks(*args, **kwargs)
        except SpotifyException as R:
            success = await self.exceptionhandler(R)
            if success:
                self.get_album(*args, **kwargs)

    async def get_several_albums(self, *args, **kwargs) -> spotipy.Spotify.albums:
        if not self.sp:
            await self.client()
        try:
            return self.sp.albums(*args, **kwargs)
        except SpotifyException as R:
            success = await self.exceptionhandler(R)
            if success: self.get_several_albums(*args, **kwargs)
