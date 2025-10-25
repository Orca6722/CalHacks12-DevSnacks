import subprocess
from .settings import COMMIT_MAX


def read_local_commits(max_count: int | None = None) -> list[str]:
    """Reads commit subjects from the current git repository."""
    n = max_count or COMMIT_MAX
    try:
        out = subprocess.check_output([
            "git", "log", f"-n", str(n), "--pretty=%s"
        ], text=True)
        commits = [line.strip() for line in out.splitlines() if line.strip()]
        return commits
    except Exception:
        return [
            "feat: initial commit",
            "fix: finally squashed heisenbug 😮‍💨",
            "chore: refactor cache and add tests",
            "wip: not sure why this crashes at 2am"
        ]