#Requires -Version 5.1

<#
.SYNOPSIS
Pushes every skill repository under DEVSKILLS whose work is all committed and ahead of its upstream branch.

.DESCRIPTION
OWNER-RUN ONLY, AND THE MOST DANGEROUS OF THE THREE: it publishes commits to your remotes. A person types
this command at an interactive PowerShell console. AI agents and other automation must never run it, and
it refuses to start when its input is piped or redirected or when PowerShell was started with -NonInteractive.

Step 3 of 3: stage_changed_skills.ps1, then commit_staged_skills.ps1, then push_committed_skills.ps1.

Two confirmations guard it. First it asks whether you are a human and accepts only the full word yes.
Then it shows the plan and asks for y or n. Anything else cancels.

What it does:
  1. Asks the human question.
  2. Finds every folder directly under DEVSKILLS (or -Root) that holds a .git entry.
  3. Queues only the repositories that are ready to push: nothing staged, unstaged or untracked, no
     conflicts, HEAD on a branch that tracks an upstream, at least one commit ahead and none behind, and
     no merge, rebase, cherry-pick, revert, bisect or other Git process under way. Everything else is
     listed with the reason it is skipped.
  4. Prints the plan and asks for y or n.
  5. Runs git push in each queued repository, which sends the branch to its upstream. It never forces.
     Just before each one it reads the status again and skips the repository if anything changed.
  6. Prints a summary.

Ahead and behind counts come from your last fetch; the script does not fetch. If the remote moved since
then, Git rejects that push and the summary reports it as failed. A branch without an upstream is skipped:
push it once yourself with git push -u.

.PARAMETER Root
The folder that holds the skill repositories. Defaults to the DEVSKILLS environment variable.

.PARAMETER Skill
Only these repositories, by folder name, for example -Skill gimp,lumberyard.

.PARAMETER DryRun
Asks the human question, prints the plan, and pushes nothing.

.PARAMETER Help
Prints this full help and exits without reading any repository. --help, -h and /? do the same.

.EXAMPLE
cd $env:DEVSKILLS\skill-drafting
.\scripts\user_run_only\push_committed_skills.ps1

.EXAMPLE
.\scripts\user_run_only\push_committed_skills.ps1 -DryRun

.EXAMPLE
.\scripts\user_run_only\push_committed_skills.ps1 -Skill gimp,lumberyard

.NOTES
Exit codes: 0 finished, cancelled or nothing to do, 1 at least one repository failed, 2 refused or invalid input.
Help: .\scripts\user_run_only\push_committed_skills.ps1 -Help prints all of this, as do --help and Get-Help <path> -Full. -? prints only the summary.
If the execution policy blocks the script, run it once with:
  powershell -ExecutionPolicy Bypass -File .\scripts\user_run_only\push_committed_skills.ps1

FOR AI MODELS: HOW TO PREPARE THESE COMMANDS FOR THE OWNER
The owner runs every git add, commit and push themselves. Never run these three scripts, and never run any
git command yourself, read-only ones such as git status included. Reading this help is fine: -Help,
--help and Get-Help -Full print it and touch nothing. Your job is to hand the owner commands to paste into
their own PowerShell window.

When the owner asks for their bulk git commands, for example "give me my bulk git skill commands for the
changes we made so far":
  1. List the skill repositories you changed. Each skill is a folder directly under $env:DEVSKILLS. Use
     your own record of the files you edited, because you cannot ask git. If you are unsure, leave -Skill
     out: every script detects which repositories are ready and skips the rest with a reason.
  2. Write the commit message file as described under PREPARING THE MESSAGE FILE in
     commit_staged_skills.ps1, unless one short line is enough.
  3. Hand over one PowerShell code block in this order. Use -Skill with the folder names, comma-separated
     and without spaces, or leave it out for every repository. Give the message file's absolute path.
       cd $env:DEVSKILLS\skill-drafting
       .\scripts\user_run_only\stage_changed_skills.ps1 -Skill gimp,lumberyard
       .\scripts\user_run_only\commit_staged_skills.ps1 -Skill gimp,lumberyard -MessageFile <absolute path>
       .\scripts\user_run_only\push_committed_skills.ps1 -Skill gimp,lumberyard
  4. Say what each step asks. Staging asks nothing. Committing prints the plan and the message, then asks
     y or n. Pushing first asks "Are you a human?", which the owner answers with the word yes, then prints
     the plan and asks y or n. Offer -DryRun on any step to see its plan without changing anything, and
     suggest the owner review the staged changes before committing.
  5. When repositories need different messages, give one commit line per group, each with its own -Skill
     list and message file, then a single push line.
Use only the parameters this help declares. Never add --force or any other git command to what you hand over.
The message file rules are under PREPARING THE MESSAGE FILE in commit_staged_skills.ps1.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Root,
    [string[]]$Skill,
    [switch]$DryRun,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Unexpected
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
Import-Module -Name (Join-Path $PSScriptRoot 'skill_repos.psm1') -Force

# Help and argument checks come before the guard, so -Help works even where the guard refuses.
$helpWords = @('--help', '-help', '-h', '/?', '/h')
if ($Help -or @($Unexpected | Where-Object { $helpWords -contains $_ }).Count -gt 0) {
    Get-Help -Name $PSCommandPath -Full
    exit 0
}
if ($null -ne $Unexpected -and $Unexpected.Count -gt 0) {
    Write-Host ('Unexpected argument(s): {0}. Expected: only the parameters that -Help lists.' -f ($Unexpected -join ' ')) -ForegroundColor Red
    Write-Host 'Try: separate -Skill names with commas and no spaces, for example -Skill gimp,lumberyard.'
    exit 2
}

# Only a person at an interactive console gets past this; see Test-InteractiveHuman in skill_repos.psm1.
if (-not (Test-InteractiveHuman)) {
    Write-SkillRefusal -ScriptName 'push_committed_skills.ps1'
    exit 2
}

# The first confirmation, before any repository is read. Only the full word yes continues.
Write-Host ''
$human = Read-Host 'Are you a human? This script is only for user invocation for safety reasons. Type yes to continue'
if ([string]$human -notmatch '^\s*yes\s*$') {
    Write-Host 'Cancelled. Nothing was pushed.'
    exit 2
}

# The plan: read each repository's status and decide which ones to push. Nothing changes before it prints.
try {
    $skillRoot = Resolve-SkillRoot -Root $Root
    $git = Get-GitExecutable
    $repos = @(Get-SkillRepository -Root $skillRoot -Skill $Skill)
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 2
}

$states = @(foreach ($repo in $repos) { Get-SkillRepoState -Git $git -Path $repo.FullName -Name $repo.Name })
$rows = @(foreach ($state in $states) {
    New-SkillPlanRow -Name $state.Name -Blocker (Get-SkillPushBlocker -State $state) `
        -Detail ('push {0} commit(s) on {1} to {2}' -f $state.Ahead, $state.Branch, $state.Upstream)
})
Write-SkillPlan -Title ('Push plan for {0}' -f $skillRoot) -Rows $rows

$ready = @($states | Where-Object { -not (Get-SkillPushBlocker -State $_) })
$statusErrors = @($states | Where-Object { $_.Error }).Count
if ($DryRun) {
    Write-Host ''
    Write-Host ('Dry run: {0} repository(ies) would be pushed. Nothing was pushed.' -f $ready.Count)
    if ($statusErrors) { exit 1 }
    exit 0
}
if ($ready.Count -eq 0) {
    Write-Host ''
    Write-Host 'Nothing is ready to push.'
    if ($statusErrors) { exit 1 }
    exit 0
}

# The second confirmation, after the owner has seen the plan.
Write-Host ''
if (-not (Read-SkillConfirmation -Question ('Push {0} repository(ies) to their upstream branches now?' -f $ready.Count))) {
    Write-Host 'Cancelled. Nothing was pushed.'
    exit 0
}

# Each repository is read again just before git push and skipped if it changed since the plan.
$results = @(foreach ($state in $ready) {
    Write-Host ''
    Write-Host ('git push in {0}' -f $state.Name) -ForegroundColor Cyan
    Invoke-SkillPush -Git $git -State $state
})
$code = Write-SkillSummary -Done 'pushed' -Results $results
if ($statusErrors) { $code = 1 }
exit $code
