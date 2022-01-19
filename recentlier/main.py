#!/usr/bin/python3.10
import operator
import asyncio

from typing import Any, List
from recentlier.spotify import Spotify
from recentlier.tools import log, Cache, ProgressBar, Flags
from recentlier.classes import Artist, Playlist, Track, Album


class Recentlier:

    spot = Spotify()
    albumbuffer:list = []
    tracks:list = []

    def __init__(self):

        self.Artists:list = []
        self.Albums:list = []
        self.Tracks:list = []
        self.playlist = Playlists(self)
        self.cache = Cache(self)
    
    async def run(self):
        # Preload from cache (if any)
        while True:
            await self.cache.load(self)
            flags = Flags(self)

            artists = await self.populate_artists()
            await flags.check('artists', artists)

            albums = await self.populate_albums(artists)
            await flags.check('albums', albums)
            
            if flags.run_tracks:
                tracks = await self.populate_tracks(self.Albums)
                await flags.check('tracks', tracks)

            if flags.update_playlist:
                await self.playlist.update()
                await self.cache.write()

            log(f'Sleeping for 6 hours.')
            await asyncio.sleep(21600)

    async def populate_artists(self) -> List[Artist]:
        ''' Creates a list of Artist-dataclasses. '''
        Artists = []
        spotify = self.spot
        
        results = await spotify.get_artists(limit=50)
        for artist in results['artists']['items']:
            Artists.append(Artist(id=artist['id'], name=artist['name']))
        
        while 'next' in results['artists'] and results['artists']['next'] is not None:
            results = await spotify.next(results['artists'])

            for artist in results['artists']['items']:
                Artists.append(
                    Artist(
                        id=artist['id'],
                        name=artist['name']
                        ) )
        return Artists

    async def populate_albums(self, artists: Artist) -> List[Album]:
        ''' creates a list of Album-databalasses'''
        progressbar = ProgressBar(len(self.Artists))
        Albums = []
        spotify = self.spot
        for artist in artists:
            results = await spotify.artist_albums(artist.id, limit=50)

            for album in results['items']:
                Albums.append(
                    Album(
                        id=album['id'],
                        release_date=album['release_date'],
                        name=album['name'],
                        artist_name=artist.name,
                        artist_id=artist.id
                        ) )

            while 'next' in results and results['next'] is not None:
                results = await spotify.next(results)

                for album in results['items']:
                    Albums.append(
                        Album(
                            id=album['id'],
                            release_date=album['release_date'],
                            name=album['name'],
                            artist_name=artist.name,
                            artist_id=artist.id

                            ) )
            progressbar.progress()
        progressbar.done()
        return Albums

    async def add_to_buffer(self, input: str) -> Any:
        ''' Return only when buffer is full'''

        if len(self.albumbuffer) + 1 == 20:
            self.albumbuffer.append(input)
            data = self.albumbuffer
            self.albumbuffer = []

            return data
        else:
            self.albumbuffer.append(input)

        return False


    async def populate_tracks(self, albums: Album) -> List[Track]:
        '''This will populate the self.Tracks and return all Tracks list format '''
        progressbar = ProgressBar(len(albums))

        Tracks = []

        for album in albums:
            data = await self.add_to_buffer(album.id)
            progressbar.progress()
            if not data:
                continue
            else:
                for track in await self.get_track_data(data, album):
                    Tracks.append(track)
                        

        if len(self.albumbuffer) != 0:
            # Check if buffer has "leftover" albums in it.

            for track in await self.get_track_data(self.albumbuffer, album):
                Tracks.append(track)
        progressbar.done()
        return Tracks


    async def get_track_data(self, data: list, _album) -> List[Track]:
        Tracks= []
        spotify = self.spot
        
        results = await spotify.get_several_albums(data)

        for album in results['albums']:
            release_date = album['release_date']

            for track in album['tracks']['items']:
                track_id = track['id']
                track_name = track['name']
                duration = track['duration_ms'] * 1000
                track_artist_id = track['artists'][0]['id']
                track_artist_name = track['artists'][0]['name']

                if track_id in self.tracks:
                    continue
                else:
                    if track_artist_id in self.Artists:
                        self.tracks.append(track_id)
                        Tracks.append(
                            Track(
                                id=track_id,
                                name=track_name,
                                release_date=release_date,
                                duration=duration,
                                artist_id = track_artist_id,
                                artist_name = track_artist_name
                                ))
        return Tracks


class Playlists():

    playlist: Playlist = []
    
    def __init__(self, recentlier):
        self.spot = recentlier.spot
        self.recentlier = recentlier

    async def update(self):
        log(f'Playlist about to be updated.')
        self.playlist = await self.get_playlist()
        new_tracks = await self.order()
        new_tracks = new_tracks[::-1]
        playlist_tracks = await self.get_playlist_tracks()
  
        if set([i.id for i in new_tracks]) == set(playlist_tracks):
            log('The local playlist and online playlist are identical.')
        else:
            me = await self.spot.me()
            log('Updating online playlist')
            await self.spot.add_tracks(
                                      me['id'],
                                      self.playlist.id,
                                      [i.id for i in new_tracks]
                                    )
            for track in new_tracks:
                log(f'{track.artist_name} - {track.name} ({track.release_date})')



    async def get_playlist_tracks(self) -> dict:
        spotify = self.spot
        tracks = []
        results = await spotify.playlist_tracks(self.playlist.id, limit=100)
        for track in results['items']:
            tracks.append(track['track']['id'])
        return tracks    
        
    async def get_playlist(self) -> Playlist:
        ''' gets or creates the playlist id '''
        spotify = self.spot
        me = await spotify.me()

        if self.playlist:
            result = await spotify.playlist(
                                            me['id'],
                                            playlist_id=self.playlist.id)
            if result: 
                log(f'Using cached playlist "{self.playlist.name}"')
                return self.playlist
            else:
                # Playlist deleted.
                log(f'Cached playlist {self.Playlist.id} no longer exists.')
        
        playlist = None
        playlist_id = None
        new = 0
        if not spotify.config.playlist_name:
            raise Exception('["playlist"]["name"] is unset in config.json')

        if not spotify.config.playlist_id:
            # No id found in config, grab all the playlists
            # and look through all of them for playlist_name.
            playlists = []
            result = await spotify.playlists(me['id'], limit=50)
            for playlist in result['items']:
                playlists.append(Playlist(
                    id=playlist['id'],
                    owner=playlist['owner']['display_name'],
                    tracks=playlist['tracks']['href'],
                    name=playlist['name']

                ))
            while 'next' in result and result['next'] is not None:
                result = await spotify.next(result)
                for playlist in result['items']:
                    playlists.append(Playlist(
                    id=playlist['id'],
                    owner=playlist['owner']['display_name'],
                    tracks=playlist['tracks']['href'],
                    name=playlist['name']
                    ))
            
            for playlist in playlists:
                if spotify.config.playlist_name == playlist.name:
                    # Found the playlist
                    playlist = playlist if playlist.owner == me['id'] else None
                    break
                else:
                    playlist = None

            if not playlist:
                log(f'Unable to find a playlist. Creating one instead.')
                
                playlist_id = await spotify.create_playlist(
                                        me['id'],
                                        spotify.config.playlist_name,
                                        public=True,
                                        collaborative=False,
                                        description='Recentlier Releaseder')
                new = 1
                playlist_id = playlist_id['id']
        else:
            playlist_id = spotify.config.playlist_id

        if playlist_id:
            result = await spotify.playlist(
                                            me['id'],
                                            playlist_id=playlist_id)
            playlist = Playlist(
                                id=result['id'],
                                owner=result['owner']['display_name'],
                                tracks=result['tracks']['href'],
                                name=result['name']
                            )
        if new:
            spotify.config.playlist_id = playlist.id
            self.recentlier.Playlist = playlist
            #spotify.config.write()
            new = 0
        return playlist

    

    async def order(self):
        ''' sorts the entire list by release_date'''
        ordered = sorted(self.recentlier.Tracks,
                        key=operator.attrgetter(
                            'release_date'
                            ))
        return ordered[-int(self.spot.config.playlist_size):]
