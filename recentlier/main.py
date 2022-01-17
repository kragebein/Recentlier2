#!/usr/bin/python3.10
import sys
import operator

from typing import Any, List
from recentlier.spotify import Spotify
from recentlier.tools import log, Cache
from recentlier.classes import Artist, Track, Album


class Recentlier:

    spot = Spotify()
    albumbuffer:list = []
    tracks:list = []

    def __init__(self):

        self.cache = Cache(self)

        self.Artists:list = []
        self.Albums:list = []
        self.Tracks:list = []

    async def run(self):
        # Preload from cache (if any)
        self.Artists, self.Albums, self.Tracks = await self.cache.load()
        
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

        elif len(albums) ==  len(self.Albums):
            log(f'Albums found: {str(len(albums))}')
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

            elif len(tracks) ==  len(self.Tracks):
                log(f'Tracks found: {str(len(artists))}')

            elif len(tracks) < len(self.Tracks):
                len(f'Tracks found: {str(len(tracks))} (removed: {str(len(self.Tracks) - len(tracks))})')
                self.Tracks = tracks
                update_playlist = 1
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
                for track in await self.get_track_data(data):

                    if track.id in self.Tracks or track.id in Tracks:
                        continue
                    else:
                        Tracks.append(track)
                        

        if len(self.albumbuffer) != 0:
            # Check if buffer has "leftover" albums in it.

            for track in await self.get_track_data(self.albumbuffer):
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

                if track_id in Tracks or track_id in self.Tracks:
                    continue
                else:
                    Tracks.append(Track(id=track_id, name=track_name, release_date=release_date))
        return Tracks

    async def order(self):
        ''' returns a sorted list of tracks, ready for playlist '''
        raise NotImplementedError()


        ordered = sorted(self.Tracks,
                        key=operator.attrgetter(
                            'release_date'
                            ))

        ordered = ordered[-int(self.spot.config.playlist_size):]

        for x in ordered:
            print(x.id, x.name, x.release_date)
        
        return ordered
