from typing import Optional, Tuple
from datetime import datetime

from .repository import GitRepository
from .db import DBStore, Trunk, Flow, Bind

# default objects (usali per init)
DEFAULT_TRUNKS = {
    "main": Trunk("main", allow_push=False, require_pr=True),
    "develop": Trunk("develop", allow_push=True, require_pr=True),
}

DEFAULT_FLOWS = {
    "feature": Flow("feature/", parent="develop", target="develop"),
    "hotfix": Flow("hotfix/", parent="main", target="main"),
    # "release": Flow("release/", parent="develop", target="main"),
}

DEFAULT_BINDS = {
    "release": Bind(
        name="release", parent="develop", target="main", mode="aggregate", tag=True
    ),
}


class TreeManager:
    def __init__(self, repo_path: str = "."):
        # determine repo root using GitRepository
        self.repo = GitRepository(repo_path)
        self.repo_root = self.repo.get_repo_root()
        self.store = DBStore(self.repo_root)

        if self.store.is_initialized():
            # load from DB
            self.trunks = {t.name: t for t in self.store.get_trunks()}
            # flows: map name->Flow
            self.flows = {name: flow for (name, flow) in self.store.get_flows()}
            # binds can be added similarly if needed
            self.binds = {b.name: b for b in self.store.get_binds()}
        else:
            # use defaults until user calls setup/init
            self.trunks = DEFAULT_TRUNKS
            self.flows = DEFAULT_FLOWS
            self.binds = DEFAULT_BINDS

        # initialize user
        self.user_exists = self.init_user()

    def init_user(self):

        if self.store.is_initialized() and self.repo.user_name and self.repo.user_email:

            # verify user on db or create default
            name = self.repo.user_name
            email = self.repo.user_email
            users = self.store.get_users()

            # if there are no users, add current as admin
            if not users:
                self.store.add_user(name=name, email=email, admin=True)
                return True
            else:
                # verify existing user
                for u in users:
                    if u.name == name and u.email == email:
                        return True

                # if the user is not found, add as non-admin
                self.store.add_user(name=name, email=email, admin=False)
                return True

        # if the user does not exist, or it's not initialized, return False
        return False

    def detect_trunk(self, branch: str) -> Optional[Trunk]:
        # direct match on trunk names
        if branch in self.trunks:
            return self.trunks[branch]
        return None

    def detect_flow(self, branch: str) -> Optional[Tuple[str, Flow]]:
        # if DB is used, prefer DB lookup; otherwise fallback to defaults
        # self.flows maps name->Flow (if from DB) or default mapping name->Flow
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

    def execute_bind(self, bind_name: str):
        bind = self.binds.get(bind_name)
        if not bind:
            raise KeyError(f"Bind '{bind_name}' not found")
        parent = bind.parent
        target = bind.target
        mode = bind.mode
        tag = bind.tag

        assert mode in ("merge", "rebase", "aggregate"), f"Invalid bind mode '{mode}'"

        # Ensure branches exist
        if not self.repo.branch_exists(parent):
            raise ValueError(f"Parent branch '{parent}' does not exist")
        if not self.repo.branch_exists(target):
            raise ValueError(f"Target branch '{target}' does not exist")

        # get target record
        target_trunk = self.store.get_trunk(target)

        if target_trunk.allow_push:

            if mode == "merge":
                # Merge changes from parent to target
                self.repo.merge(source=parent, target=target)
            elif mode == "rebase":
                # Rebase target onto parent
                self.repo.rebase(source=parent, onto=target)
            elif mode == "aggregate":
                # Aggregate changes from both branches and push in both directions
                # Merge parent into target
                self.repo.merge(source=parent, target=target)
                # Merge target back into parent to keep them in sync
                self.repo.merge(source=target, target=parent)

            self.repo.checkout(target)
            self.repo.push(target)

            if tag:
                # Create a tag with current timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                tag_name = f"{bind.name}-{timestamp}"
                self.repo.repo.create_tag(tag_name)
                self.repo.push()

        if target_trunk.require_pr:
            print(
                f"Target trunk '{target}' requires PRs; please create a PR for changes from '{parent}' to '{target}'."
            )

    # def retain_flow_branches(self, older_than_days: int = 30):
    #     # retention process: delete merged flow branches
    #     # (not-trunks) older than a given date, with no additional commit,
    #     # and with no PRs open
    #     now = datetime.now()
    #     cutoff_date = now - timedelta(days=older_than_days)
    #     remote = self.repo.get_remote_name()

    #     for name, fs in self.flows.items():
    #         if isinstance(fs, tuple):
    #             fs = fs[1]
    #         prefix = fs.prefix
    #         for bname in self.repo.list_branches(remote=True):
    #             # remove remote prefix if present
    #             branch_short = bname[len(f"{remote}/") :]
    #             print(bname)
    #             if branch_short.startswith(prefix):
    #                 # check last commit date
    #                 commit = self.repo.repo.commit(bname)
    #                 commit_date = datetime.fromtimestamp(commit.committed_date)
    #                 if commit_date < cutoff_date:
    #                     # 1 - check if merged into target trunk
    #                     target_trunk = fs.target
    #                     if not self.repo.branch_exists(target_trunk):
    #                         continue
    #                     target_commit = self.repo.repo.commit(target_trunk)
    #                     if commit.hexsha == target_commit.hexsha:
    #                         # already at tip, can delete
    #                         pass
    #                     elif commit in self.repo.repo.iter_commits(
    #                         f"{bname}..{target_trunk}"
    #                     ):
    #                         # commit is ancestor of target trunk, can delete
    #                         pass
    #                     else:
    #                         # not merged yet
    #                         continue
    #                     # 2- check for open PRs

    #                     # Here you would check for open PRs via provider API
    #                     # For now, we just print the branch to be deleted
    #                     print(
    #                         f"Branch '{bname}' is older than {older_than_days} days and can be deleted."
    #                     )


# TODO git tagging
# TODO direct flow between trunks with tag: link/join/hook/weld/stamp
# TODO merge back main to develop
# TODO test CI
# TODO impostare effettivamente su git repo che non si può pushare su trunk che non lo permettono
# TODO aggiungere controllo automatico con gerarchia dei trunks
# (es. la modifica di develop deve essere propatagata a main, quindi develop ha una gerarchia su main)
# per ogni commit crea un file fittizio, collezionali, ed alla fine verifica che per ogni trunk le modifiche siano propatagate senza conflitti
