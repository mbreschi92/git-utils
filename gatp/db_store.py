import sqlite3
from pathlib import Path
from typing import Optional, List, Tuple

from .local_git import TrunkSettings, FlowSettings, BindSettings


class DBStore:
    """
    DBStore manages a sqlite DB stored in REPO_ROOT/.gitflow/config.db.
    It also ensures that .gitflow/ is present in the repo .gitignore.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)
        self.dir = self.repo_root / ".gitflow"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.dir / "config.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_ignored()

    def _ensure_ignored(self):
        gitignore = self.repo_root / ".gitignore"
        line = ".gitflow/\n"
        if not gitignore.exists():
            # create .gitignore and add the line
            gitignore.write_text(line)
            return
        content = gitignore.read_text()
        if ".gitflow/" not in content:
            # append line
            with gitignore.open("a") as fh:
                if not content.endswith("\n"):
                    fh.write("\n")
                fh.write(line)

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_file)
            # use row factory for easier access
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def is_initialized(self) -> bool:
        return self.db_file.exists()

    def init_db(self, trunks: dict, flows: dict, binds: dict):
        """
        trunks: mapping name -> TrunkSettings
        flows: mapping name -> FlowSettings
        binds: mapping name -> BindSettings
        """
        conn = self.connect()
        cur = conn.cursor()

        cur.executescript(
            """
        CREATE TABLE IF NOT EXISTS trunks (
            name TEXT PRIMARY KEY,
            allow_push INTEGER NOT NULL,
            require_pr INTEGER NOT NULL,
            deprecated BOOLEAN DEFAULT FALSE,
            default_branch BOOLEAN DEFAULT FALSE,
            sync_with TEXT  -- JSON list, es. '["release", "hotfix"]'
        );

        CREATE TABLE IF NOT EXISTS flows (
            name TEXT PRIMARY KEY,
            prefix TEXT NOT NULL,
            parent TEXT NOT NULL,
            target TEXT NOT NULL,
            max_lifetime_days INTEGER DEFAULT NULL,
            allow_push INTEGER NOT NULL DEFAULT 0,
            require_pr INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(parent) REFERENCES trunks(name),
            FOREIGN KEY(target) REFERENCES trunks(name)
        );

        CREATE TABLE IF NOT EXISTS binds (
            name TEXT PRIMARY KEY,
            parent TEXT NOT NULL,
            target TEXT NOT NULL,
            mode TEXT NOT NULL,
            tag INTEGER NOT NULL,
            conflict_policy TEXT DEFAULT "block",  -- "block", "notify", "resolve_ours", "resolve_theirs"
            schedule TEXT DEFAULT "on_push"  -- "daily", "weekly", "on_push"
            FOREIGN KEY(parent) REFERENCES trunks(name),
            FOREIGN KEY(target) REFERENCES trunks(name)
        );

        CREATE TABLE IF NOT EXISTS logger (
            id INTEGER PRIMARY KEY,
            timestamp DATETIME,
            user TEXT,
            level TEXT,
            message TEXT
        );
        """
        )

        # insert defaults
        for name, t in trunks.items():
            cur.execute(
                "INSERT OR REPLACE INTO trunks (name, allow_push, require_pr, deprecated, default_branch, sync_with) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    t.name,
                    int(t.allow_push),
                    int(t.require_pr),
                    int(t.deprecated),
                    int(t.default_branch),
                    t.sync_with,
                ),
            )

        for name, f in flows.items():
            cur.execute(
                "INSERT OR REPLACE INTO flows (name, prefix, parent, target, max_lifetime_days, allow_push, require_pr) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    f.prefix,
                    f.parent,
                    f.target,
                    f.max_lifetime_days,
                    int(f.allow_push),
                    int(f.require_pr),
                ),
            )

        for name, b in binds.items():
            cur.execute(
                "INSERT OR REPLACE INTO binds (name, parent, target, mode, tag, conflict_policy, schedule) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    b.parent,
                    b.target,
                    b.mode,
                    b.tag,
                    b.conflict_policy,
                    b.schedule,
                ),
            )

        conn.commit()

    # -------------------------
    # trunks API
    # -------------------------
    def add_trunk(self, t: TrunkSettings):
        conn = self.connect()
        conn.execute(
            "INSERT OR REPLACE INTO trunks (name, allow_push, require_pr, deprecated, default_branch, sync_with) VALUES (?, ?, ?, ?, ?, ?)",
            (
                t.name,
                int(t.allow_push),
                int(t.require_pr),
                int(t.deprecated),
                int(t.default_branch),
                t.sync_with,
            ),
        )
        conn.commit()

    def get_trunk(self, name: str) -> Optional[TrunkSettings]:
        conn = self.connect()
        r = conn.execute(
            "SELECT name, allow_push, require_pr, deprecated, default_branch, sync_with FROM trunks WHERE name = ?",
            (name,),
        ).fetchone()
        if r:
            return TrunkSettings(
                r["name"],
                bool(r["allow_push"]),
                bool(r["require_pr"]),
                bool(r["deprecated"]),
                bool(r["default_branch"]),
                r["sync_with"],
            )
        return None

    def list_trunks(self) -> List[TrunkSettings]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT name, allow_push, require_pr, deprecated, default_branch, sync_with FROM trunks"
        ).fetchall()
        return [
            TrunkSettings(
                r["name"],
                bool(r["allow_push"]),
                bool(r["require_pr"]),
                bool(r["deprecated"]),
                bool(r["default_branch"]),
                r["sync_with"],
            )
            for r in rows
        ]

    # -------------------------
    # flows API
    # -------------------------
    def add_flow(self, name: str, f: FlowSettings):
        conn = self.connect()
        conn.execute(
            "INSERT OR REPLACE INTO flows (name, prefix, parent, target, max_lifetime_days, allow_push, require_pr) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                f.prefix,
                f.parent,
                f.target,
                f.max_lifetime_days,
                int(f.allow_push),
                int(f.require_pr),
            ),
        )
        conn.commit()

    def get_flow(self, name: str) -> Optional[FlowSettings]:
        conn = self.connect()
        r = conn.execute(
            "SELECT prefix, parent, target, max_lifetime_days, allow_push, require_pr FROM flows WHERE name = ?",
            (name,),
        ).fetchone()
        if r:
            return FlowSettings(
                r["prefix"],
                r["parent"],
                r["target"],
                r["max_lifetime_days"],
                bool(r["allow_push"]),
                bool(r["require_pr"]),
            )
        return None

    def list_flows(self) -> List[Tuple[str, FlowSettings]]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT name, prefix, parent, target, max_lifetime_days, allow_push, require_pr FROM flows"
        ).fetchall()
        return [
            (
                r["name"],
                FlowSettings(
                    r["prefix"],
                    r["parent"],
                    r["target"],
                    r["max_lifetime_days"],
                    bool(r["allow_push"]),
                    bool(r["require_pr"]),
                ),
            )
            for r in rows
        ]

    def detect_flow_for_branch(self, branch: str) -> Optional[Tuple[str, FlowSettings]]:
        """
        Returns (flow_name, FlowSettings) for the first matching prefix,
        or None.
        """
        conn = self.connect()
        rows = conn.execute(
            "SELECT name, prefix, parent, target, max_lifetime_days, allow_push, require_pr FROM flows"
        ).fetchall()
        for r in rows:
            prefix = r["prefix"]
            if branch.startswith(prefix):
                return (
                    r["name"],
                    FlowSettings(
                        r["prefix"],
                        r["parent"],
                        r["target"],
                        r["max_lifetime_days"],
                        bool(r["allow_push"]),
                        bool(r["require_pr"]),
                    ),
                )
        return None

    # -------------------------
    # binds API
    # -------------------------
    def add_bind(self, b: BindSettings):
        conn = self.connect()
        conn.execute(
            "INSERT OR REPLACE INTO binds (name, parent, target, mode, tag, conflict_policy, schedule) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                b.name,
                b.parent,
                b.target,
                b.mode,
                int(b.tag),
                b.conflict_policy,
                b.schedule,
            ),
        )
        conn.commit()

    def get_bind(self, name: str) -> Optional[BindSettings]:
        conn = self.connect()
        r = conn.execute(
            "SELECT parent, target, mode, tag, conflict_policy, schedule FROM binds WHERE name = ?",
            (name,),
        ).fetchone()
        if r:
            return BindSettings(
                name,
                r["parent"],
                r["target"],
                r["mode"],
                bool(r["tag"]),
                r["conflict_policy"],
                r["schedule"],
            )
        return None

    def list_binds(self) -> List[BindSettings]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT name, parent, target, mode, tag, conflict_policy, schedule FROM binds"
        ).fetchall()
        return [
            BindSettings(
                r["name"],
                r["parent"],
                r["target"],
                r["mode"],
                bool(r["tag"]),
                r["conflict_policy"],
                r["schedule"],
            )
            for r in rows
        ]
