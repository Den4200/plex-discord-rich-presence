import asyncio
import logging
import typing as t

from plexapi.myplex import MyPlexAccount
from pypresence import AioPresence

log = logging.getLogger(__name__)


class PlexDiscordRichPresence(AioPresence):

    def __init__(
        self,
        username: str,
        password: t.Optional[str] = None,
        token: t.Optional[str] = None,
        client_id: str = '741382142730305587'
    ) -> None:
        super().__init__(client_id=client_id, loop=asyncio.get_event_loop())

        self.username = username

        if not password and not token:
            raise RuntimeError('Password and token are both empty! Please provide at least one.')

        self.password = password
        self.token = token

        self.plex_account = None

        self.connected = asyncio.Event()

    async def connect(self) -> None:
        while True:
            try:
                if self.token:
                    self.plex_account = MyPlexAccount(self.username, token=self.token)
                else:
                    self.plex_account = MyPlexAccount(self.username, self.password)

                log.info(f'Logged into Plex as {self.username}.')
                break

            except Exception as err:
                log.error(f'Failed to connect to Plex: {err}')
                log.debug('Attempting reconnection in 10 seconds..')

                await asyncio.sleep(10)

        log.debug('Attempting to open IPC connection to Discord..')
        await super().connect()
        log.info('IPC connection established to Discord.')

        self.connected.set()

    def run(self) -> None:
        self.loop.run_until_complete(self.connect())
