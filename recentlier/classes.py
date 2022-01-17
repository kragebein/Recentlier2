from dataclasses import dataclass

@dataclass(order=True)
class Track:
    id: str
    name: str
    release_date: str

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

@dataclass
class Artist:
    id: str
    name: str


@dataclass
class Playlist:
    id: str
    size: int
    albums: str
