#Requires -Version 5.1

<#
.SYNOPSIS
Shared helpers for the three owner-run Git scripts in this folder.

.DESCRIPTION
stage_changed_skills.ps1, commit_staged_skills.ps1 and push_committed_skills.ps1 import this module.
It is not a command: do not run or import it yourself. Agents and other automation must not use it,
because the owner runs every git add, commit and push.

How the pieces fit:
  - Get-SkillRepository finds the repositories, Get-SkillRepoState reads each one's status, and the
    Get-Skill*Blocker functions decide whether a repository is ready for a step or why it is skipped.
  - Write-SkillPlan prints that plan, and Read-SkillConfirmation asks the owner y or n.
  - Invoke-SkillStage, Invoke-SkillCommit and Invoke-SkillPush read each repository again and act only
    if it is still ready. Write-SkillSummary reports the outcome and sets the exit code.

AI models preparing these commands for the owner: read FOR AI MODELS in the header of any of the three
scripts, and PREPARING THE MESSAGE FILE in commit_staged_skills.ps1. The blocker functions below list
every reason a repository is skipped, so you can tell the owner in advance which repositories a step
will touch.
#>

Set-StrictMode -Version 2.0

$script:OperationMarkers = [ordered]@{
    'MERGE_HEAD'       = 'merge'
    'rebase-merge'     = 'rebase'
    'rebase-apply'     = 'rebase or patch apply'
    'CHERRY_PICK_HEAD' = 'cherry-pick'
    'REVERT_HEAD'      = 'revert'
    'BISECT_LOG'       = 'bisect'
    'index.lock'       = 'another Git process (index.lock is present)'
}

function Test-InteractiveHuman {
    <#
    .SYNOPSIS
    True only for a person at an interactive console whose input comes from the keyboard.

    .DESCRIPTION
    Each script calls this before it reads any repository and refuses to start when it returns false.
    It returns false when PowerShell was started with -NonInteractive (except in the console of the
    VS Code PowerShell extension, which uses that flag yet prompts normally), when the session is not
    user-interactive, or when standard input is piped or redirected.

    For AI models: this check exists to stop you. Do not work around it by piping answers, by starting
    a console the owner cannot see, by editing or copying the scripts without it, or by running the git
    commands they wrap. Hand the owner the commands to run instead.

    .OUTPUTS
    System.Boolean
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param()
    # VS Code's PowerShell extension starts its console with -NonInteractive yet prompts normally.
    $flags = @([Environment]::GetCommandLineArgs() | Where-Object { $_ -match '^[-/]noni' })
    if ($flags.Count -gt 0 -and $Host.Name -ne 'Visual Studio Code Host') { return $false }
    if (-not [Environment]::UserInteractive) { return $false }
    if ([Console]::IsInputRedirected) { return $false }
    return $true
}

function Write-SkillRefusal {
    <#
    .SYNOPSIS
    Prints why a script refused to start and how the owner runs it instead.

    .PARAMETER ScriptName
    The file name of the refusing script, shown in the first line.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$ScriptName)
    Write-Host ''
    Write-Host ('{0} refused to start.' -f $ScriptName) -ForegroundColor Red
    Write-Host 'It runs only for a person at an interactive PowerShell console: input must come from the keyboard,'
    Write-Host 'and the session must not be started with -NonInteractive. Automation and AI agents must not run it.'
    Write-Host 'Try: open a PowerShell window yourself, cd into the skill-drafting folder, and run it from there.'
}

function Resolve-SkillRoot {
    <#
    .SYNOPSIS
    Returns the full path of the folder that holds the skill repositories.

    .DESCRIPTION
    Uses -Root when given, otherwise the DEVSKILLS environment variable, and throws when neither names
    an existing folder. Each skill repository is a folder directly under this one.

    .PARAMETER Root
    The folder to use instead of DEVSKILLS.

    .OUTPUTS
    System.String
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([string]$Root)
    if ([string]::IsNullOrWhiteSpace($Root)) { $Root = $env:DEVSKILLS }
    if ([string]::IsNullOrWhiteSpace($Root)) {
        throw 'No skill folder given. Expected: the DEVSKILLS environment variable, or -Root naming the folder that holds your skill repositories. Try: set DEVSKILLS, or pass -Root <folder>.'
    }
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw ('Skill folder not found: {0}. Expected: an existing folder that holds your skill repositories. Try: check DEVSKILLS or -Root.' -f $Root)
    }
    return (Resolve-Path -LiteralPath $Root).ProviderPath
}

function Get-GitExecutable {
    <#
    .SYNOPSIS
    Returns the path of the git executable on PATH, or throws when there is none.

    .DESCRIPTION
    Every Git call in the scripts goes through this path, so they run whichever git the owner's PATH
    finds first.

    .OUTPUTS
    System.String
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param()
    $command = @(Get-Command -Name git -CommandType Application -ErrorAction SilentlyContinue) | Select-Object -First 1
    if ($null -eq $command) {
        throw 'Git was not found on PATH. Expected: git.exe from Git for Windows. Try: install Git for Windows, or add its cmd folder to PATH.'
    }
    return $command.Path
}

function Get-SkillRepository {
    <#
    .SYNOPSIS
    Lists the skill repositories under Root, sorted by name.

    .DESCRIPTION
    A skill repository is a folder directly under Root that holds a .git folder or file. Deeper folders
    are never searched. With -Skill only the named repositories are returned, and an unknown name throws
    an error that lists every valid name.

    For AI models: the names are the repository folder names directly under $env:DEVSKILLS. In a
    command for the owner, write them comma-separated without spaces, as in
    -Skill skill-one,skill-two. After a space PowerShell passes the next name as a separate argument, and
    the scripts refuse it.

    .PARAMETER Root
    The folder that holds the skill repositories, as Resolve-SkillRoot returns it.

    .PARAMETER Skill
    Repository folder names. Each item may itself hold several names separated by commas.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [string[]]$Skill
    )
    $all = @(Get-ChildItem -LiteralPath $Root -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName '.git') } |
        Sort-Object -Property Name)
    $wanted = @()
    if ($Skill) {
        $wanted = @($Skill | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if ($wanted.Count -eq 0) { return $all }
    $names = @($all | ForEach-Object { $_.Name })
    $unknown = @($wanted | Where-Object { $names -notcontains $_ })
    if ($unknown.Count -gt 0) {
        throw ('Not a skill repository under {0}: {1}. Expected one of: {2}.' -f $Root, ($unknown -join ', '), ($names -join ', '))
    }
    return @($all | Where-Object { $wanted -contains $_.Name })
}

function Get-GitDirectory {
    <#
    .SYNOPSIS
    Returns the repository's Git directory, or an empty string when it cannot be found.

    .DESCRIPTION
    A normal clone keeps it in the .git folder. A worktree or submodule has a .git file whose first line
    reads gitdir: <path>, and a relative path there is resolved against the repository folder.

    .PARAMETER RepoPath
    The repository's working folder.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$RepoPath)
    $dotGit = Join-Path $RepoPath '.git'
    if (Test-Path -LiteralPath $dotGit -PathType Container) { return $dotGit }
    $first = Get-Content -LiteralPath $dotGit -TotalCount 1 -ErrorAction SilentlyContinue
    if ($first -match '^gitdir:\s*(.+?)\s*$') {
        $target = $Matches[1]
        if (-not [System.IO.Path]::IsPathRooted($target)) { $target = Join-Path $RepoPath $target }
        return $target
    }
    return ''
}

function Get-GitOperation {
    <#
    .SYNOPSIS
    Names an unfinished merge, rebase, cherry-pick, revert or bisect, or a running Git process.

    .DESCRIPTION
    Looks in the Git directory for the marker files listed in $script:OperationMarkers and returns the
    first one's description, or an empty string when none is present. Every step skips a repository
    with an operation under way.

    .PARAMETER GitDirectory
    The Git directory from Get-GitDirectory. Empty means there is nothing to check.
    #>
    [CmdletBinding()]
    param([string]$GitDirectory)
    if (-not $GitDirectory) { return '' }
    foreach ($name in $script:OperationMarkers.Keys) {
        if (Test-Path -LiteralPath (Join-Path $GitDirectory $name)) { return $script:OperationMarkers[$name] }
    }
    return ''
}

function Get-SkillRepoState {
    <#
    .SYNOPSIS
    Reads one repository's branch, tracking and change counts from git status --porcelain=v2 --branch.

    .DESCRIPTION
    Returns an object with these properties:
      - Name and Path
      - Branch, which is "(detached)" when HEAD is not on a branch, and Upstream
      - Ahead and Behind, as of the last fetch, because nothing here fetches
      - Staged, Unstaged, Untracked and Conflicts, counted per file. A file changed again after staging
        counts as both staged and unstaged.
      - Operation, from Get-GitOperation
      - Error, set when git status fails. The change counts are then zero.
    Every plan is built from these objects. Reading them stages, commits and pushes nothing.

    .PARAMETER Git
    The git executable from Get-GitExecutable.

    .PARAMETER Path
    The repository's working folder.

    .PARAMETER Name
    The name shown in the plan. Defaults to the folder name.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Git,
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Name
    )
    if (-not $Name) { $Name = Split-Path -Leaf $Path }
    $state = [pscustomobject][ordered]@{
        Name = $Name; Path = $Path; Branch = ''; Upstream = ''; Ahead = 0; Behind = 0
        Staged = 0; Unstaged = 0; Untracked = 0; Conflicts = 0; Operation = ''; Error = ''
    }
    $state.Operation = [string](Get-GitOperation -GitDirectory (Get-GitDirectory -RepoPath $Path))
    $lines = @(& $Git -C $Path status --porcelain=v2 --branch)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $state.Error = 'git status failed with exit code {0}' -f $exitCode
        return $state
    }
    foreach ($line in $lines) {
        $text = [string]$line
        if ($text.StartsWith('# branch.head ')) { $state.Branch = $text.Substring(14) }
        elseif ($text.StartsWith('# branch.upstream ')) { $state.Upstream = $text.Substring(18) }
        elseif ($text -match '^# branch\.ab \+(\d+) -(\d+)$') {
            $state.Ahead = [int]$Matches[1]
            $state.Behind = [int]$Matches[2]
        }
        elseif ($text -match '^[12] (.)(.) ') {
            if ($Matches[1] -ne '.') { $state.Staged++ }
            if ($Matches[2] -ne '.') { $state.Unstaged++ }
        }
        elseif ($text.StartsWith('u ')) { $state.Conflicts++ }
        elseif ($text.StartsWith('? ')) { $state.Untracked++ }
    }
    return $state
}

function Get-SkillCommonBlocker {
    <#
    .SYNOPSIS
    The reasons every step shares for skipping a repository.

    .DESCRIPTION
    Returns the first of these that applies, or an empty string when none does:
      - git status failed
      - a merge, rebase, cherry-pick, revert, bisect or other Git process is under way
      - there are unresolved conflicts

    .PARAMETER State
    A repository state from Get-SkillRepoState.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$State)
    if ($State.Error) { return $State.Error }
    if ($State.Operation) { return ('a {0} is in progress; finish or abort it first' -f $State.Operation) }
    if ($State.Conflicts) { return ('{0} unresolved conflict(s)' -f $State.Conflicts) }
    return ''
}

function Get-SkillStageBlocker {
    <#
    .SYNOPSIS
    Empty when git add -A should run in this repository, otherwise the reason it is skipped.

    .DESCRIPTION
    Skipped for any reason in Get-SkillCommonBlocker, and also when there is nothing left to stage:
    "no changes", or "already fully staged" when every change is already staged.

    For AI models: staging takes every new, modified and deleted file in the repository that .gitignore
    does not exclude. Before you hand over the staging command, make sure each repository it will touch
    holds only work the owner means to commit, and leave nothing of your own there, such as a scratch
    file or the commit message file.

    .PARAMETER State
    A repository state from Get-SkillRepoState.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$State)
    $common = Get-SkillCommonBlocker -State $State
    if ($common) { return $common }
    if (($State.Unstaged + $State.Untracked) -eq 0) {
        if ($State.Staged) { return 'already fully staged' }
        return 'no changes'
    }
    return ''
}

function Get-SkillCommitBlocker {
    <#
    .SYNOPSIS
    Empty only when everything is staged and nothing else has changed, otherwise the reason it is skipped.

    .DESCRIPTION
    Skipped for any reason in Get-SkillCommonBlocker, and also for a detached HEAD, unstaged changes,
    untracked entries, or nothing staged.

    For AI models: a repository edited after the owner staged it is skipped by the commit step until it
    is staged again. After further edits, hand over the staging command again before the commit command.

    .PARAMETER State
    A repository state from Get-SkillRepoState.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$State)
    $common = Get-SkillCommonBlocker -State $State
    if ($common) { return $common }
    if ($State.Branch -eq '(detached)') { return 'detached HEAD; check out a branch first' }
    if ($State.Unstaged) { return ('{0} unstaged change(s); stage them or set them aside first' -f $State.Unstaged) }
    if ($State.Untracked) { return ('{0} untracked entry(ies); stage or ignore them first' -f $State.Untracked) }
    if (-not $State.Staged) { return 'nothing staged' }
    return ''
}

function Get-SkillPushBlocker {
    <#
    .SYNOPSIS
    Empty only when the tree is clean, the branch tracks an upstream, and it is ahead and not behind.

    .DESCRIPTION
    Skipped for any reason in Get-SkillCommonBlocker, and also for a detached HEAD, any staged, unstaged
    or untracked work, a branch without an upstream, a branch behind its upstream, or nothing to push.
    Ahead and behind are as of the last fetch.

    For AI models: the script never pushes a branch that has no upstream. Tell the owner which
    repositories that applies to, so they can push each once themselves, rather than adding a git
    command to the bulk commands you hand over.

    .PARAMETER State
    A repository state from Get-SkillRepoState.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$State)
    $common = Get-SkillCommonBlocker -State $State
    if ($common) { return $common }
    if ($State.Branch -eq '(detached)') { return 'detached HEAD; check out a branch first' }
    if ($State.Staged -or $State.Unstaged -or $State.Untracked) {
        return ('uncommitted work: {0} staged, {1} unstaged, {2} untracked' -f $State.Staged, $State.Unstaged, $State.Untracked)
    }
    if (-not $State.Upstream) { return 'no upstream branch; push it once yourself with git push -u <remote> <branch>' }
    if ($State.Behind) { return ('behind {0} by {1} commit(s); pull or rebase first' -f $State.Upstream, $State.Behind) }
    if (-not $State.Ahead) { return 'nothing to push' }
    return ''
}

function New-SkillPlanRow {
    <#
    .SYNOPSIS
    Builds one plan line: ready with what the step will do, or skipped with the reason.

    .PARAMETER Name
    The repository name.

    .PARAMETER Blocker
    The reason from a Get-Skill*Blocker function. Empty means the repository is ready.

    .PARAMETER Detail
    What the step will do in a ready repository.
    #>
    [CmdletBinding()]
    param([string]$Name, [string]$Blocker, [string]$Detail)
    return [pscustomobject][ordered]@{ Name = $Name; Ready = (-not $Blocker); Detail = $(if ($Blocker) { $Blocker } else { $Detail }) }
}

function Write-SkillPlan {
    <#
    .SYNOPSIS
    Prints the plan: ready repositories in green, skipped ones in gray with the reason.

    .PARAMETER Title
    The heading, which names the step and the skill folder.

    .PARAMETER Rows
    Rows from New-SkillPlanRow.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Title, [object[]]$Rows)
    Write-Host ''
    Write-Host $Title -ForegroundColor Cyan
    $rowsHere = @($Rows)
    if ($rowsHere.Count -eq 0) {
        Write-Host '  (no skill repositories found)'
        return
    }
    $width = ($rowsHere | ForEach-Object { $_.Name.Length } | Measure-Object -Maximum).Maximum
    foreach ($row in $rowsHere) {
        if ($row.Ready) {
            Write-Host ('  {0}  {1}' -f $row.Name.PadRight($width), $row.Detail) -ForegroundColor Green
        } else {
            Write-Host ('  {0}  skip: {1}' -f $row.Name.PadRight($width), $row.Detail) -ForegroundColor DarkGray
        }
    }
}

function Read-SkillConfirmation {
    <#
    .SYNOPSIS
    Asks a y or n question and returns true only when the person types y or yes.

    .DESCRIPTION
    Any other answer, an empty one included, means no. The commit and push steps call it after the plan
    is printed. The push step's earlier "Are you a human?" question is asked in push_committed_skills.ps1
    itself and accepts only the full word yes.

    .PARAMETER Question
    The question without the [y/N] suffix, which is added here.

    .OUTPUTS
    System.Boolean
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param([Parameter(Mandatory = $true)][string]$Question)
    $answer = Read-Host ('{0} [y/N]' -f $Question)
    return ([string]$answer -match '^\s*(y|yes)\s*$')
}

function New-SkillResult {
    <#
    .SYNOPSIS
    Builds one summary line for a repository.

    .PARAMETER Name
    The repository name.

    .PARAMETER Status
    One of staged, committed, pushed, skipped or failed.

    .PARAMETER Detail
    What happened, shown in parentheses after the status.
    #>
    [CmdletBinding()]
    param([string]$Name, [string]$Status, [string]$Detail)
    return [pscustomobject][ordered]@{ Name = $Name; Status = $Status; Detail = $Detail }
}

function Invoke-SkillStage {
    <#
    .SYNOPSIS
    Reads the repository again, then runs git add -A only if it still needs staging.

    .DESCRIPTION
    Returns a result from New-SkillResult with the status staged, skipped (the repository changed since
    the plan) or failed (git add -A returned a nonzero exit code). Git's own output goes to the console.

    .PARAMETER Git
    The git executable from Get-GitExecutable.

    .PARAMETER State
    The repository state the plan was built from.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Git, [Parameter(Mandatory = $true)]$State)
    $fresh = Get-SkillRepoState -Git $Git -Path $State.Path -Name $State.Name
    $blocker = Get-SkillStageBlocker -State $fresh
    if ($blocker) { return New-SkillResult -Name $State.Name -Status 'skipped' -Detail ('changed since the plan: {0}' -f $blocker) }
    & $Git -C $State.Path add -A | Out-Host
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { return New-SkillResult -Name $State.Name -Status 'failed' -Detail ('git add -A failed with exit code {0}' -f $exitCode) }
    $after = Get-SkillRepoState -Git $Git -Path $State.Path -Name $State.Name
    return New-SkillResult -Name $State.Name -Status 'staged' -Detail ('{0} change(s) now staged' -f $after.Staged)
}

function ConvertTo-SkillMessageText {
    <#
    .SYNOPSIS
    Normalizes a commit message: LF line endings, no leading or trailing blank lines, one final newline.

    .DESCRIPTION
    Spaces and tabs at the very start and end are trimmed as well, so indentation on the first line is
    lost. Returns an empty string when nothing is left, and the commit step refuses an empty message.

    .PARAMETER Text
    The message as given in quotes or read from the message file.

    .OUTPUTS
    System.String
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text)
    $lines = ($Text -replace "`r`n", "`n" -replace "`r", "`n").Trim([char[]]@("`n", ' ', "`t"))
    if (-not $lines) { return '' }
    return $lines + "`n"
}

function Read-SkillMessageFile {
    <#
    .SYNOPSIS
    Reads a commit message file as UTF-8 and returns the normalized message. The file is never changed.

    .DESCRIPTION
    A UTF-8 byte order mark is allowed and dropped, LF and CRLF line endings both work, and the text goes
    through ConvertTo-SkillMessageText. It throws when the file is missing, is not valid UTF-8, or holds
    no text. A relative path is resolved against the current folder, which is the skill-drafting folder
    when the owner follows the usual cd, so an absolute path is safer.

    For AI models writing the file for the owner: put it outside every skill repository, save it as
    UTF-8, make line 1 an imperative subject of about 72 characters at most, leave line 2 blank, and put
    the body after it. The full rules are under PREPARING THE MESSAGE FILE in commit_staged_skills.ps1.

    .PARAMETER Path
    The message file, absolute or relative to the current folder.

    .OUTPUTS
    System.String
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw ('Message file not found: {0}. Expected: an existing text file holding the commit message. Try: check the path, relative to {1}.' -f $Path, (Get-Location).ProviderPath)
    }
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path).ProviderPath)
    $offset = 0
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) { $offset = 3 }
    try {
        $text = (New-Object System.Text.UTF8Encoding($false, $true)).GetString($bytes, $offset, $bytes.Length - $offset)
    } catch {
        throw ('Message file is not UTF-8 text: {0}. Expected: a UTF-8 text file. Try: save it as UTF-8 in your editor.' -f $Path)
    }
    $message = ConvertTo-SkillMessageText -Text $text
    if (-not $message) {
        throw ('Message file is empty: {0}. Expected: a subject line, optionally followed by a blank line and a body. Try: write the message into the file.' -f $Path)
    }
    return $message
}

function New-SkillMessageFile {
    <#
    .SYNOPSIS
    Writes the normalized commit message to a new temporary file and returns its path.

    .DESCRIPTION
    The file is UTF-8 without a byte order mark, which git commit -F reads as written. Passing the
    message through a file keeps quotes, apostrophes and non-ASCII characters exactly as given. The
    commit script deletes the file when the run ends.

    .PARAMETER Text
    The normalized message from ConvertTo-SkillMessageText or Read-SkillMessageFile.

    .OUTPUTS
    System.String
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][string]$Text)
    $path = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($path, $Text, (New-Object System.Text.UTF8Encoding($false)))
    return $path
}

function Invoke-SkillCommit {
    <#
    .SYNOPSIS
    Reads the repository again, then commits the staged changes only if it is still ready.

    .DESCRIPTION
    Runs git commit -F with the temporary message file, so Git's hooks and settings apply as they do to
    a commit typed by hand. Returns a result with the status committed (with how far the branch is now
    ahead of its upstream), skipped or failed.

    .PARAMETER Git
    The git executable from Get-GitExecutable.

    .PARAMETER State
    The repository state the plan was built from.

    .PARAMETER MessageFile
    The temporary file from New-SkillMessageFile.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Git,
        [Parameter(Mandatory = $true)]$State,
        [Parameter(Mandatory = $true)][string]$MessageFile
    )
    $fresh = Get-SkillRepoState -Git $Git -Path $State.Path -Name $State.Name
    $blocker = Get-SkillCommitBlocker -State $fresh
    if ($blocker) { return New-SkillResult -Name $State.Name -Status 'skipped' -Detail ('changed since the plan: {0}' -f $blocker) }
    & $Git -C $State.Path commit -F $MessageFile | Out-Host
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { return New-SkillResult -Name $State.Name -Status 'failed' -Detail ('git commit failed with exit code {0}' -f $exitCode) }
    $after = Get-SkillRepoState -Git $Git -Path $State.Path -Name $State.Name
    $tracking = 'no upstream branch'
    if ($after.Upstream) { $tracking = '{0} commit(s) ahead of {1}' -f $after.Ahead, $after.Upstream }
    return New-SkillResult -Name $State.Name -Status 'committed' -Detail $tracking
}

function Invoke-SkillPush {
    <#
    .SYNOPSIS
    Reads the repository again, then pushes its branch to its upstream only if it is still ready.

    .DESCRIPTION
    Runs a plain git push with no options such as --force, --tags or -u, so it never forces. Git's own
    push settings apply as they do to a push typed by hand. Returns a result with the status pushed,
    skipped or failed. A push the remote rejects, for example because it moved since the last fetch,
    is reported as failed.

    .PARAMETER Git
    The git executable from Get-GitExecutable.

    .PARAMETER State
    The repository state the plan was built from.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Git, [Parameter(Mandatory = $true)]$State)
    $fresh = Get-SkillRepoState -Git $Git -Path $State.Path -Name $State.Name
    $blocker = Get-SkillPushBlocker -State $fresh
    if ($blocker) { return New-SkillResult -Name $State.Name -Status 'skipped' -Detail ('changed since the plan: {0}' -f $blocker) }
    & $Git -C $State.Path push | Out-Host
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { return New-SkillResult -Name $State.Name -Status 'failed' -Detail ('git push failed with exit code {0}' -f $exitCode) }
    $after = Get-SkillRepoState -Git $Git -Path $State.Path -Name $State.Name
    return New-SkillResult -Name $State.Name -Status 'pushed' -Detail ('{0} now {1} commit(s) ahead of {2}' -f $after.Branch, $after.Ahead, $after.Upstream)
}

function Write-SkillSummary {
    <#
    .SYNOPSIS
    Prints one line per repository and the totals, then returns the exit code: 1 when anything failed, else 0.

    .PARAMETER Done
    The status that counts as done for this step: staged, committed or pushed.

    .PARAMETER Results
    Results from Invoke-SkillStage, Invoke-SkillCommit or Invoke-SkillPush.

    .OUTPUTS
    System.Int32
    #>
    [CmdletBinding()]
    [OutputType([int])]
    param([Parameter(Mandatory = $true)][string]$Done, [object[]]$Results)
    Write-Host ''
    Write-Host 'Summary' -ForegroundColor Cyan
    $all = @($Results)
    foreach ($result in $all) {
        $color = 'Green'
        if ($result.Status -eq 'skipped') { $color = 'Yellow' }
        if ($result.Status -eq 'failed') { $color = 'Red' }
        Write-Host ('  {0}: {1} ({2})' -f $result.Name, $result.Status, $result.Detail) -ForegroundColor $color
    }
    $doneCount = @($all | Where-Object { $_.Status -eq $Done }).Count
    $skipped = @($all | Where-Object { $_.Status -eq 'skipped' }).Count
    $failed = @($all | Where-Object { $_.Status -eq 'failed' }).Count
    Write-Host ('{0} {1}, {2} skipped, {3} failed.' -f $doneCount, $Done, $skipped, $failed)
    if ($failed -gt 0) { return 1 }
    return 0
}

Export-ModuleMember -Function Test-InteractiveHuman, Write-SkillRefusal, Resolve-SkillRoot, Get-GitExecutable,
    Get-SkillRepository, Get-SkillRepoState, Get-SkillStageBlocker, Get-SkillCommitBlocker, Get-SkillPushBlocker,
    New-SkillPlanRow, Write-SkillPlan, Read-SkillConfirmation, ConvertTo-SkillMessageText, Read-SkillMessageFile,
    New-SkillMessageFile, Invoke-SkillStage,
    Invoke-SkillCommit, Invoke-SkillPush, Write-SkillSummary
