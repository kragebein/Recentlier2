from dataclasses import dataclass

@dataclass(order=True)
class Track:
    id: str
    name: str
    release_date: str
    duration: int
    artist_id: str
    artist_name: str
    

    def __post_init__(self):
        ''' enables comparison and sorting'''
        object.__setattr__(self, 'release_date', self.release_date)

    def __repr__(self):
        return self.id
    
    def __eq__(self, _id): 
        return self.id == _id 

@dataclass
class Album:
    release_date: str
    id: str
    name: str
    artist_name: str
    artist_id: str

    def __eq__(self, id):
        return self.id == id

@dataclass
class Artist:
    id: str
    name: str


@dataclass
class Playlist:
    id: str
    name: str
    owner: str
    tracks: list


    def __eq__(self, _in): 
        return self.name == _in or self.id == _in