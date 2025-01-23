#!/usr/bin/env python3
import os
from dataclasses import KW_ONLY, dataclass
from email.message import EmailMessage
from urllib.parse import urlencode

import httpx
from pathvalidate import sanitize_filepath
from rich import print
from rich.console import Console
from rich.progress import (
    BarColumn,
    FileSizeColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TotalFileSizeColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text

from jellysync.types import (
    Episode,
    Item,
    Movie,
    is_episode,
    is_movie,
    is_season,
    is_series,
)


def parse_filename(content_disposition: str) -> str:
    msg = EmailMessage()
    msg["content-type"] = content_disposition
    params = msg["content-type"].params
    return sanitize_filepath(params["filename"])


@dataclass
class JellySync:
    host: str
    token: str
    user_id: str
    _: KW_ONLY
    media_dir: str | None = None
    use_content_disposition: bool = False
    dry_run: bool = False
    debug: bool = False

    def __post_init__(self):
        if self.media_dir:
            os.chdir(os.path.expanduser(self.media_dir))

    def render_table(self, items: list[Item]):
        table = Table("Type", "Title", "Year", "ID")
        for item in items:
            name = item["Name"]
            year = str(item.get("ProductionYear"))

            if is_series(item):
                style = "magenta"
            elif is_episode(item):
                style = "cyan"
                name = f"{item['Name']} ({item['SeriesName']})"
            elif is_movie(item):
                style = "green"
            else:
                style = None

            table.add_row(item["Type"], name, year, item["Id"], style=style)
        console = Console()
        console.print(table)

    def search(self, query: str):
        items = self.search_items(query)
        if len(items) == 0:
            print(f'No results found for "{query}"')
            return
        self.render_table(items)

    def download_series(self, series_id: str):
        seasons = self.get_seasons(series_id)
        for season in seasons:
            self.download_season(series_id, season["Id"])

    def download_season(self, series_id: str, season_id: str):
        episodes = self.get_episodes(series_id, season_id)
        for episode in episodes:
            self.download_item(episode["Id"])

    def download_item(self, item_id: str):
        item = self.get_item(item_id)
        if is_episode(item) or is_movie(item):
            self.download(item)
        elif is_season(item):
            self.download_season(item["SeriesId"], item["Id"])
        elif is_series(item):
            self.download_series(item["Id"])
        else:
            raise Exception(f"Unknown item type for {item_id}: {item['Type']}")

    def get_auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f'MediaBrowser Client="JellySync", Token="{self.token}"'
        }

    def get(self, url):
        if self.debug:
            print(f"GET {url}")
        resp = httpx.get(url, headers=self.get_auth_header())
        resp.raise_for_status()
        data = resp.json()
        if self.debug:
            print(data)
        return data

    def get_item(self, item_id: str) -> Item:
        url = f"{self.host}/Users/{self.user_id}/Items/{item_id}"
        return self.get(url)

    def search_items(self, search_terms: str) -> list[Item]:
        params = urlencode(
            {
                "searchTerm": search_terms,
                "recursive": True,
                "includeItemTypes": ",".join(["Movie", "Series", "Episode"]),
            }
        )
        url = f"{self.host}/Items?{params}"
        return self.get(url)["Items"]

    def get_seasons(self, series_id: str) -> list[Item]:
        url = f"{self.host}/Shows/{series_id}/Seasons"
        return self.get(url)["Items"]

    def get_episodes(self, series_id: str, season_id: str) -> list[Item]:
        url = f"{self.host}/Shows/{series_id}/Episodes?seasonId={season_id}"
        return self.get(url)["Items"]

    def make_file_path(self, item: Episode | Movie):
        if is_episode(item):
            series = item["SeriesName"]
            episode_id = f"S{item['ParentIndexNumber']:02d}E{item['IndexNumber']:02d}"
            title = item["Name"]
            ext = item["MediaSources"][0]["Container"]
            return sanitize_filepath(
                os.path.join(
                    "Shows",
                    series,
                    f"Season {item['ParentIndexNumber']:02d}",
                    f"{series} - {episode_id} - {title}.{ext}",
                )
            )

        if is_movie(item):
            title = item["Name"]
            year = item["ProductionYear"]
            ext = item["MediaSources"][0]["Container"]
            return sanitize_filepath(
                os.path.join(
                    "Movies",
                    f"{title} ({year})",
                    f"{title} ({year}).{ext}",
                )
            )

        raise Exception(f"Unknown Item Type: {item['Type']}")

    def download(self, item: Movie | Episode):
        url = f"{self.host}/Items/{item['Id']}/Download"
        if self.debug:
            print(f"Download URL: {url}")
        with httpx.stream("GET", url, headers=self.get_auth_header()) as resp:
            resp.raise_for_status()
            if self.use_content_disposition:
                filename = parse_filename(resp.headers["Content-Disposition"])
            else:
                filename = self.make_file_path(item)
            filesize = int(resp.headers["Content-Length"])

            if os.path.isfile(filename):
                existing_filesize = os.stat(filename).st_size
                if filesize == existing_filesize:
                    text = Text()
                    text.append("Skipping ", style="bold red")
                    text.append(filename, style="bold")
                    text.append(" because file already exists", style="bold blue")
                    print(text)
                    return

            if self.dry_run:
                text = Text()
                text.append("Skipping ", style="bold red")
                text.append(filename, style="bold")
                text.append(" because dry-run flag is set", style="bold blue")
                print(text)
                return

            text = Text()
            text.append("Downloading ", style="bold green")
            text.append(filename, style="bold")
            print(text)

            folder = os.path.dirname(filename)
            if folder:
                os.makedirs(folder, exist_ok=True)

            with open(filename, "wb") as fp:
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                    TextColumn("remaining"),
                    FileSizeColumn(),
                    TextColumn("of"),
                    TotalFileSizeColumn(),
                    TextColumn("at"),
                    TransferSpeedColumn(),
                ) as progress:
                    task = progress.add_task("Downloading", total=filesize)
                    for bytes in resp.iter_bytes():
                        progress.update(task, advance=len(bytes))
                        fp.write(bytes)
