from typing import Optional, Tuple

from .local_git import LocalGit, TrunkSettings, FlowSettings
from .db_store import DBStore

# default objects (usali per init)
DEFAULT_TRUNKS = {
    "main": TrunkSettings("main", allow_push=False, require_pr=True),
    "develop": TrunkSettings("develop", allow_push=True, require_pr=True),
}

DEFAULT_FLOWS = {
    "feature": FlowSettings("feature/", parent="develop", target="develop"),
    "hotfix": FlowSettings("hotfix/", parent="main", target="main"),
    "release": FlowSettings("release/", parent="develop", target="main"),
}


class FlowManager:
    def __init__(self, repo_path: str = "."):
        # determine repo root using LocalGit
        lg = LocalGit(repo_path)
        self.repo_root = lg.get_repo_root()
        self.store = DBStore(self.repo_root)

        if self.store.is_initialized():
            # load from DB
            self.trunks = {t.name: t for t in self.store.list_trunks()}
            # flows: map name->FlowSettings
            self.flows = {name: flow for (name, flow) in self.store.list_flows()}
        else:
            # use defaults until user calls setup/init
            self.trunks = DEFAULT_TRUNKS
            self.flows = DEFAULT_FLOWS

    # -------------------------
    # detect/trunk helpers
    # -------------------------
    def detect_trunk(self, branch: str) -> Optional[TrunkSettings]:
        # direct match on trunk names
        if branch in self.trunks:
            return self.trunks[branch]
        return None

    def detect_flow(self, branch: str) -> Optional[Tuple[str, FlowSettings]]:
        # if DB is used, prefer DB lookup; otherwise fallback to defaults
        # self.flows maps name->FlowSettings (if from DB) or default mapping name->FlowSettings
        for name, cfg in self.flows.items():
            if isinstance(cfg, tuple):
                # case when list_flows returned raw tuples (defensive)
                cfg = cfg[1]
            if branch.startswith(cfg.prefix):
                return (name, cfg)
        return None

    def get_target(self, flow_name: str) -> str:
        f = self.flows.get(flow_name)
        if not f:
            raise KeyError(flow_name)
        return f.target

    def can_push(self, branch: str) -> bool:
        # if branch is trunk, read trunk settings; else find flow and use flow.parent target trunk settings
        t = self.detect_trunk(branch)
        if t:
            return bool(t.allow_push)
        flow = self.detect_flow(branch)
        if flow:
            _, fs = flow
            # target trunk settings if present
            trunk = self.trunks.get(fs.target)
            if trunk:
                return bool(trunk.allow_push)
            # default conservative
            return False
        return False

    def requires_pr(self, branch: str) -> bool:
        t = self.detect_trunk(branch)
        if t:
            return bool(t.require_pr)
        flow = self.detect_flow(branch)
        if flow:
            _, fs = flow
            trunk = self.trunks.get(fs.target)
            if trunk:
                return bool(trunk.require_pr)
            return True
        return True

    # Convenience: expose store init
    def init_store_with_defaults(self):
        # create DB and write defaults
        self.store.init_db(DEFAULT_TRUNKS, DEFAULT_FLOWS)
        # reload into memory
        self.trunks = {t.name: t for t in self.store.list_trunks()}
        self.flows = {name: flow for (name, flow) in self.store.list_flows()}
