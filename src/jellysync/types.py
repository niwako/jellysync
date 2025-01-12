from typing import Literal, TypedDict, TypeGuard


class MediaSource(TypedDict):
    Container: str


class Item(TypedDict):
    Id: str
    Name: str
    Type: Literal["Episode", "Movie", "Series", "Season"]
    ProductionYear: int


class Episode(Item):
    SeriesName: str
    IndexNumber: int
    ParentIndexNumber: int
    MediaSources: list[MediaSource]


class Movie(Item):
    MediaSources: list[MediaSource]


class Season(Item):
    SeriesId: str


class Series(Item): ...


def is_episode(item: Item) -> TypeGuard[Episode]:
    return item["Type"] == "Episode"


def is_movie(item: Item) -> TypeGuard[Movie]:
    return item["Type"] == "Movie"


def is_season(item: Item) -> TypeGuard[Season]:
    return item["Type"] == "Season"


def is_series(item: Item) -> TypeGuard[Series]:
    return item["Type"] == "Series"


class User(TypedDict):
    Name: str
    Id: str


class AuthenticationResponse(TypedDict):
    User: User
    AccessToken: str
