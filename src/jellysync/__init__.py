#!/usr/bin/env python3
import argparse
import json

from .jellysync import JellySync


def main():
    parser = argparse.ArgumentParser()

    conf_group = parser.add_mutually_exclusive_group()
    conf_group.add_argument("--config", help="The config name to use from ~/.jellysync")
    conf_group.add_argument("--host", help="The Jellyfin host URL")

    auth_group = parser.add_mutually_exclusive_group()
    auth_group.add_argument("--user", help="The User name, e.g. jellyfin")
    auth_group.add_argument("--token", help="The Jellyfin API key")

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

    info_parser = subparsers.add_parser("info")
    info_parser.set_defaults(cmd="info")
    info_parser.add_argument("item-id", help="The Jellyfin item ID")

    search_parser = subparsers.add_parser("search")
    search_parser.set_defaults(cmd="search")
    search_parser.add_argument("query", help="The search query")

    download_parser = subparsers.add_parser("download")
    download_parser.set_defaults(cmd="download")
    download_parser.add_argument("item-id", help="The Jellyfin item ID")

    args = parser.parse_args()

    if args.host:
        if args.token:
            if args.user_id is None:
                parser.error("--user-id is required if --token is used")
            jelly_sync = JellySync(
                args.host,
                args.token,
                args.user_id,
                media_dir=args.media_dir,
                use_content_disposition=args.use_content_disposition,
                dry_run=args.dry_run,
                debug=args.debug,
            )
        else:
            if args.user is None:
                parser.error("--user is required if using password authentication")
            jelly_sync = JellySync.login(
                args.host,
                args.user,
                media_dir=args.media_dir,
                use_content_disposition=args.use_content_disposition,
                dry_run=args.dry_run,
                debug=args.debug,
            )
    else:
        jelly_sync = JellySync.load(
            args.config,
            media_dir=args.media_dir,
            use_content_disposition=args.use_content_disposition,
            dry_run=args.dry_run,
            debug=args.debug,
        )

    if args.cmd == "info":
        print(json.dumps(jelly_sync.get_item(args.item_id)))

    if args.cmd == "search":
        jelly_sync.search(args.query)

    if args.cmd == "download":
        jelly_sync.download_item(args.item_id)


if __name__ == "__main__":
    main()
