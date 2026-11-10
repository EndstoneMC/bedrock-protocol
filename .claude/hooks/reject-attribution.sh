#!/bin/sh
input=$(cat)
case $input in
*"git commit"* | *"git -C "*" commit"* | *"gh pr create"* | *"gh pr edit"*) ;;
*) exit 0 ;;
esac
if printf '%s\n' "$input" | grep -qiE '(\\n|\\"|'"'"')[a-z]+(-[a-z]+)*-by:|--trailer|generated with \[claude code\]'; then
    echo 'blocked: commits and PRs here carry no trailer or attribution line (CLAUDE.md, Commits)' >&2
    exit 2
fi
exit 0
