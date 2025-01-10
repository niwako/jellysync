#!/usr/bin/env python3
import argparse

from .jellysync import JellySync


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host-url",
        help="The Jellyfin host URL, e.g. https://jellyfin.myhost.com",
        required=True,
    )
    parser.add_argument(
        "--api-key",
        help="The Jellyfin API key, e.g. cab52cae2ffe4683a6a8d61a8c568e32",
        required=True,
    )
    parser.add_argument(
        "--user-id",
        help="The User ID, e.g. 2358e328747a4115be0e46a6dd35b16c",
        required=True,
    )
    parser.add_argument(
        "--media-dir",
        help="The destinatin media folder, e.g. /mnt/media",
    )
    parser.add_argument(
        "--use-content-disposition",
        help="Use the filename given by content disposition instead of metadata",
        action="store_true",
    )
    parser.add_argument(
        "--dry-run",
        help="Do a dry run without downloading",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        help="Print HTTP requests and responses to and from Jellyfin server",
        action="store_true",
    )

    subparsers = parser.add_subparsers(title="subcommands", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.set_defaults(cmd="search")
    search_parser.add_argument("query", help="The search query")

    download_series_parser = subparsers.add_parser("download-series")
    download_series_parser.set_defaults(cmd="download-series")
    download_series_parser.add_argument(
        "series_id",
        help="The Jellyfin series ID, e.g. 0b6ce693abb4663e3079cb01330bfd58",
    )

    download_season_parser = subparsers.add_parser("download-season")
    download_season_parser.set_defaults(cmd="download-season")
    download_season_parser.add_argument(
        "series_id",
        help="The Jellyfin series ID, e.g. 0b6ce693abb4663e3079cb01330bfd58",
    )
    download_season_parser.add_argument(
        "season_id",
        help="The Jellyfin season ID, e.g. b77ea4639d6b5645891f3ab93cafaaf0",
    )

    download_item_parser = subparsers.add_parser("download-item")
    download_item_parser.set_defaults(cmd="download-item")
    download_item_parser.add_argument(
        "item_id",
        help="The Jellyfin item ID, e.g. 4dd52f217a5025bee6a2614cbbf6c7d2",
    )

    args = parser.parse_args()

    jelly_sync = JellySync(
        args.host_url,
        args.api_key,
        args.user_id,
        args.media_dir,
        args.use_content_disposition,
        args.dry_run,
        args.debug,
    )

    if args.cmd == "search":
        jelly_sync.search(args.query)

    if args.cmd == "download-series":
        jelly_sync.download_series(args.series_id)

    if args.cmd == "download-season":
        jelly_sync.download_season(args.series_id, args.season_id)

    if args.cmd == "download-item":
        jelly_sync.download_item(args.item_id)


if __name__ == "__main__":
    main()
