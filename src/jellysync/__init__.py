#!/usr/bin/env python3
import argparse
import json

from rich import print

from .config import JellySyncConfigs
from .jellysync import JellySync


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--config", help="The config name to use from ~/.jellysync")
    parser.add_argument("--host", help="The Jellyfin host URL")
    parser.add_argument("--token", help="The Jellyfin API key")
    parser.add_argument("--user-id", help="The User ID")
    parser.add_argument("--media-dir", help="The output folder, e.g. /mnt/media")

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

    login_parser = subparsers.add_parser("login")
    login_parser.set_defaults(cmd="login")
    login_parser.add_argument("--name", help="The name of the configuration")
    login_parser.add_argument("--host", help="The Jellyfin host URL")
    login_parser.add_argument("--user", help="The user name, e.g. jellyfin")
    login_parser.add_argument("--media-dir", help="The output folder, e.g. /mnt/media")

    info_parser = subparsers.add_parser("info")
    info_parser.set_defaults(cmd="info")
    info_parser.add_argument("item_id", help="The Jellyfin item ID")

    search_parser = subparsers.add_parser("search")
    search_parser.set_defaults(cmd="search")
    search_parser.add_argument("query", help="The search query")

    download_parser = subparsers.add_parser("download")
    download_parser.set_defaults(cmd="download")
    download_parser.add_argument("item_id", help="The Jellyfin item ID")

    args = parser.parse_args()

    configs = JellySyncConfigs.load()

    if args.cmd == "login":
        configs.configure(
            host=args.host,
            user=args.user,
            name=args.name,
        )
        configs.save()
        return

    config = configs.resolve(parser, args)

    jelly_sync = JellySync(
        config.host,
        config.token,
        config.user_id,
        media_dir=config.media_dir,
        use_content_disposition=args.use_content_disposition,
        dry_run=args.dry_run,
        debug=args.debug,
    )

    if args.cmd == "info":
        print(json.dumps(jelly_sync.get_item(args.item_id)))
        return

    if args.cmd == "search":
        jelly_sync.search(args.query)
        return

    if args.cmd == "download":
        jelly_sync.download_item(args.item_id)
        return


if __name__ == "__main__":
    main()
