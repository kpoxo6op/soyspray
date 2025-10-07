# Create PR

## Overview

Create a well-structured pull request with proper description

## Steps

1. **Tidy up**
    - Update all `*-application.yaml` files in `playbooks/yaml/argocd-apps/`
    - Find: `targetRevision: "current-branch-name"` (note - this is example only, not actual branch name)
    - Replace with: `targetRevision: "main"`
    - Only modify where `repoURL` is `https://github.com/kpoxo6op/soyspray.git`
2. **Clean up commits**
    - Run: `git diff origin/main..HEAD` to see all changes
    - Analyze changes and group into logical commits
    - Run: `git reset --soft origin/main` (keeps all changes staged)
    - Run: `git reset` (unstage everything)
    - Stage and commit changes in logical groups:
      - Use `git add <files>` for each logical group
      - Use `git commit -m "clear message example"` for each group
      - Repeat until all changes are committed
    - Verify: `git diff origin/main` should show nothing
    - Force push: `git push --force-with-lease`
3. **Prepare branch**
    - Ensure all changes are committed
    - Push branch to remote (if not done in step 2)
    - Verify branch is up to date with main
4. **Set up PR**
    - Summarize changes clearly
    - Create PR with descriptive title and description.  Never use emojis.
