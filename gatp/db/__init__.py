from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, Trunk, Flow, Bind, Log, User


class DBStore:
    def __init__(self, db_path: str = ".gatp/config.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)

    def open(self):
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def close(self):
        self.session.close()

    def is_initialized(self) -> bool:
        # check if tables exist
        self.open()
        inspector = self.engine.inspect(self.engine)
        tables = inspector.get_table_names()
        self.close()
        required_tables = {"trunks", "flows", "binds", "logger"}
        return required_tables.issubset(set(tables))

    ### ADD METHODS TO ADD/GET trunks, flows, binds, ... ###
    def add_trunk(self, **kwargs):
        self.open()
        trunk = Trunk(**kwargs)
        self.session.add(trunk)
        self.session.commit()
        self.close()

    def add_flow(self, **kwargs):
        self.open()
        flow = Flow(**kwargs)
        self.session.add(flow)
        self.session.commit()
        self.close()

    def add_bind(self, **kwargs):
        self.open()
        bind = Bind(**kwargs)
        self.session.add(bind)
        self.session.commit()
        self.close()

    def add_log(self, **kwargs):
        self.open()
        log = Log(**kwargs)
        self.session.add(log)
        self.session.commit()
        self.close()

    def add_user(self, **kwargs):
        self.open()
        user = User(**kwargs)
        self.session.add(user)
        self.session.commit()
        self.close()

    ### GET METHODS FOR trunks, flows, binds, logs, ... ###
    def get_trunks(self, filter_by: dict = None):
        self.open()
        if filter_by:
            out = self.session.query(Trunk).filter_by(**filter_by).all()
        else:
            out = self.session.query(Trunk).all()
        self.close()
        return out

    def get_flows(self, filter_by: dict = None):
        self.open()
        if filter_by:
            out = self.session.query(Flow).filter_by(**filter_by).all()
        else:
            out = self.session.query(Flow).all()
        self.close()
        return out

    def get_binds(self, filter_by: dict = None):
        self.open()
        if filter_by:
            out = self.session.query(Bind).filter_by(**filter_by).all()
        else:
            out = self.session.query(Bind).all()
        self.close()
        return out

    def get_logs(self, filter_by: dict = None):
        self.open()
        if filter_by:
            out = self.session.query(Log).filter_by(**filter_by).all()
        else:
            out = self.session.query(Log).all()
        self.close()
        return out

    def get_users(self, filter_by: dict = None):
        self.open()
        if filter_by:
            out = self.session.query(User).filter_by(**filter_by).all()
        else:
            out = self.session.query(User).all()
        self.close()
        return out

    ### DELETE METHODS FOR trunks, flows, binds, logs, users ... ###
    def delete_trunk(self, name: str):
        self.open()
        self.session.query(Trunk).filter_by(name=name).delete()
        self.session.commit()
        self.close()

    def delete_flow(self, name: str):
        self.open()
        self.session.query(Flow).filter_by(name=name).delete()
        self.session.commit()
        self.close()

    def delete_bind(self, name: str):
        self.open()
        self.session.query(Bind).filter_by(name=name).delete()
        self.session.commit()
        self.close()

    def delete_user(self, name: str):
        self.open()
        self.session.query(User).filter_by(name=name).delete()
        self.session.commit()
        self.close()


# # Previous sqlite3-based implementation (to be removed)

# import sqlite3
# from pathlib import Path
# from typing import Optional, List, Tuple
# from dataclasses import dataclass


# @dataclass
# class Trunk:
#     name: str
#     allow_push: bool
#     require_pr: bool
#     deprecated: bool = False
#     default_branch: bool = False
#     sync_with: list[str] = None


# @dataclass
# class Flow:
#     prefix: str
#     parent: str
#     target: str | list[str]
#     max_lifetime_days: Optional[int] = None
#     auto_delete: bool = False
#     allow_push: bool = True
#     require_pr: bool = False


# @dataclass
# class Bind:
#     name: str
#     parent: str
#     target: str | list[str]
#     mode: str = "merge"  # "merge", "rebase", "aggregate"
#     tag: bool = True
#     conflict_policy: str = (
#         "block"  # "block", "notify", "resolve_ours", "resolve_theirs"
#     )
#     schedule: str = "on_push"  # "daily", "weekly", "on_push"


# class DBStore:
#     """
#     DBStore manages a sqlite DB stored in REPO_ROOT/.gatp/config.db.
#     It also ensures that .gatp/ is present in the repo .gitignore.
#     """

#     def __init__(self, repo_root: Path):
#         self.repo_root = Path(repo_root)
#         self.dir = self.repo_root / ".gatp"
#         self.dir.mkdir(parents=True, exist_ok=True)
#         self.db_file = self.dir / "config.db"
#         self._conn: Optional[sqlite3.Connection] = None
#         self._ensure_ignored()

#     def _ensure_ignored(self):
#         gitignore = self.repo_root / ".gitignore"
#         line = ".gatp/\n"
#         if not gitignore.exists():
#             # create .gitignore and add the line
#             gitignore.write_text(line)
#             return
#         content = gitignore.read_text()
#         if ".gatp/" not in content:
#             # append line
#             with gitignore.open("a") as fh:
#                 if not content.endswith("\n"):
#                     fh.write("\n")
#                 fh.write(line)

#     def connect(self):
#         if self._conn is None:
#             self._conn = sqlite3.connect(self.db_file)
#             # use row factory for easier access
#             self._conn.row_factory = sqlite3.Row
#         return self._conn

#     def is_initialized(self) -> bool:
#         return self.db_file.exists()

#     def init_db(self, trunks: dict, flows: dict, binds: dict):
#         """
#         trunks: mapping name -> Trunk
#         flows: mapping name -> Flow
#         binds: mapping name -> Bind
#         """
#         conn = self.connect()
#         cur = conn.cursor()

#         cur.executescript(
#             """
#         CREATE TABLE IF NOT EXISTS trunks (
#             name TEXT PRIMARY KEY,
#             allow_push BOOLEAN NOT NULL DEFAULT FALSE,
#             require_pr BOOLEAN NOT NULL DEFAULT TRUE,
#             deprecated BOOLEAN DEFAULT FALSE,
#             default_branch BOOLEAN DEFAULT FALSE,
#             sync_with TEXT  -- JSON list, es. '["release", "hotfix"]'
#         );

#         CREATE TABLE IF NOT EXISTS flows (
#             name TEXT PRIMARY KEY,
#             prefix TEXT NOT NULL,
#             parent TEXT NOT NULL,
#             target TEXT NOT NULL,
#             max_lifetime_days INTEGER DEFAULT NULL,
#             auto_delete BOOLEAN DEFAULT FALSE,
#             allow_push BOOLEAN NOT NULL DEFAULT FALSE,
#             require_pr BOOLEAN NOT NULL DEFAULT TRUE,
#             FOREIGN KEY(parent) REFERENCES trunks(name)
#         );

#         CREATE TABLE IF NOT EXISTS binds (
#             name TEXT PRIMARY KEY,
#             parent TEXT NOT NULL,
#             target TEXT NOT NULL,
#             mode TEXT NOT NULL,
#             tag BOOLEAN NOT NULL DEFAULT TRUE,
#             conflict_policy TEXT DEFAULT "block",  -- "block", "notify", "resolve_ours", "resolve_theirs"
#             schedule TEXT DEFAULT "on_push",  -- "daily", "weekly", "on_push"
#             FOREIGN KEY(parent) REFERENCES trunks(name)
#         );

#         CREATE TABLE IF NOT EXISTS logger (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             timestamp DATETIME,
#             user TEXT,
#             level TEXT,
#             message TEXT
#         );
#         """
#         )

#         # insert defaults
#         for name, t in trunks.items():
#             cur.execute(
#                 "INSERT OR REPLACE INTO trunks (name, allow_push, require_pr, deprecated, default_branch, sync_with) VALUES (?, ?, ?, ?, ?, ?)",
#                 (
#                     t.name,
#                     int(t.allow_push),
#                     int(t.require_pr),
#                     int(t.deprecated),
#                     int(t.default_branch),
#                     t.sync_with,
#                 ),
#             )

#         for name, f in flows.items():
#             cur.execute(
#                 "INSERT OR REPLACE INTO flows (name, prefix, parent, target, max_lifetime_days, allow_push, require_pr) VALUES (?, ?, ?, ?, ?, ?, ?)",
#                 (
#                     name,
#                     f.prefix,
#                     f.parent,
#                     f.target,
#                     f.max_lifetime_days,
#                     int(f.auto_delete),
#                     int(f.allow_push),
#                     int(f.require_pr),
#                 ),
#             )

#         for name, b in binds.items():
#             cur.execute(
#                 "INSERT OR REPLACE INTO binds (name, parent, target, mode, tag, conflict_policy, schedule) VALUES (?, ?, ?, ?, ?, ?, ?)",
#                 (
#                     name,
#                     b.parent,
#                     b.target,
#                     b.mode,
#                     b.tag,
#                     b.conflict_policy,
#                     b.schedule,
#                 ),
#             )

#         conn.commit()

#     # -------------------------
#     # trunks API
#     # -------------------------
#     def add_trunk(self, t: Trunk):
#         conn = self.connect()
#         conn.execute(
#             "INSERT OR REPLACE INTO trunks (name, allow_push, require_pr, deprecated, default_branch, sync_with) VALUES (?, ?, ?, ?, ?, ?)",
#             (
#                 t.name,
#                 int(t.allow_push),
#                 int(t.require_pr),
#                 int(t.deprecated),
#                 int(t.default_branch),
#                 t.sync_with,
#             ),
#         )
#         conn.commit()

#     def get_trunk(self, name: str) -> Optional[Trunk]:
#         conn = self.connect()
#         r = conn.execute(
#             "SELECT * FROM trunks WHERE name = ?",
#             (name,),
#         ).fetchone()
#         if r:
#             return Trunk(
#                 r["name"],
#                 bool(r["allow_push"]),
#                 bool(r["require_pr"]),
#                 bool(r["deprecated"]),
#                 bool(r["default_branch"]),
#                 r["sync_with"],
#             )
#         return None

#     def list_trunks(self) -> List[Trunk]:
#         conn = self.connect()
#         rows = conn.execute("SELECT * FROM trunks").fetchall()
#         return [
#             Trunk(
#                 r["name"],
#                 bool(r["allow_push"]),
#                 bool(r["require_pr"]),
#                 bool(r["deprecated"]),
#                 bool(r["default_branch"]),
#                 r["sync_with"],
#             )
#             for r in rows
#         ]

#     # -------------------------
#     # flows API
#     # -------------------------
#     def add_flow(self, name: str, f: Flow):
#         conn = self.connect()
#         conn.execute(
#             "INSERT OR REPLACE INTO flows (name, prefix, parent, target, max_lifetime_days, allow_push, require_pr) VALUES (?, ?, ?, ?, ?, ?, ?)",
#             (
#                 name,
#                 f.prefix,
#                 f.parent,
#                 f.target,
#                 f.max_lifetime_days,
#                 int(f.allow_push),
#                 int(f.require_pr),
#             ),
#         )
#         conn.commit()

#     def get_flow(self, name: str) -> Optional[Flow]:
#         conn = self.connect()
#         r = conn.execute(
#             "SELECT prefix, parent, target, max_lifetime_days, allow_push, require_pr FROM flows WHERE name = ?",
#             (name,),
#         ).fetchone()
#         if r:
#             return Flow(
#                 r["prefix"],
#                 r["parent"],
#                 r["target"],
#                 r["max_lifetime_days"],
#                 bool(r["allow_push"]),
#                 bool(r["require_pr"]),
#             )
#         return None

#     def list_flows(self) -> List[Tuple[str, Flow]]:
#         conn = self.connect()
#         rows = conn.execute(
#             "SELECT name, prefix, parent, target, max_lifetime_days, allow_push, require_pr FROM flows"
#         ).fetchall()
#         return [
#             (
#                 r["name"],
#                 Flow(
#                     r["prefix"],
#                     r["parent"],
#                     r["target"],
#                     r["max_lifetime_days"],
#                     bool(r["allow_push"]),
#                     bool(r["require_pr"]),
#                 ),
#             )
#             for r in rows
#         ]

#     def detect_flow_for_branch(self, branch: str) -> Optional[Tuple[str, Flow]]:
#         """
#         Returns (flow_name, Flow) for the first matching prefix,
#         or None.
#         """
#         conn = self.connect()
#         rows = conn.execute(
#             "SELECT name, prefix, parent, target, max_lifetime_days, allow_push, require_pr FROM flows"
#         ).fetchall()
#         for r in rows:
#             prefix = r["prefix"]
#             if branch.startswith(prefix):
#                 return (
#                     r["name"],
#                     Flow(
#                         r["prefix"],
#                         r["parent"],
#                         r["target"],
#                         r["max_lifetime_days"],
#                         bool(r["allow_push"]),
#                         bool(r["require_pr"]),
#                     ),
#                 )
#         return None

#     # -------------------------
#     # binds API
#     # -------------------------
#     def add_bind(self, b: Bind):
#         conn = self.connect()
#         conn.execute(
#             "INSERT OR REPLACE INTO binds (name, parent, target, mode, tag, conflict_policy, schedule) VALUES (?, ?, ?, ?, ?, ?, ?)",
#             (
#                 b.name,
#                 b.parent,
#                 b.target,
#                 b.mode,
#                 int(b.tag),
#                 b.conflict_policy,
#                 b.schedule,
#             ),
#         )
#         conn.commit()

#     def get_bind(self, name: str) -> Optional[Bind]:
#         conn = self.connect()
#         r = conn.execute(
#             "SELECT parent, target, mode, tag, conflict_policy, schedule FROM binds WHERE name = ?",
#             (name,),
#         ).fetchone()
#         if r:
#             return Bind(
#                 name,
#                 r["parent"],
#                 r["target"],
#                 r["mode"],
#                 bool(r["tag"]),
#                 r["conflict_policy"],
#                 r["schedule"],
#             )
#         return None

#     def list_binds(self) -> List[Bind]:
#         conn = self.connect()
#         rows = conn.execute(
#             "SELECT name, parent, target, mode, tag, conflict_policy, schedule FROM binds"
#         ).fetchall()
#         return [
#             Bind(
#                 r["name"],
#                 r["parent"],
#                 r["target"],
#                 r["mode"],
#                 bool(r["tag"]),
#                 r["conflict_policy"],
#                 r["schedule"],
#             )
#             for r in rows
#         ]
