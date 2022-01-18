#!/usr/bin/python3.10
import sys
import operator

from typing import Any, List
from unicodedata import name
from recentlier.spotify import Spotify
from recentlier.tools import log, Cache, ProgressBar
from recentlier.classes import Artist, Playlist, Track, Album


class Recentlier:

    spot = Spotify()
    albumbuffer:list = []
    tracks:list = []

    def __init__(self):

        self.cache = Cache(self)

        self.Artists:list = []
        self.Albums:list = []
        self.Tracks:list = []
        self.Playlist: Playlist = None

    async def run(self):
        # Preload from cache (if any)
        await self.cache.load(self)
        

        run_tracks = 0
        update_playlist = 0

        artists = await self.populate_artists()


        if len(artists) > len(self.Artists):
            log(f'Artists found: {str(len(artists))} (new: {str(len(artists) - len(self.Artists))})')
            self.Artists = artists
            run_tracks = 1

        elif len(artists) ==  len(self.Artists):
            log(f'Artists found: {str(len(artists))}')

        elif len(artists) < len(self.Artists):
            len(f'Artists found: {str(len(artists))} (removed: {str(len(self.Artists) - len(artists))})')
            self.Artists = artists
            run_tracks = 1


        albums = await self.populate_albums(artists)

        if len(albums) > len(self.Albums):
            log(f'Albums found: {str(len(albums))} (new: {str(len(albums) - len(self.Albums))})')
            self.Albums = albums
            run_tracks = 1
            await self.cache.write()
            
        elif len(albums) ==  len(self.Albums):
            log(f'Albums found: {str(len(albums))} (Nothing to update)')
            run_tracks = 0

        elif len(albums) < len(self.Albums):
            len(f'Artists found: {str(len(albums))} (removed: {str(len(self.Albums) - len(albums))})')
            self.Albums = albums
            run_tracks = 1
            await self.cache.write()
        
        if run_tracks:
            tracks = await self.populate_tracks(self.Albums)
            if len(tracks) > len(self.Tracks):
                log(f'Tracks found: {str(len(tracks))} (new: {str(len(tracks) - len(self.Tracks))})')
                self.Tracks = tracks
                update_playlist = 1
                await self.cache.write()

            elif len(tracks) ==  len(self.Tracks):
                log(f'Tracks found: {str(len(artists))}')

            elif len(tracks) < len(self.Tracks):
                len(f'Tracks found: {str(len(tracks))} (removed: {str(len(self.Tracks) - len(tracks))})')
                self.Tracks = tracks
                update_playlist = 1
                await self.cache.write()

        if update_playlist:
            playlist = await self.playlist()
            self.Playlist = playlist

        await self.cache.write()

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

        Tracks = []

        for album in albums:
            data = await self.add_to_buffer(album.id)
            if not data:
                continue
            else:
                for track in await self.get_track_data(data), album:

                    if track.id in self.Tracks or track.id in Tracks:
                        continue
                    else:
                        Tracks.append(track)
                        

        if len(self.albumbuffer) != 0:
            # Check if buffer has "leftover" albums in it.

            for track in await self.get_track_data(self.albumbuffer, album):
                if track.id in self.Tracks or track.id in Tracks:
                    continue
                else:
                    Tracks.append(track)
                    
        return Tracks


    async def get_track_data(self, data: list) -> List[Track]:
        Tracks= []
        spotify = self.spot
        
        results = await spotify.get_several_albums(data)

        for album in results['albums']:
            release_date = album['release_date']

            for track in album['tracks']['items']:
                track_id = track['id']
                track_name = track['name']
                duration = track['duration_ms'] * 1000
        

                if track_id in Tracks or track_id in self.Tracks:
                    continue
                else:
                    Tracks.append(
                        Track(
                            id=track_id,
                            name=track_name,
                            release_date=release_date,
                            duration=duration,
                            artist_id = album.artist_id,
                            artist_name = album.artist_name
                            ))
        return Tracks

    async def playlist(self) -> Playlist:
        ''' gets or creates the playlist id '''
        spotify = self.spot
        me = await spotify.me()

        if self.Playlist:
            result = await spotify.playlist(
                                            me['id'],
                                            playlist_id=self.Playlist.id)
            if result: 
                log(f'Using cached playlist "{self.Playlist.name}"')
                return self.Playlist
            else:
                # Playlist deleted.
                log(f'Cached playlist {self.Playlist.id} no longer exists.')
        
        playlist = None
        playlist_id = None
        new = 0
        if not spotify.config.playlist_name:
            raise Exception('["playlist"]["name"] is unset in config.json')

        if not spotify.config.playlist_id:
            # No Id found in config, grab all the playlists.
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
            spotify.config.write()
            new = 0
        return playlist


    async def order(self):
        ''' sorts the entire list by release_date'''
        ordered = sorted(self.Tracks,
                        key=operator.attrgetter(
                            'release_date'
                            ))
       
        return ordered[-int(self.spot.config.playlist_size):]

