# Issue tracker: GitHub

Issues and specs live in AbdelStark/hallmark GitHub Issues.
Use the gh CLI from this clone.

- Read: gh issue view <number> --json number,title,body,labels,comments
- List: gh issue list --state open
- Create: gh issue create --title "..." --body-file <file>
- Comment: gh issue comment <number> --body-file <file>
- Label: gh issue edit <number> --add-label "..."
- Close: post the explanation first, then gh issue close <number>.

Before creating an issue, verify the target with:
gh repo view --json nameWithOwner

Use native GitHub sub-issues and dependencies when available.
Otherwise, record Part of: #<parent> and Blocked by: #<blocker>
in the issue body. A ticket is unblocked when all blockers are closed.

When a skill says to publish to the issue tracker, create an issue.
When it says to fetch a ticket, read the corresponding issue.

PRs as a request surface: no.
