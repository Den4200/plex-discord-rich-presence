from pathlib import Path

import yaml

from plex_drp.rich_presence import PlexDiscordRichPresence


def main() -> None:
    if not (config_path := Path('config.yml')).exists():
        raise RuntimeError('Missing config.yml file!')

    with open(config_path, 'r') as f:
        config = yaml.load(f, Loader=yaml.Loader)

    pdrp = PlexDiscordRichPresence(**config['plex_drp'])
    pdrp.run()


if __name__ == "__main__":
    main()
