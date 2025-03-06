#!/usr/bin/env python3
import asyncio
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
    DownloadColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
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

console = Console()
client = httpx.AsyncClient(
    transport=httpx.AsyncHTTPTransport(
        retries=5,
        limits=httpx.Limits(
            max_connections=20,
        ),
    ),
    timeout=30,
)


async def gather(tasks):
    results = await asyncio.gather(*tasks)
    return [item for collection in results for item in collection]


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
    dry_run: bool = False
    debug: bool = False

    def __post_init__(self):
        if self.media_dir:
            os.chdir(os.path.expanduser(self.media_dir))
        self.semaphore = asyncio.Semaphore(20)

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
        console.print(table)

    async def search(self, query: str):
        items = await self.search_items(query)
        if len(items) == 0:
            print(f'No results found for "{query}"')
            return
        self.render_table(items)

    async def download_item(self, item_id: str):
        with console.status("Collecting metadata..."):
            items = await self.collect(item_id)
        console.print(f"[bold green]✔[/bold green] Collected {len(items)} items.")
        for item in items:
            self.download(item)

    def get_auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f'MediaBrowser Client="JellySync", Token="{self.token}"'
        }

    async def get(self, url):
        if self.debug:
            print(f"GET {url}")
        async with self.semaphore:
            resp = await client.get(url, headers=self.get_auth_header())
        resp.raise_for_status()
        data = resp.json()
        if self.debug:
            print(data)
        return data

    async def get_item(self, item_id: str) -> Item:
        url = f"{self.host}/Users/{self.user_id}/Items/{item_id}"
        return await self.get(url)

    async def collect(self, item_id: str) -> list[Episode | Movie]:
        item = await self.get_item(item_id)
        if is_episode(item) or is_movie(item):
            return [item]
        if is_season(item):
            episodes = await self.get_episodes(item["SeriesId"], item["Id"])
            return await gather([self.collect(episode["Id"]) for episode in episodes])
        if is_series(item):
            seasons = await self.get_seasons(item["Id"])
            return await gather([self.collect(season["Id"]) for season in seasons])
        raise Exception(f"Unknown item type for {item_id}: {item['Type']}")

    async def search_items(self, search_terms: str) -> list[Item]:
        params = urlencode(
            {
                "searchTerm": search_terms,
                "recursive": True,
                "includeItemTypes": ",".join(["Movie", "Series", "Episode"]),
            }
        )
        url = f"{self.host}/Items?{params}"
        resp = await self.get(url)
        return resp["Items"]

    async def get_seasons(self, series_id: str) -> list[Item]:
        url = f"{self.host}/Shows/{series_id}/Seasons"
        resp = await self.get(url)
        return resp["Items"]

    async def get_episodes(self, series_id: str, season_id: str) -> list[Item]:
        url = f"{self.host}/Shows/{series_id}/Episodes?seasonId={season_id}"
        resp = await self.get(url)
        return resp["Items"]

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

        filename = self.make_file_path(item)
        filesize = item["MediaSources"][0]["Size"]
        if os.path.isfile(filename):
            text = Text()
            text.append("Skipping ", style="bold red")
            text.append(filename, style="bold")
            text.append(" because file already exists", style="bold blue")
            print(text)
            return

        with httpx.stream("GET", url, headers=self.get_auth_header()) as resp:
            resp.raise_for_status()
            filesize = int(resp.headers["Content-Length"])

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

            with open(f"{filename}.tmp", "wb") as fp:
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                    TextColumn("remaining"),
                    DownloadColumn(),
                    TextColumn("at"),
                    TransferSpeedColumn(),
                ) as progress:
                    task = progress.add_task("Downloading", total=filesize)
                    for bytes in resp.iter_bytes():
                        progress.update(task, advance=len(bytes))
                        fp.write(bytes)
            os.rename(f"{filename}.tmp", filename)
