import sqlite3
from pathlib import Path
from typing import Optional, List, Tuple

from .local_git import TrunkSettings, FlowSettings


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

    def init_db(self, trunks: dict, flows: dict):
        """
        trunks: mapping name -> TrunkSettings
        flows: mapping name -> FlowSettings
        """
        conn = self.connect()
        cur = conn.cursor()

        cur.executescript(
            """
        CREATE TABLE IF NOT EXISTS trunks (
            name TEXT PRIMARY KEY,
            allow_push INTEGER NOT NULL,
            require_pr INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS flows (
            name TEXT PRIMARY KEY,
            prefix TEXT NOT NULL,
            parent TEXT NOT NULL,
            target TEXT NOT NULL,
            FOREIGN KEY(parent) REFERENCES trunks(name),
            FOREIGN KEY(target) REFERENCES trunks(name)
        );
        """
        )

        # insert defaults
        for name, t in trunks.items():
            cur.execute(
                "INSERT OR REPLACE INTO trunks (name, allow_push, require_pr) VALUES (?, ?, ?)",
                (t.name, int(t.allow_push), int(t.require_pr)),
            )

        for name, f in flows.items():
            cur.execute(
                "INSERT OR REPLACE INTO flows (name, prefix, parent, target) VALUES (?, ?, ?, ?)",
                (name, f.prefix, f.parent, f.target),
            )

        conn.commit()

    # -------------------------
    # trunks API
    # -------------------------
    def add_trunk(self, t: TrunkSettings):
        conn = self.connect()
        conn.execute(
            "INSERT OR REPLACE INTO trunks (name, allow_push, require_pr) VALUES (?, ?, ?)",
            (t.name, int(t.allow_push), int(t.require_pr)),
        )
        conn.commit()

    def get_trunk(self, name: str) -> Optional[TrunkSettings]:
        conn = self.connect()
        r = conn.execute(
            "SELECT name, allow_push, require_pr FROM trunks WHERE name = ?", (name,)
        ).fetchone()
        if r:
            return TrunkSettings(
                r["name"], bool(r["allow_push"]), bool(r["require_pr"])
            )
        return None

    def list_trunks(self) -> List[TrunkSettings]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT name, allow_push, require_pr FROM trunks"
        ).fetchall()
        return [
            TrunkSettings(r["name"], bool(r["allow_push"]), bool(r["require_pr"]))
            for r in rows
        ]

    # -------------------------
    # flows API
    # -------------------------
    def add_flow(self, name: str, f: FlowSettings):
        conn = self.connect()
        conn.execute(
            "INSERT OR REPLACE INTO flows (name, prefix, parent, target) VALUES (?, ?, ?, ?)",
            (name, f.prefix, f.parent, f.target),
        )
        conn.commit()

    def get_flow(self, name: str) -> Optional[FlowSettings]:
        conn = self.connect()
        r = conn.execute(
            "SELECT prefix, parent, target FROM flows WHERE name = ?", (name,)
        ).fetchone()
        if r:
            return FlowSettings(r["prefix"], r["parent"], r["target"])
        return None

    def list_flows(self) -> List[Tuple[str, FlowSettings]]:
        conn = self.connect()
        rows = conn.execute("SELECT name, prefix, parent, target FROM flows").fetchall()
        return [
            (r["name"], FlowSettings(r["prefix"], r["parent"], r["target"]))
            for r in rows
        ]

    def detect_flow_for_branch(self, branch: str) -> Optional[Tuple[str, FlowSettings]]:
        """
        Returns (flow_name, FlowSettings) for the first matching prefix,
        or None.
        """
        conn = self.connect()
        rows = conn.execute("SELECT name, prefix, parent, target FROM flows").fetchall()
        for r in rows:
            prefix = r["prefix"]
            if branch.startswith(prefix):
                return (r["name"], FlowSettings(r["prefix"], r["parent"], r["target"]))
        return None
