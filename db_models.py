import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

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

class Platform(Base):
    __tablename__ = 'platforms_lookup'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)

class GameMode(Base):
    __tablename__ = 'game_modes_lookup'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)



#Main tables
class Game(Base):
    __tablename__ = 'games'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, nullable=False)
    rating = sa.Column(sa.Float)
    updated_at = sa.Column(sa.DateTime)
    first_release_date = sa.Column(sa.DateTime)
    
    # Many-to-many relationships
    genres = relationship('Genre', secondary=genres_junction, backref='games')
    game_modes = relationship('GameMode', secondary=game_modes_junction, backref='games')
    platforms = relationship('Platform', secondary=platforms_junction, backref='games')
    multiplayer_modes = relationship('MultiplayerMode', backref='game')

class MultiplayerMode(Base):
    __tablename__ = 'multiplayer_modes'
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    game = sa.Column(sa.Integer, sa.ForeignKey('games.id'))
    dropin = sa.Column(sa.Boolean)
    campaigncoop = sa.Column(sa.Boolean)
    offlinecoop = sa.Column(sa.Boolean)
    offlinecoopmax = sa.Column(sa.Integer)
    offlinemax = sa.Column(sa.Integer)
    onlinecoop = sa.Column(sa.Boolean)
    onlinecoopmax = sa.Column(sa.Integer)
    onlinemax = sa.Column(sa.Integer)
    splitscreen = sa.Column(sa.Boolean)
    platform = sa.Column(sa.Integer, sa.ForeignKey('platforms_lookup.id'))


