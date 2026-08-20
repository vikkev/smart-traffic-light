param(
  [Parameter(Mandatory=$true)][string]$RepoUrl,
  [string]$Branch = "main",
  [Parameter(Mandatory=$true)][string]$AuthorName,
  [Parameter(Mandatory=$true)][string]$AuthorEmail,
  [switch]$Force
)

# Warning: this will replace the history on the remote branch if --Force is used.
Write-Host "Repo URL: $RepoUrl"
Write-Host "Branch: $Branch"
Write-Host "Author: $AuthorName <$AuthorEmail>"

# Initialize git repo if needed
if (-not (Test-Path ".git")) {
  git init
}

# Ensure clean index
git add -A

# Configure local author for this repo only
git config user.name "$AuthorName"
git config user.email "$AuthorEmail"

# Commit
$commitMsg = "Replace repository with workspace content"
git commit -m $commitMsg || Write-Host "No changes to commit or commit failed."

# Add or set remote
try {
  git remote remove origin 2>$null
} catch {}

git remote add origin $RepoUrl

# Push
if ($Force.IsPresent) {
  Write-Host "Pushing with --force to origin/$Branch"
  git push -u origin $Branch --force
} else {
  Write-Host "Pushing to origin/$Branch"
  git push -u origin $Branch
}

Write-Host "Done. Verify the remote repository on GitHub."