import typer

from typing import Annotated

from .config import app as config_app
from .bind import app as bind_app
from .flux import app as flux_app
from .trunk import app as trunk_app
from ..tree_manager import TreeManager

# Istanza condivisa
tree_manager = TreeManager()
app = typer.Typer()


@app.callback()
def callback(
    ctx: typer.Context,
    tree_manager: Annotated[
        TreeManager, typer.Option(help="Tree manager instance")
    ] = tree_manager,
):
    ctx.obj = {"tree_manager": tree_manager}


app.add_typer(config_app, name="config")
app.add_typer(bind_app, name="bind")
app.add_typer(flux_app, name="flux")
app.add_typer(trunk_app, name="trunk")


# ---------------------- COMMIT/UPDATE ----------------------
@app.command()
def commit(
    message: str = typer.Option(..., help="Commit message"),
    all: bool = typer.Option(False, help="Add all changes"),
    files: list[str] = typer.Option(None, help="List of files to add"),
):
    """Commit changes to the current branch."""
    current_branch = tree_manager.lg.current_branch()
    flow = tree_manager.detect_flow(current_branch)
    if flow is None:
        # maybe it's a trunk: we still allow commit, but warn
        typer.echo(
            "Warning: current branch is not part of a flow; treating as trunk/standalone."
        )

    # Stage changes
    if all:
        tree_manager.lg.add(all=True)
    elif files:
        tree_manager.lg.add(all=False, files=[f for f in files])
    else:
        raise typer.Exit("No files specified for commit and --all not set")

    # Commit
    tree_manager.lg.commit(message)
    typer.echo(f"Committed changes on {current_branch} with message: '{message}'")

    # Push if policy allows (check via TreeManager)
    if tree_manager.can_push(current_branch):
        tree_manager.lg.push(current_branch)
        typer.echo(f"Pushed {current_branch}")
    else:
        typer.echo(f"Push skipped: policy forbids pushing directly to {current_branch}")

    # Advisory about PR
    if tree_manager.requires_pr(current_branch):
        typer.echo(
            f"Note: merging {current_branch} into its target should follow PR workflow."
        )


# ---------------------- LIST BRANCHES ----------------------
@app.command()
def list(remote: bool = typer.Option(True, help="Include remote branches")):
    """Show current branch and list of branches."""
    current_branch = tree_manager.lg.current_branch()
    branches = tree_manager.lg.list_branches(remote=remote)

    typer.echo(f"Current branch: {current_branch}")
    typer.echo(f"Branches ({'remote' if remote else 'local'}):")
    for b in branches:
        print(b)


# ---------------------- BRANCH SWITCH ----------------------
@app.command()
def switch(branch: str = typer.Argument(..., help="Branch name to switch to")):
    """Switch to an existing branch."""
    tree_manager.lg.checkout(branch)
    typer.echo(f"Switched to {branch}")


# ---------------------- BRANCH RENAME ----------------------
# @app.command()
# def rename(
#     old: str = typer.Argument(..., help="Old branch name"),
#     new: str = typer.Argument(..., help="New branch name"),
# ):
#     """Rename a branch locally and remotely."""
#     tree_manager.lg.rename_branch(old, new)
#     typer.echo(f"Renamed branch {old} → {new}")


# ---------------------- BRANCH DELETE ----------------------
# @app.command()
# def delete(
#     branch: str = typer.Argument(..., help="Branch name to delete"),
#     remote: bool = typer.Option(False, help="Also delete remote branch"),
# ):
#     """Delete a branch locally and optionally remotely."""
#     tree_manager.lg.delete_branch(branch, remote=remote)
#     typer.echo(f"Deleted branch {branch}")


# # ---------------------- SQUASH COMMITS ----------------------
# @app.command()
# def squash(
#     n: int = typer.Argument(..., help="Number of commits to squash"),
#     message: str = typer.Option(..., help="Message for the squashed commit"),
# ):
#     """Squash the last N commits into a single commit."""
#     current = fm.lg.current_branch()
#     repo = fm.lg.repo

#     # Verifica che ci siano abbastanza commit
#     commits = list(repo.iter_commits(current))
#     if len(commits) < n:
#         typer.echo(f"Branch has only {len(commits)} commits, cannot squash {n}.")
#         raise typer.Exit(1)

#     # Individua il commit "base"
#     base_commit = commits[n]  # commit prima degli ultimi n

#     typer.echo(f"Squashing last {n} commits on {current}...")

#     try:
#         # Soft reset al commit base
#         repo.git.reset("--soft", base_commit.hexsha)

#         # Crea il nuovo commit squashed
#         repo.git.commit("-m", message)

#         typer.echo(f"Squash successful. New single commit created.")
#     except Exception as e:
#         typer.echo(f"Error during squash: {e}")
#         raise typer.Exit(1)


# ---------------------- LOG ----------------------
# TODO gatp log
# @app.command()
# def log(
#     n: int = typer.Option(10, help="Number of commits to show"),
#     full: bool = typer.Option(False, help="Show full commit message"),
# ):
#     """Show the last N commits on the current branch."""
#     commits = fm.lg.get_commits(n)
#     for c in commits:
#         typer.echo(f"\nCommit: {c.hexsha[:10]}")
#         typer.echo(f"Author: {c.author.name}")
#         typer.echo(f"Date:   {c.committed_datetime}")
#         typer.echo(f"Msg:    {c.message if full else c.summary}")


# ---------------------- SHOW COMMIT DIFF ----------------------
# @app.command()
# def diff(
#     commit: str = typer.Argument(..., help="Commit hash"),
#     file: str = typer.Option(None, help="Show diff only for this file"),
# ):
#     """Show the diff of a specific commit, optionally for a single file."""
#     diff = fm.lg.show_commit(commit, file)
#     typer.echo(diff)


# # ---------------------- BLAME ----------------------
# @app.command()
# def blame(
#     file: str = typer.Argument(..., help="File to analyze"),
#     line: int = typer.Option(None, help="Line number to blame"),
# ):
#     """Show git blame information for a file, optionally for a specific line."""
#     result = fm.lg.blame(file, line)
#     typer.echo(result)


# # ---------------------- CONFIG ----------------------
# @config_app.command("setup")
# def config_setup():
#     """Initialize trunk/flow configuration database in this repository."""
#     if fm.store.is_initialized():
#         typer.echo("Repository is already initialized.")
#         raise typer.Exit()

#     fm.init_store_with_defaults()
#     typer.echo("Repository initialized for flow management.")


# @config_app.command("show")
# def config_show():
#     """Show current trunk and flow configuration."""
#     if not fm.store.is_initialized():
#         typer.echo("Not initialized. Run `tool config setup` first.")
#         raise typer.Exit()

#     typer.echo("Trunks:")
#     for t in fm.store.list_trunks():
#         typer.echo(
#             f"  - {t.name}: allow_push={t.allow_push}, require_pr={t.require_pr}"
#         )

#     typer.echo("\nFlows:")
#     for name, f in fm.store.list_flows():
#         typer.echo(
#             f"  - {name}: prefix={f.prefix}, parent={f.parent}, target={f.target}"
#         )


# @config_app.command("cleanup")
# def config_cleanup():
#     """Delete remote branches that are not part of any trunk or configured flow."""
#     if not fm.store.is_initialized():
#         typer.echo("Not initialized. Run `tool config setup` first.")
#         raise typer.Exit()

#     remote = fm.lg.get_remote_name()
#     all_branches = fm.lg.list_branches(remote=True)

#     valid_trunks = [f"{remote}/{t}" for t in fm.trunks.keys()]
#     valid_flow_prefixes = [f"{remote}/{f.prefix}" for f in fm.flows.values()]

#     for branch in all_branches:
#         if branch in valid_trunks:
#             continue
#         if any(branch.startswith(prefix) for prefix in valid_flow_prefixes):
#             continue

#         # extract branch name without remote prefix
#         branch_name = branch.split("/", 1)[1]

#         # skip HEAD or weird git branches
#         if branch_name == "HEAD":
#             continue

#         # ask for confirmation and delete if confirmed
#         confirm = typer.confirm(f"Delete remote branch '{branch_name}'?", default=False)
#         if confirm:
#             fm.lg.delete_branch(branch_name, remote=True)
#             typer.echo(f"Deleted remote branch: {branch_name}")


# @config_app.command("new-trunk")
# def config_new_trunk(
#     name: str = typer.Argument(...),
#     allow_push: bool = typer.Option(True),
#     require_pr: bool = typer.Option(False),
# ):
#     """Create a new trunk branch definition."""
#     if not fm.store.is_initialized():
#         typer.echo("Not initialized. Run `tool config setup` first.")
#         raise typer.Exit()

#     t = Trunk(name=name, allow_push=allow_push, require_pr=require_pr)
#     fm.store.add_trunk(t)
#     typer.echo(f"Added trunk '{name}' (push={allow_push}, pr={require_pr}).")


# @config_app.command("new-flow")
# def config_new_flow(
#     flow_name: str = typer.Argument(...),
#     prefix: str = typer.Option(...),
#     parent: str = typer.Option(..., help="Must be a trunk"),
#     target: str = typer.Option(..., help="Must be a trunk"),
# ):
#     """Create a new flow definition."""
#     if not fm.store.is_initialized():
#         typer.echo("Not initialized. Run `tool config setup` first.")
#         raise typer.Exit()

#     # validation: parent & target must be trunks
#     if not fm.store.get_trunk(parent):
#         raise typer.Exit(f"Parent trunk '{parent}' does not exist.")
#     if not fm.store.get_trunk(target):
#         raise typer.Exit(f"Target trunk '{target}' does not exist.")

#     f = Flow(prefix=prefix, parent=parent, target=target)
#     fm.store.add_flow(flow_name, f)

#     typer.echo(
#         f"Added flow '{flow_name}' → prefix={prefix}, parent={parent}, target={target}."
#     )


# @config_app.command("del-trunk")
# def config_del_trunk(name: str):
#     """Delete a trunk if not referenced by any flow."""
#     if not fm.store.is_initialized():
#         typer.echo("Not initialized.")
#         raise typer.Exit()

#     # check for flows referencing this trunk
#     flows = fm.store.list_flows()
#     for flow_name, f in flows:
#         if f.parent == name or f.target == name:
#             raise typer.Exit(
#                 f"Trunk '{name}' is used by flow '{flow_name}' and cannot be deleted."
#             )

#     conn = fm.store.connect()
#     conn.execute("DELETE FROM trunks WHERE name = ?", (name,))
#     conn.commit()

#     typer.echo(f"Deleted trunk '{name}'.")


# @config_app.command("del-flow")
# def config_del_flow(name: str):
#     """Delete a flow definition."""
#     if not fm.store.is_initialized():
#         typer.echo("Not initialized.")
#         raise typer.Exit()

#     conn = fm.store.connect()
#     conn.execute("DELETE FROM flows WHERE name = ?", (name,))
#     conn.commit()

#     typer.echo(f"Deleted flow '{name}'.")


# # @config_app.command("retain")
# # def config_retain_flow_branches(days: int = typer.Argument(...)):
# #     """Delete merged flow branches older than a given number of days."""
# #     fm.retain_flow_branches(older_than_days=days)
# #     typer.echo(f"Deleted flows older than {days} days.")


# if __name__ == "__main__":
#     app()
