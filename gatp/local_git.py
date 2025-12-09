# local_git.py
import git
from typing import Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


class MergeConflictError(Exception):
    pass


@dataclass
class TrunkSettings:
    name: str
    allow_push: bool
    require_pr: bool
    deprecated: bool = False
    default_branch: bool = False
    sync_with: list[str] = None


@dataclass
class FlowSettings:
    prefix: str
    parent: str
    target: str | list[str]
    max_lifetime_days: Optional[int] = None
    allow_push: bool = True
    require_pr: bool = False


@dataclass
class BindSettings:
    name: str
    parent: str
    target: str | list[str]
    mode: str = "merge"  # "merge", "rebase", "aggregate"
    tag: bool = True
    conflict_policy: str = (
        "block"  # "block", "notify", "resolve_ours", "resolve_theirs"
    )
    schedule: str = "on_push"  # "daily", "weekly", "on_push"


class LocalGit:
    def __init__(self, path: str):
        self.repo = git.Repo(path, search_parent_directories=True)

        # root del repo (cartella che contiene .git)
        self.repo_root = Path(self.repo.git.rev_parse("--show-toplevel"))

    def get_repo_root(self) -> Path:
        return self.repo_root

    def get_remote_name(self) -> str:
        return self.repo.remotes.origin.name

    def get_user_info(self) -> Tuple[str, str]:
        """Restituisce il nome e l'email dell'utente Git configurato."""
        with self.repo.config_reader() as config:
            name = config.get_value("user", "name", "")
            email = config.get_value("user", "email", "")
        return name, email

    def checkout(self, branch: str, create: bool = False):
        if create:
            return self.repo.git.checkout("-b", branch)
        return self.repo.git.checkout(branch)

    def current_branch(self) -> str:
        return self.repo.active_branch.name

    def branch_exists(self, name: str) -> bool:
        return name in [h.name for h in self.repo.heads]

    def create_branch(self, name: str, base: Optional[str] = None):
        if base:
            return self.repo.git.branch(name, base)
        return self.repo.git.branch(name)

    def push(self, branch: str = None):
        if branch is None:
            branch = self.current_branch()
        return self.repo.git.push(self.get_remote_name(), branch)

    def pull(self, branch: Optional[str] = None):
        if branch:
            return self.repo.git.pull(self.get_remote_name(), branch)
        return self.repo.git.pull(self.get_remote_name())

    def rename_branch(self, old: str, new: str):
        # rename locally
        self.repo.git.branch("-m", old, new)
        # push rename
        self.repo.git.push(self.get_remote_name(), f":{old}")  # delete old on remote
        self.repo.git.push(self.get_remote_name(), new)  # push new
        return True

    def add(self, all: bool = True, files: list[str] = None):
        if all:
            self.repo.git.add(A=True)
        elif files:
            for file in files:
                self.repo.index.add([file])
        else:
            self.repo.git.add(".")
        return True

    def commit(self, message: str):
        self.repo.index.commit(message)
        return True

    def rebase(self, source: str, onto: str):
        self.repo.git.checkout(onto)
        try:
            return self.repo.git.rebase(source)
        except git.exc.GitCommandError:
            raise MergeConflictError("Rebase conflict detected")

    def merge(
        self,
        source: str,
        target: str,
        strategy: str = None,
        no_ff: bool = True,
    ):
        if strategy not in ("ort", "ours", "theirs", "resolve"):
            raise ValueError(f"Unsupported merge strategy: {strategy}")
            # TODO implement strategy handling
        self.repo.git.checkout(target)
        try:
            if strategy and no_ff:
                return self.repo.git.merge("--no-ff", source, strategy_option=strategy)
            elif strategy:
                return self.repo.git.merge(source, strategy_option=strategy)
            elif no_ff:
                return self.repo.git.merge("--no-ff", source)
            return self.repo.git.merge(source)
        except git.exc.GitCommandError:
            raise MergeConflictError("Merge conflict detected")

    def delete_branch(self, name: str, remote: bool = False, force: bool = False):
        """
        Delete a branch locally and/or remotely.
        Handles branches that exist only on remote.
        """

        # ----------------------
        # 1. Delete LOCAL branch (if exists)
        # ----------------------
        local_branches = [h.name for h in self.repo.heads]

        if name in local_branches:
            try:
                if force:
                    self.repo.git.branch("-D", name)
                else:
                    self.repo.git.branch("-d", name)
            except Exception as e:
                # Still continue to remote delete if requested
                pass

        else:
            # no local branch → skip local delete silently
            pass

        # ----------------------
        # 2. Delete REMOTE branch
        # ----------------------
        if remote:
            remote_ref = f"origin/{name}"
            remote_branches = self.repo.git.branch("-r").splitlines()

            remote_branches = [b.strip() for b in remote_branches]

            if remote_ref in remote_branches:
                # delete remote branch
                try:
                    self.repo.git.push("origin", f":{name}")
                except Exception as e:
                    raise RuntimeError(f"Failed to delete remote branch '{name}': {e}")
            else:
                # remote branch does not exist → ignore
                pass

        return True

    def list_branches(self, remote: bool = False) -> list[str]:
        if remote:
            return [ref.name for ref in self.repo.remote().refs]
        return [h.name for h in self.repo.heads]

    def get_commits(self, n=10):
        return list(self.repo.iter_commits(self.repo.active_branch.name, max_count=n))

    def show_commit(self, commit_hash: str, path: str | None = None) -> str:
        commit = self.repo.commit(commit_hash)
        if commit.parents:
            parent = commit.parents[0]
        else:
            parent = None

        if parent:
            if path:
                return parent.diff(commit, paths=path, create_patch=True)[
                    0
                ].diff.decode()
            else:
                return self.repo.git.show(commit_hash)
        else:
            # First commit of the repo
            return self.repo.git.show(commit_hash)

    def blame(self, file_path: str, line: int | None = None) -> str:
        if line:
            # blame singola linea
            blame_info = self.repo.git.blame("-L", f"{line},{line}", file_path)
            return blame_info
        else:
            # blame completo
            return self.repo.git.blame(file_path)


if __name__ == "__main__":
    lg = LocalGit(".")
    print("Current branch:", lg.current_branch())
    print(lg.repo.config_reader())
