import asyncio
import logging
import time
import typing as t

from plexapi.myplex import MyPlexAccount
from pypresence import AioPresence

log = logging.getLogger(__name__)


class PlexDiscordRichPresence(AioPresence):

    def __init__(
        self,
        server: str,
        username: str,
        password: t.Optional[str] = None,
        token: t.Optional[str] = None,
        client_id: str = '741382142730305587'
    ) -> None:
        super().__init__(client_id=client_id, loop=asyncio.get_event_loop())

        self.server = server
        self.username = username

        if not password and not token:
            raise RuntimeError('Password and token are both empty! Please provide at least one.')

        self.password = password
        self.token = token

        self.plex_account = None
        self.plex_server = None

        self._prev_state = None
        self._prev_session_key = None
        self._prev_rating_key = None

        self.connected = asyncio.Event()

    async def connect(self) -> None:
        while True:
            try:
                if self.token:
                    self.plex_account = MyPlexAccount(self.username, token=self.token)
                else:
                    self.plex_account = MyPlexAccount(self.username, self.password)

                log.info(f'Logged into Plex as {self.username}.')

                self.plex_server = self.plex_account.resource(self.server).connect()
                log.info(f'Connected to Plex {self.server} server.')
                break

            except Exception as err:
                log.error(f'Failed to connect to Plex: {err}')
                log.debug('Attempting reconnection in 10 seconds..')

                await asyncio.sleep(10)

        log.debug('Attempting to open IPC connection to Discord..')
        await super().connect()
        log.info('IPC connection established to Discord.')

        self.connected.set()

    async def clear_presence(self) -> None:
        self._prev_state = None
        self._prev_session_key = None
        self._prev_rating_key = None

        await self.update(details='Nothing is playing', large_text='Plex', large_image='plex')

    async def process_alert(self, data: t.Dict) -> None:
        await self.connected.wait()

        if not data.get('type') == 'playing':
            return

        if not (session_data := data.get('PlaySessionStateNotification')):
            return

        session_data = session_data[0]

        state = session_data.get('state', 'stopped')
        session_key = session_data.get('sessionKey', None)
        rating_key = session_data.get('ratingKey', None)
        view_offset = session_data.get('viewOffset', 0)

        is_admin = self.plex_account.email == self.plex_server.myPlexUsername or \
            self.plex_account.username == self.plex_server.myPlexUsername

        if session_key is None or not session_key.isdigit():
            return

        rating_key = int(rating_key)

        # Clear presence if session is stopped
        if (
            state == 'stopped' and
            self._prev_session_key == session_key and
            self._prev_rating_key == rating_key
        ):
            await self.clear_presence()

        elif state == 'stopped':
            return

        # If user is admin, ensure the alert is for the current user
        if is_admin:
            for session in self.plex_server.sessions():
                if session.sessionKey == session_key:

                    if session.usernames[0].lower() == self.username.lower():
                        break
                    return

        # Skip if nothing has changed
        if (
            self._prev_state == state and
            self._prev_session_key == session_key and
            self._prev_rating_key == rating_key
        ):
            return

        # Save the session
        self._prev_state = state
        self._prev_session_key = session_key
        self._prev_rating_key = rating_key

        # Format rich presence based on media type
        metadata = self.plex_server.fetchItem(rating_key)
        media_type = metadata.type

        if media_type == 'movie':
            title = metadata.title
            subtitle = str(metadata.year)
        elif media_type == 'episode':
            title = f'{metadata.grandparentTitle} - {metadata.title}'
            subtitle = f'S{metadata.parentIndex}, E{metadata.index}'
        elif media_type == 'track':
            title = f'{metadata.grandparentTitle} - {metadata.title}'
            subtitle = metadata.parentTitle
        else:
            return

        payload = {
            'details': title,
            'state': subtitle,
            'large_text': 'Plex',
            'large_image': 'plex'
        }

        if state == 'playing':
            current_time = int(time.time())
            start_time = current_time - view_offset / 1000

            payload['start'] = start_time

        await self.update(**payload)

    async def set_presence(self) -> None:
        await self.connected.wait()

        def sync_alert_processor(data: t.Dict) -> None:
            self.loop.run_until_complete(self.process_alert(data))

        log.debug('Starting Plex alert listener..')
        self.plex_server.startAlertListener(sync_alert_processor)

    async def start(self) -> None:
        await self.connect()
        await self.set_presence()

    def run(self) -> None:
        self.loop.run_until_complete(self.start())

        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            log.info('Stopping Plex Discord Rich Presence..')
        finally:
            self.close()
