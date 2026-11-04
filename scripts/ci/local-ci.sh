#!/usr/bin/env bash
# Test only committed files, attest that exact tree, then push the PR branch.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
mode=${1:-}
case "$mode" in ''|--dry-run|--no-push) ;; *) echo 'Use [--dry-run|--no-push]' >&2; exit 2 ;; esac
sha=$(git rev-parse HEAD)
tree=$(git rev-parse 'HEAD^{tree}')
branch=$(git branch --show-current)
[ -n "$branch" ] && [ "$branch" != main ] || { echo 'Use a PR branch' >&2; exit 1; }
git fetch --quiet origin main
git merge-base --is-ancestor origin/main "$sha" || { echo 'Update branch from origin/main first' >&2; exit 1; }
repo=$(git remote get-url origin | sed -E 's#^.*[:/]([^/:]+/[^/]+)$#\1#; s#\.git$##')
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || exit 1
owner=${repo%%/*}
if [ "$mode" != --dry-run ]; then
  gh auth status
  [ "$(gh api user --jq .login)" = "$owner" ] || { echo 'Active GitHub account must be the repository owner' >&2; exit 1; }
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/cortex-ci.XXXXXX")
ref="refs/local-ci/$sha"
published=0
cleanup() {
  code=$?
  git -C "$root" worktree remove --force "$work" >/dev/null 2>&1 || true
  if [ "$published" = 1 ]; then git -C "$root" push --quiet origin ":$ref" || true; fi
  exit "$code"
}
trap cleanup EXIT
git worktree add --quiet --detach "$work" "$sha"
(
  cd "$work"
  env -i HOME="$HOME" PATH="$PATH" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" bash scripts/ci/run.sh
)
[ "$mode" != --dry-run ] || exit 0
# Non-branch reference makes the commit available for status without triggering CI.
git push --quiet origin "$sha:$ref"
published=1
gh api -X POST "repos/$repo/statuses/$sha" -f state=success -f context=local-ci -f description="tree $tree" --silent
if [ "$mode" != --no-push ]; then
  [ "$(git rev-parse HEAD)" = "$sha" ] || { echo 'HEAD changed during CI; refusing push' >&2; exit 1; }
  git push origin "HEAD:refs/heads/$branch"
fi
