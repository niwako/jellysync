from typing import TypedDict, TypeGuard


class Item(TypedDict):
    Id: str
    Name: str
    Type: str
    ProductionYear: int


class MediaSource(TypedDict):
    Container: str


class FullItem(Item):
    MediaSources: list[MediaSource]


class Episode(FullItem):
    SeriesName: str
    IndexNumber: int
    ParentIndexNumber: int


class Movie(FullItem): ...


class Series(FullItem): ...


def is_episode(item: Item) -> TypeGuard[Episode]:
    return item["Type"] == "Episode"


def is_movie(item: Item) -> TypeGuard[Movie]:
    return item["Type"] == "Movie"


def is_series(item: Item) -> TypeGuard[Series]:
    return item["Type"] == "Series"
