from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from typing import TypedDict, cast
from urllib.parse import urlparse

import httpx
import toml
import tomllib
from rich.prompt import Confirm, Prompt


class User(TypedDict):
    Name: str
    Id: str


class AuthenticationResponse(TypedDict):
    User: User
    AccessToken: str


@dataclass
class JellySyncConfig:
    host: str
    user_id: str
    token: str
    media_dir: str | None


@dataclass
class ServerConfig:
    host: str
    user_id: str
    token: str


@dataclass
class JellySyncConfigs:
    default: str | None = None
    media_dir: str | None = None
    configs: dict[str, ServerConfig] = field(default_factory=dict)

    @staticmethod
    def load() -> JellySyncConfigs:
        config_file = os.path.expanduser("~/.jellysync")

        if not os.path.exists(config_file):
            return JellySyncConfigs()

        with open(config_file, "rb") as fp:
            data = tomllib.load(fp)

        default = None
        media_dir = None
        configs = {}
        for key, value in data.items():
            if key == "default":
                default = value
            if key == "media_dir":
                media_dir = value
            if isinstance(value, dict):
                configs[key] = ServerConfig(
                    host=value["host"], user_id=value["user_id"], token=value["token"]
                )

        return JellySyncConfigs(default=default, media_dir=media_dir, configs=configs)

    def resolve(
        self, parser: argparse.ArgumentParser, args: argparse.Namespace
    ) -> JellySyncConfig:
        host, user_id, token, media_dir = None, None, None, self.media_dir
        name = args.config or self.default

        if name is not None:
            config = self.configs[name]
            host, user_id, token = config.host, config.user_id, config.token

        if args.host:
            host = args.host
        if args.user_id:
            user_id = args.user_id
        if args.token:
            token = args.token
        if args.media_dir:
            media_dir = args.media_dir

        if host is None:
            parser.error("--host is required")
        if user_id is None:
            parser.error("--user-id is required")
        if token is None:
            parser.error("--token is required")

        return JellySyncConfig(host, user_id, token, media_dir)

    def configure(
        self,
        *,
        host: str | None = None,
        user: str | None = None,
        name: str | None = None,
    ):
        if host is None:
            host = Prompt.ask("Enter Jellyfin server URL")
        hostname = urlparse(host).hostname
        if hostname is None:
            raise Exception(f"Failed to parse hostname from URL: {host}")
        if user is None:
            user = Prompt.ask("Enter login")
        passwd = Prompt.ask("Enter password", password=True)

        # Build auth params and return connection details
        resp = httpx.post(
            f"{host}/Users/authenticatebyname",
            json={"Username": user, "Pw": passwd},
            headers={
                "Authorization": 'MediaBrowser Client="JellySync", Device="JellySync", DeviceId="SmVsbHlTeW5j", Version="0.1.3"'
            },
        )
        resp.raise_for_status()
        auth = cast(AuthenticationResponse, resp.json())

        if name is None:
            for part in hostname.split("."):
                if part != "jellyfin" and len(part) > 3:
                    name = Prompt.ask(
                        "Enter a name for this configuration", default=part
                    )
                    break
            else:
                name = Prompt.ask("Enter a name for this configuration")
        self.configs[name] = ServerConfig(host, auth["User"]["Id"], auth["AccessToken"])

        is_default = Confirm.ask(f"Make {name} the default Jellyfin server?")
        if is_default:
            self.default = name

    def save(self):
        output = {}
        if self.default is not None:
            output["default"] = self.default
        if self.media_dir is not None:
            output["media_dir"] = self.media_dir
        for key, value in self.configs.items():
            output[key] = {
                "host": value.host,
                "user_id": value.user_id,
                "token": value.token,
            }
        config_file = os.path.expanduser("~/.jellysync")
        with open(config_file, "w") as fp:
            toml.dump(output, fp)
