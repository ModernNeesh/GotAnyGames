import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv
import os


Base = declarative_base()

#Initialize the database
def init_db():
    load_dotenv()
    POSTGRES_URL = os.getenv("POSTGRES_URL")

    engine = sa.create_engine(POSTGRES_URL, connect_args={"sslmode": "require"})

    Session = sessionmaker(bind=engine)
    inspector = sa.inspect(engine)

    #Skip table creation if all tables already exist
    expected_tables = [table.name for table in Base.metadata.sorted_tables]
    if not all(table_name in inspector.get_table_names() for table_name in expected_tables):
        print("Initializing cloud database tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
    else:
        print("Tables already exist.")

    return engine, Base, Session


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

group_membership = sa.Table(
    'group_membership',
    Base.metadata,
    sa.Column('user_id', PgUUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
    sa.Column('group_id', sa.Integer, sa.ForeignKey('groups.id'), primary_key=True)
)


#Feature lookup tables
class Genre(Base):
    """
    Represents a genre entry in the database.

    Columns/Attributes:

    id (Integer, primary key): The unique identifier of the genre entry.
    name (String): The name of the genre.
    updated_at (DateTime): The timestamp of the last update for the genre entry.
    """
    
    __tablename__ = 'genres_lookup'

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)
    updated_at = sa.Column(sa.DateTime)

    def __repr__(self):
        return f"<ID: {self.id}; Name: {self.name}>"

class Platform(Base):
    """
    Represents a platform entry in the database.

    Columns/Attributes:

    id (Integer, primary key): The unique identifier of the platform entry.
    name (String): The name of the platform.
    updated_at (DateTime): The timestamp of the last update for the platform entry.
    """

    __tablename__ = 'platforms_lookup'

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)
    updated_at = sa.Column(sa.DateTime)

    def __repr__(self):
        return f"<ID: {self.id}; Name: {self.name}>"


class GameMode(Base):
    """
    Represents a game mode entry in the database.

    Columns/Attributes:

    id (Integer, primary key): The unique identifier of the game mode entry.
    name (String): The name of the game mode.
    updated_at (DateTime): The timestamp of the last update for the game mode entry.
    """

    __tablename__ = 'game_modes_lookup'

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    name = sa.Column(sa.String, unique=True, nullable=False)
    updated_at = sa.Column(sa.DateTime)

    def __repr__(self):
        return f"<ID: {self.id}; Name: {self.name}>"

#Main tables
class Game(Base):
    """
    Represents a video game entry in the database.

    Columns/Attributes:

    id (Integer, primary key): The unique identifier of the game entry.
    name (String): The name of the game.
    total_rating (Float): The total rating of the game.
    total_rating_count (Integer): The total number of ratings for the game.
    updated_at (DateTime): The timestamp of the last update for the game entry.
    first_release_date (DateTime): The release date of the game.
    summary (String): A brief summary or description of the game.
    height (Integer): The height of the game's cover image if applicable.
    width (Integer): The width of the game's cover image if applicable.
    url (String): The URL to the game's cover image.
    slug (String): The slug or URL-friendly identifier for the game.
    game_type (Integer): The type or category of the game.

    
    genres (List[Genre]): The list of genres associated with the game. References the 'genres_lookup' table through the 'genres_junction' association table.
    game_modes (List[GameMode]): The list of game modes available for the game. References the 'game_modes_lookup' table through the 'game_modes_junction' association table.
    platforms (List[Platform]): The list of platforms the game is available on. References the 'platforms_lookup' table through the 'platforms_junction' association table.
    multiplayer_modes (List[MultiplayerMode]): The list of multiplayer modes available for the game. References the 'multiplayer_modes' table.
    
    """
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
    """
    Represents the multiplayer modes available for a specific game.

    Columns/Attributes:

    id (Integer, primary key): The unique identifier of the multiplayer mode entry.
    game (Integer, foreign key): The ID of the game this multiplayer mode belongs to. References the 'games' table.
    dropin (Boolean): Whether drop-in multiplayer is supported.
    campaigncoop (Boolean): Whether campaign co-op is supported.
    offlinecoopmax (Integer): Maximum number of players for offline co-op.
    offlinepvpmax (Integer): Maximum number of players for offline PVP.
    onlinecoopmax (Integer): Maximum number of players for online co-op.
    onlinepvpmax (Integer): Maximum number of players for online PVP.
    splitscreen (Boolean): Whether splitscreen is supported.
    platform (Integer, foreign key): The ID of the platform this multiplayer mode is available on. References the 'platforms_lookup' table.
    """
    __tablename__ = 'multiplayer_modes'

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    game = sa.Column(sa.Integer, sa.ForeignKey('games.id'))  # References the 'games' table.
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


#Classes for user and group data tables

class User(Base):
    """
    Represents a user in the system.

    Columns/Attributes:

    id (UUID, primary key): The Supabase UUID of the user.
    name (String): The name of the user.
    """

    __tablename__ = 'users'

    id = sa.Column(PgUUID(as_uuid=True), primary_key=True)
    name = sa.Column(sa.String)


class UserRating(Base):
    """
    Represents a user's rating for a specific game.
    
    Columns/Attributes:

    user_id (UUID, primary key): The Supabase UUID of the user who provided the rating.
    game_id (Integer, primary key): The ID of the game being rated.
    rating (Integer): The rating given by the user.
    """

    __tablename__ = "user_ratings"

    user_id = sa.Column(PgUUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True)
    game_id = sa.Column(sa.Integer, sa.ForeignKey('games.id'), primary_key=True)
    rating = sa.Column(sa.Integer)

    game_rel = relationship('Game')


class UserPref(Base):
    """
    Represents a user's platform preferences.

    Columns/Attributes:

    user_id (UUID, primary key): The Supabase UUID of the user this preference belongs to.
    platform_id (Integer, primary key): The ID of the platform selected by the user.
    online (Boolean, primary key): Whether the user prefers online play on this platform.
    offline (Boolean, primary key): Whether the user prefers offline play on this platform.
    """

    __tablename__ = "user_prefs"

    user_id = sa.Column(PgUUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True)
    platform_id = sa.Column(sa.Integer, sa.ForeignKey('platforms_lookup.id'), primary_key=True)
    online = sa.Column(sa.Boolean, primary_key=True)
    offline = sa.Column(sa.Boolean, primary_key=True)



class Group(Base):
    """
    Represents a group of users.

    Columns/Attributes:

    id (Integer): The unique identifier for the group.
    name (String): The name of the group.
    users (List[User]): The list of users who are members of the group. References the 'users' table through the 'group_membership' association table.
    """
    __tablename__ = "groups"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)

    users = relationship('User', secondary=group_membership, backref='groups')


class GroupUserPreference(Base):
    """
    Represents one selected platform for one user's preferences in one group.
    

    Columns/Attributes:

    group_id (Integer, primary key): The ID of the group this preference belongs to.
    user_id (UUID, primary key): The Supabase UUID of the user this preference belongs to.
    platform_id (Integer, primary key): The ID of the platform selected by the user.
    online (Boolean): Whether the user prefers online play on this platform, in this group.
    offline (Boolean): Whether the user prefers offline play on this platform, in this group.
    """

    __tablename__ = "group_user_preferences"

    group_id = sa.Column(sa.Integer, sa.ForeignKey('groups.id'), primary_key=True)
    user_id = sa.Column(PgUUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True)
    platform_id = sa.Column(sa.Integer, sa.ForeignKey('platforms_lookup.id'), primary_key=True)
    online = sa.Column(sa.Boolean, nullable=False)
    offline = sa.Column(sa.Boolean, nullable=False)
