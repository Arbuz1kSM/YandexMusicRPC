from __future__ import annotations

import unittest

from media.windows_media import WindowsMediaSource


class Status:
    def __init__(self, name):
        self.name = name


class Playback:
    def __init__(self, name):
        self.playback_status = Status(name)


class Session:
    def __init__(self, sid, state):
        self.source_app_user_model_id = sid
        self.state = state

    def get_playback_info(self):
        return Playback(self.state)


class Manager:
    def __init__(self, sessions, current):
        self.sessions = sessions
        self.current = current

    def get_sessions(self):
        return self.sessions

    def get_current_session(self):
        return self.current


class SessionSelectionTests(unittest.TestCase):
    def test_prefers_playing_yandex_session_over_stale_current(self) -> None:
        stale = Session("ru.yandex.desktop.music", "paused")
        live = Session("ru.yandex.desktop.music", "playing")
        source = WindowsMediaSource(["yandex"])
        source._manager = Manager([stale, live], stale)
        self.assertIs(source._select_session(), live)

    def test_keeps_current_when_current_is_playing(self) -> None:
        current = Session("ru.yandex.desktop.music", "playing")
        other = Session("ru.yandex.desktop.music", "playing")
        source = WindowsMediaSource(["yandex"])
        source._manager = Manager([other, current], current)
        self.assertIs(source._select_session(), current)


if __name__ == "__main__":
    unittest.main()
