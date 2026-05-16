---
name: commit
description: Stage and commit repository changes when the user asks to commit, create a git commit, or use the /commit workflow. Use this skill to review the working tree, group changes by intent, stage only relevant files, and write concise conventional commit messages.
---

# /commit

Stage and commit changes with concise, scannable commit messages.

## Instructions

1. Run `git status`, `git diff --staged`, and `git diff` in parallel.
2. Review all changes and group them by intent. If changes serve different purposes, make separate commits, one per intent. If a single intent spans many files but has logically distinct parts, break those into separate commits too.
3. For each commit:

   1. Stage only the files belonging to that intent by name. Never use `git add -A` or `git add .`. Never stage secrets (`.env`, credentials, etc.).

   2. Draft a commit message:

      - Format: `category: summary` (e.g. `feat:`, `fix:`, `chore:`, `refactor:`)
      - Summary in imperative mood, under 70 characters
      - If multiple distinct changes belong in one commit, add bullets below a blank line: one line each, no fluff
      - No co-author lines (`Co-Authored-By`) and no emojis

   3. Commit using a HEREDOC. Keep the `EOF` markers at the start of the line when running the command:

      ```
      git commit -m "$(cat <<'EOF'
      category: summary line

      - bullet if needed
      EOF
      )"
      ```

   4. If the commit fails due to pre-commit hooks (`phpstan`, linting, formatting):

      - Print the stderr output for the user to review
      - Do not retry, amend, or use `--no-verify`
      - Stop and let the user decide next steps

4. Run `git status` after all commits to verify.

Keep token usage minimal. Do not read files, explore code, or explain changes back to the user. Just commit.
