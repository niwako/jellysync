#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse
import asyncio
import importlib.metadata
import json
import signal
import sys

import argcomplete

from .config import JellySyncConfigs
from .jellysync import JellySync


def signal_handler(sig, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


async def run():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {importlib.metadata.version('jellysync')}",
        help="show jellysync version number and exit",
    )

    parser.add_argument("--config", help="config name to use from ~/.jellysync")
    parser.add_argument("--host", help="Jellyfin host URL")
    parser.add_argument("--token", help="Jellyfin API key")
    parser.add_argument("--user-id", help="User ID")
    parser.add_argument("--media-dir", help="output folder, e.g. /mnt/media")

    parser.add_argument(
        "--dry-run",
        help="dry run without downloading",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        help="print HTTP requests and responses to and from Jellyfin server",
        action="store_true",
    )

    subparsers = parser.add_subparsers(title="commands", dest="cmd")

    login_parser = subparsers.add_parser("login")
    login_parser.add_argument("--name", help="name of the configuration")
    login_parser.add_argument("--host", help="Jellyfin host URL")
    login_parser.add_argument("--user", help="user name, e.g. jellyfin")
    login_parser.add_argument("--media-dir", help="output folder, e.g. /mnt/media")

    info_parser = subparsers.add_parser("info")
    info_parser.add_argument("item_id", help="Jellyfin item ID")

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument(
        "--movie", dest="types", action="append_const", const="Movie"
    )
    list_parser.add_argument(
        "--series", dest="types", action="append_const", const="Series"
    )
    list_parser.add_argument(
        "--episode", dest="types", action="append_const", const="Episode"
    )

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query", help="search query")
    search_parser.add_argument(
        "--movie", dest="types", action="append_const", const="Movie"
    )
    search_parser.add_argument(
        "--series", dest="types", action="append_const", const="Series"
    )
    search_parser.add_argument(
        "--episode", dest="types", action="append_const", const="Episode"
    )

    download_parser = subparsers.add_parser("download")
    download_parser.add_argument("item_id", help="Jellyfin item ID")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.cmd is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

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
        dry_run=args.dry_run,
        debug=args.debug,
    )

    if args.cmd == "info":
        item = await jelly_sync.get_item(args.item_id)
        print(json.dumps(item))
        return

    if args.cmd == "list":
        types = ["Movie", "Series"] if args.types is None else args.types
        await jelly_sync.search("", types)
        return

    if args.cmd == "search":
        types = ["Movie", "Series", "Episode"] if args.types is None else args.types
        await jelly_sync.search(args.query, types)
        return

    if args.cmd == "download":
        await jelly_sync.download_item(args.item_id)
        return


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
