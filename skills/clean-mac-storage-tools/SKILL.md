---
name: clean-mac-storage-tools
description: Reclaim storage safely on a Mac and reach a concrete used-space
  target without deleting important data. Use whenever a user asks to clean a
  Mac, free disk space, reduce System Data, get below a storage threshold,
  repeat a previous Mac cleanup, inspect what is consuming space, or remove
  rebuildable Docker, Xcode, simulator, package-manager, cache, and
  inactive-project artifacts. Trigger even for casual requests such as "clean my
  Mac", "disk almost full", "same cleanup as last time", or "get me below 300
  GB". This skill owns macOS storage diagnosis and cleanup; it does not own
  malware removal, general performance tuning, or cleanup on Windows/Linux.
metadata: {}
compatibility: macOS 13 or later. Python 3 is recommended for the bundled
  read-only audit helper. Docker and Xcode integrations are optional.
allowed-tools: read_file run_shell
---

# Clean My Mac Storage

Reclaim only as much space as the user needs while preserving personal data, active work, application state, databases, and recoverability. Treat cleanup as a measured sequence of small, approved waves rather than a search for the maximum possible deletion.

## Protected invariants

- Audit before deleting. Never estimate the current state from memory alone.
- When the user says “same as last time” or refers to prior cleanup, inspect accessible conversation/task history before proposing actions. Recover past protected items, approvals, failed commands, and verification steps. If history is unavailable, say so and ask only which data or apps must be protected.
- Get explicit approval for each destructive wave. A broad “clean my Mac” request authorizes diagnosis, not every deletion that might free space.
- Resolve every destructive target to an exact path, runtime identifier, device identifier, cache class, or tool-owned object before acting. Do not use unresolved globs, broad recursive targets, or home-directory variables in destructive commands.
- Stop as soon as the requested threshold is met. Do not keep deleting merely because more candidates exist.
- Never trade irreplaceable data for rebuildable space. Prefer tool-supported cleanup, Trash for material user files, and reversible actions where practical.
- Measure again after every wave because APFS, purgeable space, snapshots, and sparse images make estimates imperfect.
- Verify the applications, simulators, containers, or services affected by cleanup before declaring success.
- Require fresh tool-reported Docker disk usage before every Docker cleanup proposal. Explicitly separate builder cache, images, containers, and volumes in the evidence and approval; a supplied estimate is planning context, not execution proof.

## Ownership boundary

Own end-to-end macOS storage diagnosis, candidate ranking, approval-gated cleanup, measurement, and verification.

Do not silently expand into:

- malware or security incident response;
- general Mac speed, battery, or memory tuning without a storage problem;
- Windows or Linux cleanup;
- cloud-account retention policy or backup deletion;
- uninstalling applications the user did not ask to remove.

For those requests, explain the boundary and hand off to the appropriate workflow.

## Workflow

### 1. Establish the target and recover context

Extract these facts from the current conversation and accessible history before asking anything:

- requested threshold or amount to free;
- whether the target means used space or free space;
- protected data, apps, projects, virtual machines, databases, and developer environments;
- previously approved cleanup classes;
- services that must remain running or be reopened afterward.

If the user says “below 300 GB” without another definition, interpret it as less than 300 decimal GB used on the macOS Data/APFS container. Report the binary `df` figure too so the two macOS views are not confused.

Ask a concise question only when a missing answer would materially change what may be deleted. Never make the user restate information already available in the task history.

When urgency or a “do not ask questions” instruction pressures the workflow, begin with the read-only audit and keep the response operational rather than stopping at a generic refusal. Explicitly protect personal data, application state, credentials, active work, volumes and databases, and backups; then name the first Tier A categories the audit will size. Urgency never authorizes `sudo`, broad deletion, or skipping the approval gate.

### 2. Capture a read-only baseline

Run the bundled helper when Python 3 is available:

```bash
python3 <skill-dir>/scripts/audit_macos_storage.py --target-gb 300 --json
```

Replace the target with the user's value. The helper performs no deletion. If it cannot run, collect equivalent evidence with macOS-native read-only commands.

At minimum record:

- APFS/Data volume used and available space in decimal GB;
- `df` used and available space in binary GiB;
- the exact remaining gap to the target;
- sizes of high-confidence rebuildable candidates;
- Docker disk usage when Docker is installed;
- Xcode runtimes and simulator devices when Xcode is installed;
- local Time Machine snapshots without deleting them;
- unusually large personal folders only when needed to close the remaining gap.

Do not use `sudo` for the initial audit. Permission errors are evidence; they are not permission to widen access.

### 3. Build the protection list

Protect these categories by default unless the user names an exact item and explicitly approves its removal:

- Photos libraries, Documents, Desktop, Pictures, Mail, Messages, downloads that have not been reviewed, and cloud-synced originals;
- application state under `Library/Application Support`, `Library/Containers`, and `Library/Group Containers`;
- password stores, keychains, SSH material, browser profiles, authentication state, and communication history;
- active repositories, uncommitted work, current build environments, virtual machines, and device backups;
- Docker volumes, database data, named persistent containers, and production-like local state;
- the current Xcode runtime, booted simulators, devices named as active by the user, and archives needed for distribution;
- backup snapshots or backup destinations.

An item being large does not make it disposable.

### 4. Rank candidates by confidence and impact

Present a compact table with exact size, recoverability, likely side effects, and the proposed action. Use these default tiers.

#### Tier A — rebuildable and usually low risk

- Docker build cache after `docker system df` confirms the composition;
- package-manager download caches using their official cleanup commands;
- Xcode DerivedData;
- per-application cache and log directories for apps that can be cleanly quit and reopened;
- unavailable simulator entries identified by `simctl`.

#### Tier B — rebuildable but context-sensitive

- old Xcode runtimes and shutdown simulator devices, while preserving the current runtime and every booted or user-designated device;
- inactive `node_modules`, build outputs, test artifacts, and dependency stores after verifying the project is inactive and the artifacts are reproducible;
- Android system images and inactive AVDs;
- Homebrew downloads and old package versions;
- local Time Machine snapshots, only after explaining the backup tradeoff.

#### Tier C — personal or stateful; review individually

- Downloads, Movies, disk images, archives, installers, exports, and large duplicate files;
- application support data, device backups, virtual-machine images, Docker volumes, databases, and project folders;
- installed applications.

Never include protected system files or bypass macOS protections as cleanup candidates.

### 5. Propose the smallest sufficient cleanup wave

Choose the smallest combination expected to cross the target with reasonable margin. For each wave show:

- exact targets;
- measured or tool-reported size;
- why each target is rebuildable or safe to remove;
- what will be quit, stopped, or rebuilt;
- the exact verification that follows;
- whether recovery is possible.

Ask for approval of that wave. Do not bundle Docker volumes, personal files, app state, or active developer environments into a generic cache approval.

### 6. Execute safely

Before each destructive command:

1. Re-resolve the exact target and confirm it still matches the reviewed item.
2. Ensure the target is not a symlink redirecting outside the reviewed location.
3. Quit or stop only the affected application or service when necessary.
4. Prefer the owning tool's cleanup command over filesystem deletion.
5. For material user files, prefer moving the exact item to Trash instead of permanent deletion.

Important tool boundaries:

- Docker: builder/image cache may be reviewed separately; never use a volume-pruning option or remove a named volume without its own explicit approval.
- Xcode: use `xcrun simctl` runtime/device identifiers; never delete the CoreSimulator tree directly and never remove a booted device.
- Package managers: use official cache cleanup commands and explain that dependencies will be downloaded again.
- Project artifacts: delete only exact rebuildable directories from inactive projects; preserve source, lockfiles, environment files, and uncommitted work.
- App caches: remove only cache/log locations, not similarly named application-support or group-container data.

Do not run a broad recursive deletion against a home directory, workspace root, volume root, `Library`, `Application Support`, `Containers`, or `Group Containers`.

### 7. Measure after every wave

Repeat the same disk measurements used for the baseline. Record:

- actual space recovered;
- current used and available space in GB and GiB;
- distance above or below the target;
- any discrepancy between estimated and actual recovery.

If the target is reached, stop. If not, propose the next smallest wave and request approval again.

### 8. Verify and restore normal operation

Reopen apps that were quit and restart only the services that were intentionally stopped. Verify proportionately:

- Docker daemon responsiveness plus the user's named containers and volumes;
- current Xcode runtime availability and required simulator boot state;
- active workspaces still exist and source-control state is unchanged;
- affected applications launch and retain their expected user state;
- the final disk measurement remains below the target.

If verification fails, stop further cleanup and prioritize recovery.

## Output contract

Keep a running cleanup ledger with:

1. baseline used/available space and target;
2. recovered history context and protected list;
3. ranked candidates with exact sizes and risk tiers;
4. the currently proposed destructive wave and approval status;
5. actions completed and actual space recovered;
6. final used/available space in GB and GiB;
7. verification results and anything intentionally left untouched.

Never claim success from candidate estimates. Success requires a fresh final measurement below the requested threshold and completed verification.

## Bundled helper

`scripts/audit_macos_storage.py` is a portable, read-only inventory helper. It measures the current volume, known rebuildable locations, and optional Docker/Xcode/Time Machine state. It never deletes, prunes, stops, or modifies anything.
