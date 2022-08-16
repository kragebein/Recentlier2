#!/usr/bin/python3.10
import asyncio
import operator

from typing import Any, Dict, List, Tuple
from recentlier.spotify import Spotify
from recentlier.util import log, Cache, ProgressBar, Flags, Version
from recentlier.classes import Artist, Playlist, Track, Album


class Recentlier:

    spot = Spotify()
    albumbuffer: list = []
    tracks: list = []

    def __init__(self):

        Version()
        self.Artists: list = []
        self.Albums: list = []
        self.Tracks: list = []
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

            log('Sleeping for 6 hours.')
            await asyncio.sleep(21600)

    async def populate_artists(self) -> List[Artist]:
        '''Creates a list of Artist-dataclasses.'''
        Artists = []
        spotify = self.spot

        results = await spotify.get_artists(limit=50)
        for artist in results['artists']['items']:
            Artists.append(Artist(id=artist['id'], name=artist['name']))

            log(f'Appended {artist["name"]} to Artists', silent=not spotify.config.verbose)

        while 'next' in results['artists'] and results['artists']['next'] is not None:
            results = await spotify.next(results['artists'])

            for artist in results['artists']['items']:
                Artists.append(Artist(id=artist['id'], name=artist['name']))

                log(f'Appended {artist["name"]} to Artists', silent=not spotify.config.verbose)
        return Artists

    async def populate_albums(self, artists: Artist) -> List[Album]:
        '''creates a list of Album-databalasses'''
        progressbar = ProgressBar(len(self.Artists), 'Populating albums')
        Albums = []
        spotify = self.spot
        for artist in artists:
            results = await spotify.artist_albums(artist.id, limit=50)

            for album in results['items']:
                if album['id'] not in Albums:
                    Albums.append(
                        Album(
                            id=album['id'],
                            release_date=album['release_date'],
                            name=album['name'],
                            artist_name=artist.name,
                            artist_id=artist.id,
                        )
                    )

                    log(f'Appended {album["name"]} to Albums', silent=not spotify.config.verbose)

            while 'next' in results and results['next'] is not None:
                results = await spotify.next(results)

                for album in results['items']:
                    if album["id"] not in Albums:
                        Albums.append(
                            Album(
                                id=album['id'],
                                release_date=album['release_date'],
                                name=album['name'],
                                artist_name=artist.name,
                                artist_id=artist.id,
                            )
                        )

                        log(f'Appended {album["name"]} to Albums', silent=not spotify.config.verbose)

            progressbar.progress()
        progressbar.done()
        return Albums

    async def add_to_buffer(self, input: str) -> Any:
        '''Return only when buffer is full'''

        if len(self.albumbuffer) + 1 == 20:
            self.albumbuffer.append(input)
            data = self.albumbuffer
            self.albumbuffer = []

            return data
        else:
            self.albumbuffer.append(input)

        return False

    async def populate_tracks(self, albums: Album) -> List[Track]:
        '''Creates a list of Track-dataclasses'''

        temporary_tracks = []
        duplicates = {}
        progressbar = ProgressBar(len(albums), 'Populating tracks')

        Tracks = []

        for album in albums:
            data = await self.add_to_buffer(album.id)
            progressbar.progress()
            if not data:
                continue
            else:
                for track in await self.get_track_data(data, album):
                    # We should check against duplicates here
                    temporary_tracks.append(track)
        if len(self.albumbuffer) != 0:
            # Check if buffer has "leftover" albums in it.
            for track in await self.get_track_data(self.albumbuffer, album):
                temporary_tracks.append(track)

        progressbar.done()
        
        progressbar = ProgressBar(len(temporary_tracks), 'Sorting tracks')
        for track in temporary_tracks:
            duplicate = f'{track.artist_name} - {track.name}'
            if duplicate in temporary_tracks:
                log(f'{duplicate} is a duplicate', silent=not self.spot.config.verbose)
                # To be dealt with later
                duplicates[duplicate] = []
                duplicates[duplicate].append(track)
                progressbar.progress()
            else:
                # Approved for final track list.
                Tracks.append(track)
                log(f'Appended {track.artist_name} - {track.name} to Tracks', silent=not self.spot.config.verbose)
                progressbar.progress()
        progressbar.done()
        temporary_tracks = []
        print(duplicates)

        progressbar = ProgressBar(len(duplicates), 'Sorting by release date')
        for track in duplicates:
            # Get the earliest release date from the duplicates.
            earliest = min(duplicates[track], key=lambda x: x.release_date)
            log(f'{earliest.name} has the earliest release date of {earliest.release_date}', silent=not self.spot.config.verbose)
            Tracks.append(earliest)
            log(f'Appended {earliest.artist_name} - {earliest.name} to Tracks', silent=not self.spot.config.verbose)
            progressbar.progress()
        progressbar.done()
            
        return Tracks

    async def check_artist_in_track(self, artists: List[Dict]) -> bool:
        '''Checks if one of the artists of this track is in the db'''
        for artist in artists:
            if artist['id'] in self.Artists:
                return artist
        return False

    async def get_track_data(self, data: list, _album) -> List[Track]:
        Tracks = []
        spotify = self.spot

        results = await spotify.get_several_albums(data)

        for album in results['albums']:
            release_date = album['release_date']

            for track in album['tracks']['items']:
                track_id = track['id']
                track_name = track['name']
                duration = track['duration_ms'] * 1000
                track_artists = track['artists']

                if track_id in self.tracks:
                    # skip this track, if track id has been processed.
                    continue

                else:
                    if get_artist := await self.check_artist_in_track(track_artists):
                        self.tracks.append(track_id)
                        Tracks.append(
                            Track(
                                id=track_id,
                                name=track_name,
                                release_date=release_date,
                                duration=duration,
                                artist_id=get_artist['id'],
                                artist_name=get_artist['name'],
                            )
                        )

            while 'next' in album and album['next'] is not None:
                album = await spotify.next(album)
                for track in album['items']:
                    track_id = track['id']
                    track_name = track['name']
                    duration = track['duration_ms'] * 1000
                    track_artists = track['artists']

                    if track_id in self.tracks:
                        continue

                    else:
                        if get_artist := await self.check_artist_in_track(track_artists):
                            self.tracks.append(track_id)
                            Tracks.append(
                                Track(
                                    id=track_id,
                                    name=track_name,
                                    release_date=release_date,
                                    duration=duration,
                                    artist_id=get_artist['id'],
                                    artist_name=get_artist['name'],
                                )
                            )
        return Tracks


class Playlists:
    playlist: Playlist = []

    def __init__(self, recentlier):
        self.spot = recentlier.spot
        self.recentlier = recentlier

    async def update(self):
        log('----------------------------')
        self.playlist = await self.get_playlist()
        new_tracks = await self.order()
        new_tracks = new_tracks[::-1]
        playlist_tracks = await self.get_playlist_tracks()

        if set([i.id for i in new_tracks]) == set(playlist_tracks):
            log('The local playlist and online playlist are identical.')

        else:
            me = await self.spot.me()
            log('Updating online playlist')
            await self.spot.add_tracks(me['id'], self.playlist.id, [i.id for i in new_tracks])
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
        '''gets or creates the playlist id'''
        spotify = self.spot
        me = await spotify.me()

        if self.playlist:
            result = await spotify.playlist(me['id'], playlist_id=self.playlist.id)

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
                playlists.append(
                    Playlist(
                        id=playlist['id'],
                        owner=playlist['owner']['display_name'],
                        tracks=playlist['tracks']['href'],
                        name=playlist['name'],
                    )
                )
            while 'next' in result and result['next'] is not None:
                result = await spotify.next(result)
                for playlist in result['items']:
                    playlists.append(
                        Playlist(
                            id=playlist['id'],
                            owner=playlist['owner']['display_name'],
                            tracks=playlist['tracks']['href'],
                            name=playlist['name'],
                        )
                    )

            for playlist in playlists:
                if spotify.config.playlist_name == playlist.name:
                    # Found the playlist
                    playlist = playlist if playlist.owner == me['id'] else None
                    break
                else:
                    playlist = None

            if not playlist:
                log('Unable to find a playlist. Creating one instead.')

                playlist_id = await spotify.create_playlist(
                    me['id'], spotify.config.playlist_name, public=True, collaborative=False, description='Recentlier Releaseder'
                )

                new = 1
                playlist_id = playlist_id['id']

        else:
            playlist_id = spotify.config.playlist_id

        if playlist_id:
            result = await spotify.playlist(me['id'], playlist_id=playlist_id)

            playlist = Playlist(
                id=result['id'], owner=result['owner']['display_name'], tracks=result['tracks']['href'], name=result['name']
            )

        if new:
            spotify.config.playlist_id = playlist.id
            self.recentlier.Playlist = playlist
            new = 0
        return playlist

    async def order(self):
        '''sorts the entire list by release_date'''
        ordered = sorted(self.recentlier.Tracks, key=operator.attrgetter('release_date'))

        return ordered[-int(self.spot.config.playlist_size) :]
