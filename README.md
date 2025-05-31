# JellySync

Provides an easy to use mechanism to sync content from a remote Jellyfin server to a local Jellyfin server.

## Installation

```
uv tool install git+https://github.com/niwako/jellysync
```

## Usage

### Login

```sh
jellysync login
```

```
Enter Jellyfin server URL: https://jellyfin.coolness.mydomain.com
Enter login: user
Enter password: <type your password>
Enter a name for this configuration (coolness):
Make coolness the default Jellyfin server? [y/n]: y
```

### Search Library

```sh
jellysync --config coolness search 'query'
```

### Sync Content

```sh
jellysync --config coolness download <hashid>
```

## Bash / Zsh Autocomplete

1. Install argcomplete

   ```sh
   uv tool install argcomplete
   ```

1. Add the following to your .bashrc / .zshrc:

   ```sh
   eval "$(register-python-argcomplete jellysync)"
   ```
