import typer

from ..provider_api import AzureDevOpsProvider

app = typer.Typer(help="Manage flux settings and operations.")

### List of commands for flux flow management
### start: create a new flow branch
### finish: finish a flow branch (merge into trunk with policy)
### resolve: complete a merge after manual conflict resolution


# ---------------------- START ----------------------
@app.command()
def start(
    ctx: typer.Context,
    branch: str = typer.Argument(..., help="Branch name including prefix"),
    base: str = typer.Option(None, help="Optional base branch override"),
    push: bool = typer.Option(True, help="Push the branch after creation"),
):
    """Start a new flow branch from the appropriate base branch."""

    tree_manager = ctx.obj["tree_manager"]

    flow = tree_manager.detect_flow(branch)
    if not flow:
        typer.echo(f"Unknown flow for branch {branch}")
        raise typer.Exit(code=1)

    flow_name, flow_settings = flow
    actual_base = base or flow_settings.parent

    if not tree_manager.lg.branch_exists(actual_base):
        raise RuntimeError(f"Base branch '{actual_base}' does not exist locally.")

    # create from base
    tree_manager.lg.checkout(actual_base)
    tree_manager.lg.checkout(branch, create=True)

    # push if requested and allowed by policy (flow/trunk)
    if push:
        if tree_manager.can_push(branch):
            tree_manager.lg.push(branch)
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
    ctx: typer.Context,
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

    tree_manager = ctx.obj["tree_manager"]

    flow = tree_manager.detect_flow(branch)
    if not flow:
        typer.echo(f"Unknown flow for branch {branch}")
        raise typer.Exit(code=1)

    flow_name, flow_settings = flow
    target_branch = flow_settings.target

    # target trunk settings
    target_trunk = tree_manager.trunks.get(target_branch)
    if not target_trunk:
        raise RuntimeError(f"Target trunk '{target_branch}' not configured.")

    if not tree_manager.lg.branch_exists(target_branch):
        raise RuntimeError(f"Target branch '{target_branch}' does not exist locally.")

    # Checkout target branch and pull latest
    tree_manager.lg.checkout(target_branch)
    tree_manager.lg.pull(target_branch)

    # Merge source into target. LocalGit.merge raises MergeConflictError if conflict.
    try:
        # LocalGit.merge signature: merge(source, target, strategy=None, no_ff=True)
        tree_manager.lg.merge(branch, target_branch, strategy=resolve, no_ff=not ff)
        typer.echo(f"Merged {branch} → {target_branch}")
    except Exception as e:
        # prefer specific MergeConflictError, fallback generic
        if isinstance(e, getattr(tree_manager.lg, "MergeConflictError", type(e))):
            conflicts = tree_manager.lg.repo.index.unmerged_blobs()
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
    if tree_manager.can_push(target_branch):
        tree_manager.lg.push(target_branch)
        typer.echo(f"Pushed {target_branch}.")
    else:
        typer.echo(f"Target {target_branch} is protected: push skipped.")

    # Create PR if required by trunk policy (note: often PR to trunk is not needed if already merged locally)
    if tree_manager.requires_pr(target_branch):
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
    ctx: typer.Context,
    org: str = typer.Option(..., help="Azure DevOps organization"),
    project: str = typer.Option(..., help="Azure DevOps project"),
    repo: str = typer.Option(..., help="Azure DevOps repository"),
    pat: str = typer.Option(..., help="Azure DevOps personal access token"),
):
    """Complete a merge after resolving conflicts manually."""
    # we expect user to be on the target branch (merge in progress)
    tree_manager = ctx.obj["tree_manager"]

    current_branch = tree_manager.lg.current_branch()

    # check merge in progress
    if not tree_manager.lg.repo.index.unmerged_blobs():
        typer.echo("No merge in progress. Nothing to resolve.")
        raise typer.Exit()

    typer.echo("Committing resolved merge ...")

    # Stage resolved files (add everything)
    tree_manager.lg.add(all=True)

    # Finalize merge commit
    message = f"Merge resolution on {current_branch}"
    tree_manager.lg.commit(message)
    typer.echo(f"Merge resolved and committed on {current_branch}.")

    # Determine flow/trunk context for push / PR decisions:
    # if current branch is a trunk, target_trunk = current_branch,
    # else it's likely a trunk name (since merge occurs on trunk).
    target_trunk = current_branch
    trunk_settings = tree_manager.trunks.get(target_trunk)
    if not trunk_settings:
        typer.echo(
            f"Warning: {target_trunk} is not registered as a trunk; using conservative defaults."
        )

    # Push if trunk allows it
    if tree_manager.can_push(target_trunk):
        tree_manager.lg.push(target_trunk)
        typer.echo(f"Pushed {target_trunk}.")

    # If the trunk's policy requires PRs (unusual after merge), create one
    if tree_manager.requires_pr(target_trunk):
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
