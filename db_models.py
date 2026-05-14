import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv
import os

# Create the engine
load_dotenv()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

engine = sa.create_engine(f'postgresql://postgres:{POSTGRES_PASSWORD}@localhost:5432/GamesDatabase')
Base = declarative_base()

Session = sessionmaker(bind=engine)
Base = declarative_base()
Base.metadata.create_all(engine)


# Junction tables for many-to-many relationships
genres_junction = sa.Table(
    'genres_junction',
    Base.metadata,
    sa.Column('game_id', sa.Integer, sa.ForeignKey('games.id'), primary_key=True),
    sa.Column('genres_id', sa.Integer, sa.ForeignKey('genres_lookup.id'), primary_key=True)
)

game_modes_junction = sa.Table(
    'game_modes_junction',
    Base.metadata,
    sa.Column('game_id', sa.Integer, sa.ForeignKey('games.id'), primary_key=True),
    sa.Column('game_modes_id', sa.Integer, sa.ForeignKey('game_modes_lookup.id'), primary_key=True)
)

platforms_junction = sa.Table(
    'platforms_junction',
    Base.metadata,
    sa.Column('game_id', sa.Integer, sa.ForeignKey('games.id'), primary_key=True),
    sa.Column('platforms_id', sa.Integer, sa.ForeignKey('platforms_lookup.id'), primary_key=True)
)


#Feature lookup tables
class Genre(Base):
    __tablename__ = 'genres_lookup'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)

    def __repr__(self):
        return f"<ID: {self.id}; Name: {self.name}>"

class Platform(Base):
    __tablename__ = 'platforms_lookup'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)

    def __repr__(self):
        return f"<ID: {self.id}; Name: {self.name}>"


class GameMode(Base):
    __tablename__ = 'game_modes_lookup'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)

    def __repr__(self):
        return f"<ID: {self.id}; Name: {self.name}>"

#Main tables
class Game(Base):
    __tablename__ = 'games'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, nullable=False)
    total_rating = sa.Column(sa.Float)
    total_rating_count = sa.Column(sa.Integer)
    updated_at = sa.Column(sa.DateTime)
    first_release_date = sa.Column(sa.DateTime)
    summary = sa.Column(sa.String)
    height = sa.Column(sa.Integer)
    width = sa.Column(sa.Integer)
    url = sa.Column(sa.String)
    slug = sa.Column(sa.String)
    game_type = sa.Column(sa.Integer)
    
    # Many-to-many relationships
    genres = relationship('Genre', secondary=genres_junction, backref='games')
    game_modes = relationship('GameMode', secondary=game_modes_junction, backref='games')
    platforms = relationship('Platform', secondary=platforms_junction, backref='games')
    multiplayer_modes = relationship('MultiplayerMode', backref = 'game_obj')


    def __repr__(self):
        return f"{self.name} (ID: {self.id})"

class MultiplayerMode(Base):
    __tablename__ = 'multiplayer_modes'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    game = sa.Column(sa.Integer, sa.ForeignKey('games.id'))
    dropin = sa.Column(sa.Boolean)
    campaigncoop = sa.Column(sa.Boolean)
    offlinecoopmax = sa.Column(sa.Integer)
    offlinepvpmax = sa.Column(sa.Integer)
    onlinecoopmax = sa.Column(sa.Integer)
    onlinepvpmax = sa.Column(sa.Integer)
    splitscreen = sa.Column(sa.Boolean)
    platform = sa.Column(sa.Integer, sa.ForeignKey('platforms_lookup.id'))

    platform_obj = relationship('Platform')

    def get_supported_modes(self):
        modes = {"Campaign Co-Op" : self.campaigncoop,
                 f"Offline Co-Op (max {self.offlinecoopmax})" : bool(self.offlinecoopmax),
                 f"Offline PVP (max {self.offlinepvpmax})" : bool(self.offlinepvpmax),
                 f"Online Co-Op (max {self.onlinecoopmax})" : bool(self.onlinecoopmax),
                 f"Online PVP (max {self.onlinepvpmax})" : bool(self.onlinepvpmax),
                 "Splitscreen" : self.splitscreen}
        
        supported_modes = [mode_str for mode_str, mode_exists in modes.items() if mode_exists]
        return ["None"] if len(supported_modes) == 0 else supported_modes

    def __repr__(self):
        platform_name = self.platform_obj.name if self.platform_obj else f"ID:{self.platform}"
        return f"Game: {self.game_obj} on {platform_name}. Supports: {", ".join(self.get_supported_modes())}"



