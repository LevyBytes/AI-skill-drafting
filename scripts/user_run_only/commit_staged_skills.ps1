#Requires -Version 5.1

<#
.SYNOPSIS
Commits the staged changes in every skill repository under DEVSKILLS that is fully staged, with one shared message.

.DESCRIPTION
OWNER-RUN ONLY. A person types this command at an interactive PowerShell console. AI agents and other
automation must never run it, and it refuses to start when its input is piped or redirected or when
PowerShell was started with -NonInteractive.

Step 2 of 3: stage_changed_skills.ps1, then commit_staged_skills.ps1, then push_committed_skills.ps1.

Give the commit message one of two ways, never both:
  - one message in quotes, for a short commit: "Fix broken reference links"
  - -MessageFile with the path of a text file, for anything longer. Write it as Git expects: the subject
    on the first line, a blank line, then the body. The file is read as UTF-8 (a byte order mark is fine)
    and is never changed.
Either way the message is normalized (LF line endings, no blank lines at the start or end), shown in full
before you confirm, and handed to Git through a temporary file with git commit -F, so quotes, apostrophes
and other characters arrive exactly as written.

What it does:
  1. Finds every folder directly under DEVSKILLS (or -Root) that holds a .git entry.
  2. Queues only the repositories that are ready to commit: something is staged, nothing is unstaged or
     untracked, there are no conflicts, HEAD is on a branch, and no merge, rebase, cherry-pick, revert,
     bisect or other Git process is under way. Everything else is listed with the reason it is skipped.
  3. Prints the plan and the exact commit message, then asks for y or n. Anything but y or yes cancels.
  4. Commits each queued repository. Just before each one it reads the status again and skips the
     repository if anything changed since the plan.
  5. Prints a summary. It never stages or pushes.

.PARAMETER Message
One commit message in quotes. Leave it out when you use -MessageFile.

.PARAMETER MessageFile
Path of a UTF-8 text file holding the commit message. Leave out -Message when you use it.

.PARAMETER Root
The folder that holds the skill repositories. Defaults to the DEVSKILLS environment variable.

.PARAMETER Skill
Only these repositories, by folder name, for example -Skill skill-one,skill-two.

.PARAMETER DryRun
Prints the plan and the message, asks nothing and changes nothing.

.PARAMETER Help
Prints this full help and exits without reading any repository. --help, -h and /? do the same.

.EXAMPLE
cd $env:DEVSKILLS\skill-drafting
.\scripts\user_run_only\commit_staged_skills.ps1 "Fix broken reference links"

.EXAMPLE
.\scripts\user_run_only\commit_staged_skills.ps1 -MessageFile ..\commit-message.txt

.EXAMPLE
.\scripts\user_run_only\commit_staged_skills.ps1 -MessageFile ..\commit-message.txt -Skill skill-one,skill-two -DryRun

.NOTES
Exit codes: 0 finished, cancelled or nothing to do, 1 at least one repository failed, 2 refused or invalid input.
Help: .\scripts\user_run_only\commit_staged_skills.ps1 -Help prints all of this, as do --help and Get-Help <path> -Full. -? prints only the summary.
If the execution policy blocks the script, run it once with:
  powershell -ExecutionPolicy Bypass -File .\scripts\user_run_only\commit_staged_skills.ps1

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
       .\scripts\user_run_only\stage_changed_skills.ps1 -Skill skill-one,skill-two
       .\scripts\user_run_only\commit_staged_skills.ps1 -Skill skill-one,skill-two -MessageFile <absolute path>
       .\scripts\user_run_only\push_committed_skills.ps1 -Skill skill-one,skill-two
  4. Say what each step asks. Staging asks nothing. Committing prints the plan and the message, then asks
     y or n. Pushing first asks "Are you a human?", which the owner answers with the word yes, then prints
     the plan and asks y or n. Offer -DryRun on any step to see its plan without changing anything, and
     suggest the owner review the staged changes before committing.
  5. When repositories need different messages, give one commit line per group, each with its own -Skill
     list and message file, then a single push line.
Use only the parameters this help declares. Never add --force or any other git command to what you hand over.

PREPARING THE MESSAGE FILE
  - Put it outside every skill repository, for example in your scratch or work folder or in $env:TEMP,
    so the staging script can never pick it up. Never write it inside $env:DEVSKILLS\<skill>.
  - Save it as UTF-8. LF or CRLF line endings both work, and a byte order mark is dropped.
  - Line 1 is the subject: what changed, in the imperative, about 72 characters at most, for example
    "Relicense the skill to Apache-2.0". Line 2 is blank. The body follows: what changed and why, as
    short paragraphs or "- " bullet lines. Lines starting with # are kept unless your Git config sets
    commit.cleanup.
  - The same message goes to every repository committed in that run, so make it true for all of them,
    or split the run by -Skill with one file per group.
  - Name it so runs are easy to tell apart, for example skills-commit-20261023.txt.
  - Show the owner the message text as well, and put nothing in it the owner has not seen, such as secrets.
  - A one-line commit can use a quoted message instead of a file. If the text holds a double quote, a
    backtick or a dollar sign, use a file, because PowerShell treats those characters specially inside
    double quotes.
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string[]]$Message,
    [string]$MessageFile,
    [string]$Root,
    [string[]]$Skill,
    [switch]$DryRun,
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Unexpected
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
Import-Module -Name (Join-Path $PSScriptRoot 'skill_repos.psm1') -Force
$usage = 'Try: .\scripts\user_run_only\commit_staged_skills.ps1 "Your message", or -MessageFile <path>'

# Help and argument checks come before the guard, so -Help works even where the guard refuses.
# A quoted message binds to -Message by position, so a help word given there counts too.
$helpWords = @('--help', '-help', '-h', '/?', '/h')
if ($Help -or @(@($Message) + @($Unexpected) | Where-Object { $helpWords -contains $_ }).Count -gt 0) {
    Get-Help -Name $PSCommandPath -Full
    exit 0
}
if ($null -ne $Unexpected -and $Unexpected.Count -gt 0) {
    Write-Host ('Unexpected argument(s): {0}. Expected: one message in quotes, or -MessageFile <path>.' -f ($Unexpected -join ' ')) -ForegroundColor Red
    Write-Host 'Try: put a longer message in a text file and pass it with -MessageFile <path>.'
    exit 2
}

# Only a person at an interactive console gets past this; see Test-InteractiveHuman in skill_repos.psm1.
if (-not (Test-InteractiveHuman)) {
    Write-SkillRefusal -ScriptName 'commit_staged_skills.ps1'
    exit 2
}

# Exactly one message, in quotes or from -MessageFile. Either way it ends up normalized in $text.
$given = @($Message | Where-Object { $null -ne $_ })
if ($given.Count -gt 0 -and $MessageFile) {
    Write-Host 'Both a message and -MessageFile were given. Expected: exactly one of them.' -ForegroundColor Red
    Write-Host $usage
    exit 2
}
if ($given.Count -gt 1) {
    Write-Host ('{0} separate messages were given. Expected: one message in quotes.' -f $given.Count) -ForegroundColor Red
    Write-Host 'Try: put a longer message in a text file and pass it with -MessageFile <path>.'
    exit 2
}
try {
    if ($MessageFile) {
        $text = Read-SkillMessageFile -Path $MessageFile
    } elseif ($given.Count -eq 1) {
        $text = ConvertTo-SkillMessageText -Text $given[0]
        if (-not $text) { throw 'The message is empty. Expected: text between the quotes.' }
    } else {
        throw 'No commit message given. Expected: one message in quotes, or -MessageFile with the path of a text file.'
    }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host $usage
    exit 2
}

# The plan: read each repository's status and decide which ones to commit. Nothing changes before it prints.
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
    New-SkillPlanRow -Name $state.Name -Blocker (Get-SkillCommitBlocker -State $state) `
        -Detail ('commit {0} staged change(s) on {1}' -f $state.Staged, $state.Branch)
})
Write-SkillPlan -Title ('Commit plan for {0}' -f $skillRoot) -Rows $rows

# The owner sees the exact message, line by line, before being asked to confirm.
Write-Host ''
Write-Host 'Commit message:' -ForegroundColor Cyan
foreach ($line in ($text.TrimEnd("`n") -split "`n")) { Write-Host ('  | {0}' -f $line) }
$subject = ($text -split "`n")[0]
if ($subject.Length -gt 72) {
    Write-Host ('Note: the subject line is {0} characters; many tools truncate after about 72.' -f $subject.Length) -ForegroundColor Yellow
}

$ready = @($states | Where-Object { -not (Get-SkillCommitBlocker -State $_) })
$statusErrors = @($states | Where-Object { $_.Error }).Count
if ($DryRun) {
    Write-Host ''
    Write-Host ('Dry run: {0} repository(ies) would be committed. Nothing was changed.' -f $ready.Count)
    if ($statusErrors) { exit 1 }
    exit 0
}
if ($ready.Count -eq 0) {
    Write-Host ''
    Write-Host 'Nothing is ready to commit. Stage everything first (stage_changed_skills.ps1), then run this again.'
    if ($statusErrors) { exit 1 }
    exit 0
}

# The one confirmation. Anything but y or yes cancels before any commit.
Write-Host ''
if (-not (Read-SkillConfirmation -Question ('Commit {0} repository(ies) with this message?' -f $ready.Count))) {
    Write-Host 'Cancelled. Nothing was committed.'
    exit 0
}

# Git reads the message from a temporary file that is deleted when the run ends. Each repository is
# read again just before its commit and skipped if it changed since the plan.
$temporary = New-SkillMessageFile -Text $text
try {
    $results = @(foreach ($state in $ready) {
        Write-Host ''
        Write-Host ('git commit in {0}' -f $state.Name) -ForegroundColor Cyan
        Invoke-SkillCommit -Git $git -State $state -MessageFile $temporary
    })
} finally {
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
}
$code = Write-SkillSummary -Done 'committed' -Results $results
if ($statusErrors) { $code = 1 }
Write-Host 'Next: run push_committed_skills.ps1 when you want these commits on the remote.'
exit $code
