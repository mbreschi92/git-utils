# app.py
import typer
from .local_git import LocalGit
from .db_store import TrunkSettings, FlowSettings
from .flow_manager import FlowManager
from .provider_api import AzureDevOpsProvider

app = typer.Typer()
config_app = typer.Typer(help="Manage flow/trunk configuration.")
app.add_typer(config_app, name="config")


lg = LocalGit(".")
fm = FlowManager()


# ---------------------- START ----------------------
@app.command()
def start(
    branch: str = typer.Argument(..., help="Branch name including prefix"),
    base: str = typer.Option(None, help="Optional base branch override"),
    push: bool = typer.Option(True, help="Push the branch after creation"),
):
    """Start a new flow branch from the appropriate base branch."""
    flow = fm.detect_flow(branch)
    if not flow:
        typer.echo(f"Unknown flow for branch {branch}")
        raise typer.Exit(code=1)

    flow_name, flow_settings = flow
    actual_base = base or flow_settings.parent

    if not lg.branch_exists(actual_base):
        raise RuntimeError(f"Base branch '{actual_base}' does not exist locally.")

    # create from base
    lg.checkout(actual_base)
    lg.checkout(branch, create=True)

    # push if requested and allowed by policy (flow/trunk)
    if push:
        if fm.can_push(branch):
            lg.push(branch)
            typer.echo(f"Created branch {branch} from {actual_base} and pushed.")
        else:
            typer.echo(
                f"Created branch {branch} from {actual_base} (push is not allowed by policy)."
            )
    else:
        typer.echo(f"Created branch {branch} from {actual_base} (not pushed).")


# ---------------------- FINISH ----------------------
@app.command()
def finish(
    branch: str = typer.Argument(..., help="Branch name including prefix"),
    org: str = typer.Option(..., help="Azure DevOps organization"),
    project: str = typer.Option(..., help="Azure DevOps project"),
    repo: str = typer.Option(..., help="Azure DevOps repository"),
    pat: str = typer.Option(..., help="Azure DevOps personal access token"),
    resolve: str = typer.Option(
        "ort", help="Auto-resolve strategy: ort|ours|theirs|resolve"
    ),
    ff: bool = typer.Option(False, help="Allow fast-forward merge"),
):
    """Finish a feature branch by merging it into the target trunk (with policy)."""
    flow = fm.detect_flow(branch)
    if not flow:
        typer.echo(f"Unknown flow for branch {branch}")
        raise typer.Exit(code=1)

    flow_name, flow_settings = flow
    target_branch = flow_settings.target

    # target trunk settings
    target_trunk = fm.trunks.get(target_branch)
    if not target_trunk:
        raise RuntimeError(f"Target trunk '{target_branch}' not configured.")

    if not lg.branch_exists(target_branch):
        raise RuntimeError(f"Target branch '{target_branch}' does not exist locally.")

    # Checkout target branch and pull latest
    lg.checkout(target_branch)
    lg.pull(target_branch)

    # Merge source into target. LocalGit.merge raises MergeConflictError if conflict.
    try:
        # LocalGit.merge signature: merge(source, target, strategy=None, no_ff=True)
        lg.merge(branch, target_branch, strategy=resolve, no_ff=not ff)
        typer.echo(f"Merged {branch} → {target_branch}")
    except Exception as e:
        # prefer specific MergeConflictError, fallback generic
        if isinstance(e, getattr(lg, "MergeConflictError", type(e))):
            conflicts = lg.repo.index.unmerged_blobs()
            typer.echo("Merge conflict detected!")
            for path, bloblist in conflicts.items():
                typer.echo(f" - {path}")
            typer.echo(
                "\nRisolvi i conflitti manualmente, poi esegui `resolve` per completare."
            )
            raise typer.Exit(code=1)
        else:
            raise

    # Push target if allowed by trunk policy
    if fm.can_push(target_branch):
        lg.push(target_branch)
        typer.echo(f"Pushed {target_branch}.")
    else:
        typer.echo(f"Target {target_branch} is protected: push skipped.")

    # Create PR if required by trunk policy (note: often PR to trunk is not needed if already merged locally)
    if fm.requires_pr(target_branch):
        provider = AzureDevOpsProvider(org, project, repo, pat)
        pr = provider.create_pr(
            source=branch,
            target=target_branch,
            title=f"Merge {branch} → {target_branch}",
            description="Auto-created by Gitflow manager.",
        )
        typer.echo(f"PR created: {pr.get('pullRequestId', 'N/A')}")
    else:
        typer.echo(
            f"PR not created: target trunk '{target_branch}' does not require PR."
        )


# ---------------------- RESOLVE MERGE FINISH ----------------------
@app.command()
def resolve(
    org: str = typer.Option(..., help="Azure DevOps organization"),
    project: str = typer.Option(..., help="Azure DevOps project"),
    repo: str = typer.Option(..., help="Azure DevOps repository"),
    pat: str = typer.Option(..., help="Azure DevOps personal access token"),
):
    """Complete a merge after resolving conflicts manually."""
    # we expect user to be on the target branch (merge in progress)
    current_branch = lg.current_branch()

    # check merge in progress
    if not lg.repo.index.unmerged_blobs():
        typer.echo("No merge in progress. Nothing to resolve.")
        raise typer.Exit()

    typer.echo("Committing resolved merge ...")

    # Stage resolved files (add everything)
    lg.add(all=True)

    # Finalize merge commit
    message = f"Merge resolution on {current_branch}"
    lg.commit(message)
    typer.echo(f"Merge resolved and committed on {current_branch}.")

    # Determine flow/trunk context for push / PR decisions:
    # if current branch is a trunk, target_trunk = current_branch,
    # else it's likely a trunk name (since merge occurs on trunk).
    target_trunk = current_branch
    trunk_settings = fm.trunks.get(target_trunk)
    if not trunk_settings:
        typer.echo(
            f"Warning: {target_trunk} is not registered as a trunk; using conservative defaults."
        )

    # Push if trunk allows it
    if fm.can_push(target_trunk):
        lg.push(target_trunk)
        typer.echo(f"Pushed {target_trunk}.")

    # If the trunk's policy requires PRs (unusual after merge), create one
    if fm.requires_pr(target_trunk):
        provider = AzureDevOpsProvider(org, project, repo, pat)
        # TODO: source branch is unknown here; user must provide it
        # We need a source branch to open a PR — in the merge flow the source branch
        # is not deterministically known here. If you want to auto-create PRs from
        # the original source branch, you should pass it as an argument to resolve().
        typer.echo(
            "PR creation requested by policy, but resolve() does not know the original source branch."
        )
        typer.echo("Please create PR manually or pass source branch to the command.")
    else:
        typer.echo("No PR required by trunk policy.")


# ---------------------- COMMIT/UPDATE ----------------------
@app.command()
def commit(
    message: str = typer.Option(..., help="Commit message"),
    all: bool = typer.Option(False, help="Add all changes"),
    files: list[str] = typer.Option(None, help="List of files to add"),
):
    """Commit changes to the current branch."""
    current_branch = lg.current_branch()
    flow = fm.detect_flow(current_branch)
    if flow is None:
        # maybe it's a trunk: we still allow commit, but warn
        typer.echo(
            "Warning: current branch is not part of a flow; treating as trunk/standalone."
        )

    # Stage changes
    if all:
        lg.add(all=True)
    elif files:
        lg.add(all=False, files=[f for f in files])
    else:
        raise typer.Exit("No files specified for commit and --all not set")

    # Commit
    lg.commit(message)
    typer.echo(f"Committed changes on {current_branch} with message: '{message}'")

    # Push if policy allows (check via FlowManager)
    if fm.can_push(current_branch):
        lg.push(current_branch)
        typer.echo(f"Pushed {current_branch}")
    else:
        typer.echo(f"Push skipped: policy forbids pushing directly to {current_branch}")

    # Advisory about PR
    if fm.requires_pr(current_branch):
        typer.echo(
            f"Note: merging {current_branch} into its target should follow PR workflow."
        )


# ---------------------- LIST BRANCHES ----------------------
@app.command()
def list(remote: bool = typer.Option(True, help="Include remote branches")):
    """Show current branch and list of branches."""
    current_branch = lg.current_branch()
    branches = lg.list_branches(remote=remote)

    typer.echo(f"Current branch: {current_branch}")
    typer.echo(f"Branches ({'remote' if remote else 'local'}):")
    for b in branches:
        print(b)


# ---------------------- BRANCH SWITCH ----------------------
@app.command()
def switch(branch: str = typer.Argument(..., help="Branch name to switch to")):
    """Switch to an existing branch."""
    lg.checkout(branch)
    typer.echo(f"Switched to {branch}")


# ---------------------- BRANCH RENAME ----------------------
@app.command()
def rename(
    old: str = typer.Argument(..., help="Old branch name"),
    new: str = typer.Argument(..., help="New branch name"),
):
    """Rename a branch locally and remotely."""
    lg.rename_branch(old, new)
    typer.echo(f"Renamed branch {old} → {new}")


# ---------------------- BRANCH DELETE ----------------------
@app.command()
def delete(
    branch: str = typer.Argument(..., help="Branch name to delete"),
    remote: bool = typer.Option(False, help="Also delete remote branch"),
):
    """Delete a branch locally and optionally remotely."""
    lg.delete_branch(branch, remote=remote)
    typer.echo(f"Deleted branch {branch}")


# ---------------------- SQUASH COMMITS ----------------------
@app.command()
def squash(
    n: int = typer.Argument(..., help="Number of commits to squash"),
    message: str = typer.Option(..., help="Message for the squashed commit"),
):
    """Squash the last N commits into a single commit."""
    current = lg.current_branch()
    repo = lg.repo

    # Verifica che ci siano abbastanza commit
    commits = list(repo.iter_commits(current))
    if len(commits) < n:
        typer.echo(f"Branch has only {len(commits)} commits, cannot squash {n}.")
        raise typer.Exit(1)

    # Individua il commit "base"
    base_commit = commits[n]  # commit prima degli ultimi n

    typer.echo(f"Squashing last {n} commits on {current}...")

    try:
        # Soft reset al commit base
        repo.git.reset("--soft", base_commit.hexsha)

        # Crea il nuovo commit squashed
        repo.git.commit("-m", message)

        typer.echo(f"Squash successful. New single commit created.")
    except Exception as e:
        typer.echo(f"Error during squash: {e}")
        raise typer.Exit(1)


# ---------------------- LOG ----------------------
@app.command()
def log(
    n: int = typer.Option(10, help="Number of commits to show"),
    full: bool = typer.Option(False, help="Show full commit message"),
):
    """Show the last N commits on the current branch."""
    commits = lg.get_commits(n)
    for c in commits:
        typer.echo(f"\nCommit: {c.hexsha[:10]}")
        typer.echo(f"Author: {c.author.name}")
        typer.echo(f"Date:   {c.committed_datetime}")
        typer.echo(f"Msg:    {c.message if full else c.summary}")


# ---------------------- SHOW COMMIT DIFF ----------------------
@app.command()
def diff(
    commit: str = typer.Argument(..., help="Commit hash"),
    file: str = typer.Option(None, help="Show diff only for this file"),
):
    """Show the diff of a specific commit, optionally for a single file."""
    diff = lg.show_commit(commit, file)
    typer.echo(diff)


# ---------------------- BLAME ----------------------
@app.command()
def blame(
    file: str = typer.Argument(..., help="File to analyze"),
    line: int = typer.Option(None, help="Line number to blame"),
):
    """Show git blame information for a file, optionally for a specific line."""
    result = lg.blame(file, line)
    typer.echo(result)


# ---------------------- CONFIG ----------------------
@config_app.command("setup")
def config_setup():
    """Initialize trunk/flow configuration database in this repository."""
    if fm.store.is_initialized():
        typer.echo("Repository is already initialized.")
        raise typer.Exit()

    fm.init_store_with_defaults()
    typer.echo("Repository initialized for flow management.")


@config_app.command("show")
def config_show():
    """Show current trunk and flow configuration."""
    if not fm.store.is_initialized():
        typer.echo("Not initialized. Run `tool config setup` first.")
        raise typer.Exit()

    typer.echo("Trunks:")
    for t in fm.store.list_trunks():
        typer.echo(
            f"  - {t.name}: allow_push={t.allow_push}, require_pr={t.require_pr}"
        )

    typer.echo("\nFlows:")
    for name, f in fm.store.list_flows():
        typer.echo(
            f"  - {name}: prefix={f.prefix}, parent={f.parent}, target={f.target}"
        )


@config_app.command("cleanup")
def config_cleanup():
    """Delete remote branches that are not part of any trunk or configured flow."""
    if not fm.store.is_initialized():
        typer.echo("Not initialized. Run `tool config setup` first.")
        raise typer.Exit()

    remote = lg.get_remote_name()
    all_branches = lg.list_branches(remote=True)

    valid_trunks = [f"{remote}/{t}" for t in fm.trunks.keys()]
    valid_flow_prefixes = [f"{remote}/{f.prefix}" for f in fm.flows.values()]

    for branch in all_branches:
        if branch in valid_trunks:
            continue
        if any(branch.startswith(prefix) for prefix in valid_flow_prefixes):
            continue

        # extract branch name without remote prefix
        branch_name = branch.split("/", 1)[1]

        # skip HEAD or weird git branches
        if branch_name == "HEAD":
            continue

        # ask for confirmation and delete if confirmed
        confirm = typer.confirm(f"Delete remote branch '{branch_name}'?", default=False)
        if confirm:
            lg.delete_branch(branch_name, remote=True)
            typer.echo(f"Deleted remote branch: {branch_name}")


@config_app.command("new-trunk")
def config_new_trunk(
    name: str = typer.Argument(...),
    allow_push: bool = typer.Option(True),
    require_pr: bool = typer.Option(False),
):
    """Create a new trunk branch definition."""
    if not fm.store.is_initialized():
        typer.echo("Not initialized. Run `tool config setup` first.")
        raise typer.Exit()

    t = TrunkSettings(name=name, allow_push=allow_push, require_pr=require_pr)
    fm.store.add_trunk(t)
    typer.echo(f"Added trunk '{name}' (push={allow_push}, pr={require_pr}).")


@config_app.command("new-flow")
def config_new_flow(
    flow_name: str = typer.Argument(...),
    prefix: str = typer.Option(...),
    parent: str = typer.Option(..., help="Must be a trunk"),
    target: str = typer.Option(..., help="Must be a trunk"),
):
    """Create a new flow definition."""
    if not fm.store.is_initialized():
        typer.echo("Not initialized. Run `tool config setup` first.")
        raise typer.Exit()

    # validation: parent & target must be trunks
    if not fm.store.get_trunk(parent):
        raise typer.Exit(f"Parent trunk '{parent}' does not exist.")
    if not fm.store.get_trunk(target):
        raise typer.Exit(f"Target trunk '{target}' does not exist.")

    f = FlowSettings(prefix=prefix, parent=parent, target=target)
    fm.store.add_flow(flow_name, f)

    typer.echo(
        f"Added flow '{flow_name}' → prefix={prefix}, parent={parent}, target={target}."
    )


@config_app.command("del-trunk")
def config_del_trunk(name: str):
    """Delete a trunk if not referenced by any flow."""
    if not fm.store.is_initialized():
        typer.echo("Not initialized.")
        raise typer.Exit()

    # check for flows referencing this trunk
    flows = fm.store.list_flows()
    for flow_name, f in flows:
        if f.parent == name or f.target == name:
            raise typer.Exit(
                f"Trunk '{name}' is used by flow '{flow_name}' and cannot be deleted."
            )

    conn = fm.store.connect()
    conn.execute("DELETE FROM trunks WHERE name = ?", (name,))
    conn.commit()

    typer.echo(f"Deleted trunk '{name}'.")


@config_app.command("del-flow")
def config_del_flow(name: str):
    """Delete a flow definition."""
    if not fm.store.is_initialized():
        typer.echo("Not initialized.")
        raise typer.Exit()

    conn = fm.store.connect()
    conn.execute("DELETE FROM flows WHERE name = ?", (name,))
    conn.commit()

    typer.echo(f"Deleted flow '{name}'.")


if __name__ == "__main__":
    app()
