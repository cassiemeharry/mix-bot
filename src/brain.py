import random
import sqlite3

class PickingError(ValueError):
    def __init__(self, needed_classes):
        self.needed_classes = needed_classes

    def __str__(self):
        n = len(self.needed_classes)
        if n == 1:
            return 'Need %s' % self.needed_classes[0]
        elif n == 2:
            return 'Need %s and %s' % (self.needed_classes[0], self.needed_classes[1])
        else:
            return 'Need %s, and %s' % (', '.join(self.needed_classes[:-1]), self.needed_classes[-1])

class BaseBotBrain(object):
    def __init__(self, settings):
        self.settings = settings
        self.dispatcher = None
        self.can_pick_cache = False
        self._setup()

    def _setup(self):
        pass

    def random_pick(self, deterministic=False):
        """Returns a random picking or throw a PickingError if picking is impossible.

        Returns: {'team': {'player name': 'class'}}
        """
        by_player = self.classes_by_player()
        by_class = {}
        for cls in self.settings['rules']['valid classes']:
            by_class[cls] = []
            for p in by_player:
                if cls in by_player[p]:
                    by_class[cls].append(p)

        classes = [
            cls for cls, _ in sorted(
                by_class.items(),
                key=lambda pair: len(pair[1]),
            )
        ]

        red, blu = {}, {}
        needed = []
        for cls in classes:
            limit = 2*self.settings['rules']['class limits'][cls]
            if len(by_class[cls]) < limit:
                needed.append(cls)
                continue
            for i in range(limit):
                # Remove player p from each class they signed up for
                if deterministic:
                    p = by_class[cls][0]
                else:
                    p = random.choice(by_class[cls])
                by_class[cls].remove(p)
                by_player[p].remove(cls)
                (red, blu)[i%2][p] = cls
                for player_class in by_player[p]:
                    by_class[player_class].remove(p)

        if needed:
            needed.sort(key=lambda cls: self.settings['rules']['valid classes'].index(cls))
            raise PickingError(needed)

        return {'red': red, 'blu': blu}

    def can_pick(self):
        """Returns True/False whether picking can start"""
        try:
            result = self.random_pick(deterministic=True)
            if not self.can_pick_cache:
                self.notice_can_pick()
                self.can_pick_cache = True
        except PickingError:
            if self.can_pick_cache:
                self.notice_cannot_pick()
                self.can_pick_cache = False

        return self.can_pick_cache

    def classes_needed(self):
        try:
            self.random_pick(deterministic=True)
            return 'No classes needed'
        except PickingError as e:
            return str(e)

    def notice_can_pick(self):
        self.dispatcher.queue_message('Picking can start at any time (try !pick)')

    def notice_cannot_pick(self):
        self.dispatcher.queue_message('Picking may no longer start')

class SqliteBotBrain(BaseBotBrain):
    def _get_cursor(self):
        return self._conn.cursor()

    def _setup(self):
        self._conn = sqlite3.connect(self.settings['database']['name'])
        self._conn.isolation_level = None # Autocommit level
        c = self._get_cursor()

        # Create the initial tables
        c.execute("""\
        CREATE TABLE IF NOT EXISTS player (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE ON CONFLICT IGNORE
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS player_pug_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            class TEXT,
            FOREIGN KEY(player_id) REFERENCES player(id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS players_added (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            class TEXT,
            FOREIGN KEY(player_id) REFERENCES player(id)
        )
        """)

        # When the bot starts up, reset the picking process (because
        # players may have left since they added)
        c.execute("DELETE FROM players_added")
        self.can_pick()

    def _player_id_from_name(self, nickname):
        c = self._get_cursor()
        c.execute("SELECT id FROM player WHERE name = ?", (nickname,))
        row = c.fetchone()
        if row is None:
            c.execute("INSERT INTO player (name) VALUES (?)", (nickname,))
            player_id = c.lastrowid
        else:
            player_id = row[0]

        return player_id

    def _player_names_from_ids(self, ids):
        if not ids:
            return {}
        c = self._get_cursor()
        query = "SELECT id, name FROM player WHERE %s" % ' OR '.join('id = ?' for _ in ids)
        c.execute(query, ids)
        return {id: name for id, name in c.fetchall()}

    # Any method that does any kind of state change should call
    # self.can_check() afterward to notify changes in the picking
    # status.
    def player_set_added_classes(self, nickname, classes):
        c = self._get_cursor()
        player_id = self._player_id_from_name(nickname)
        c.execute("DELETE FROM players_added WHERE player_id = ?", (player_id,))
        for class_name in classes:
            c.execute("INSERT INTO players_added (player_id, class) VALUES (?, ?)", (player_id, class_name))
        self.can_pick()

    def player_remove(self, nickname):
        player_id = self._player_id_from_name(nickname)
        c = self._get_cursor()
        c.execute("DELETE FROM players_added WHERE player_id = ?", (player_id,))
        self.can_pick()

    def player_changed_name(self, old_nick, new_nick):
        c = self._get_cursor()
        c.execute("UPDATE OR IGNORE SET name = ? WHERE name = ?", (new_nick, old_nick))
        return True

    def players_added(self):
        c = self._get_cursor()
        c.execute("SELECT player_id FROM players_added")
        rows = c.fetchall()
        player_ids = [pid for (pid,) in rows]
        players_by_id = self._player_names_from_ids(player_ids)
        return sorted(players_by_id.values())

    def players_by_class(self):
        c = self._get_cursor()
        c.execute("SELECT player_id FROM players_added")
        rows = c.fetchall()
        player_ids = [pid for (pid,) in rows]
        players_by_id = self._player_names_from_ids(player_ids)

        by_class = {}
        for player_id, cls in c.execute("SELECT player_id, class FROM players_added"):
            by_class.setdefault(cls, [])
            by_class[cls].append(players_by_id[player_id])
            by_class[cls].sort()

        return by_class

    def classes_by_player(self):
        c = self._get_cursor()
        c.execute("SELECT player_id FROM players_added")
        rows = c.fetchall()
        player_ids = [pid for (pid,) in rows]
        players_by_id = self._player_names_from_ids(player_ids)

        by_player = {}
        for player_id, cls in c.execute("SELECT player_id, class FROM players_added"):
            name = players_by_id[player_id]
            by_player.setdefault(name, [])
            by_player[name].append(cls)
            by_player[name].sort(key=lambda cls: self.settings['rules']['valid classes'].index(cls))
        return by_player


def make_brain(settings):
    db_type = settings['database']['type']

    return {
        'sqlite': SqliteBotBrain,
    }[db_type](settings)
