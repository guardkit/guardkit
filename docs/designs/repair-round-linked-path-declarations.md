# Protected paths reached through links: one declaration rule

This document records the implementation’s declaration rule, compatibility changes and acceptance requirements.

## Rule

A protected object may change only when the task declares its actual repository path. Aliases establish protection and explain refusals; they never grant an exemption. Factory records are excluded by their actual location.

This replaces the earlier rule that a declaration of every observed protected alias could authorize a target edit. Directory traversal deliberately visits each real folder a bounded number of times; it cannot promise to enumerate every logical alias in a graph with cycles. Making permission depend on that incomplete list is the defect.

## Actual paths and fingerprints

- A regular file uses its real repository-relative path. Distinct real paths to hardlinked files retain distinct records, even when content hashing can be shared. One arbitrary first-visited hardlink name is not authoritative.
- A symlink uses its actual directory-entry path: resolve its parent directories, but never resolve the final link for the record key. Its fingerprint includes the link text and resolved target. Declaring the link authorizes its own record; declaring its target authorizes that target record. A retarget that adds or removes actual target paths from the protected set also requires declarations of those old and new target paths, even when their bytes are unchanged.
- Retained logical names are diagnostic witnesses only. They do not affect fingerprint change detection, declarations or exemptions. A different traversal order must not turn unchanged content into a change or make a protected change disappear.
- Existing before/after records retain their diagnostic names for useful refusal messages, including deleted files. Existing in-memory record consumers remain compatible.

## Traversal and exclusions

Keep the bounded real-directory walk and protected-root reachability. Do not enumerate every alias. Every real folder is listed a bounded number of times, every protected content file is opened only if regular, and links outside the worktree are recorded without walking their targets.

Apply the factory-owned prefixes `.guardkit/` and `docs/state/` by actual location only. A logical `docs` alias into an ordinary build directory must not hide that directory's `state/README.md`. A real factory-owned target stays excluded whatever alias reaches it. Record a protected symlink outside those locations before excluding its factory-owned target, so changing that link itself remains visible.

Move the installed-package and cache exclusions currently enforced only by the caller into collection. Keep their current extent: `node_modules` and `site-packages` directory entries at any depth; `.venv*` and `.local` entries whose actual parent is the worktree root; `.tmp` and `.npm` directory entries at any depth; plus the collector's existing cache names and compiled-file suffixes. Decide these package exclusions from the entry's own name and actual parent, not the target of an alias. Thus an ordinary dependency installation remains excluded, but a protected `infra` alias into one of those directories still protects the files it exposes. A plain file with a cache directory's name remains a file. Protected symlink entries in the newly moved package/cache exclusions remain recorded before pruning their targets, preserving their previous coverage.

Every collection-time prune must depend only on an entry's own name or its actual repository location, never on a logical ancestor. This is the invariant that makes the bounded global directory-visited sets sound. Any multi-component prefix is applied to actual location. Preserve the genuine factory/orchestrator namespaces already excluded by the caller: task lifecycle folders under `tasks`, `large_tool_results`, `.claude/task-plans`, `conversation_history`, and the existing factory record names/prefixes. Do not broaden them to unrelated task or dot-directory contents. These are distinct from the package/cache exclusions above. These genuine factory targets remain excluded through any alias, while a protected link outside them is still recorded; nested `.guardkit/memory-query-log.jsonl*` records remain excluded too.

After collection, the caller treats the protected records as authoritative. It must not suppress a record merely because every retained diagnostic alias is excluded. Only genuine factory-owned and induced records may receive their existing exclusion by stable actual path. Do not use the broad orchestrator-managed-path predicate: it also includes installed packages and would erase protection through a protected alias.

## Compatibility and scope

This deliberately tightens alias-only declarations. For example, when `infra/config.txt` links to `build/runtime/config.txt`, declaring only `infra/config.txt` no longer permits changing the target. The task must declare `build/runtime/config.txt`. Declaring every observed alias also no longer permits that change. The refusal names the actual path, with aliases as explanatory context. This also tightens link-only retargeting: for `.env -> build/a.txt` retargeted to `build/b.txt`, when these targets are protected only through that link, declaring `.env` alone refuses even if both target files keep the same bytes. Declare `.env`, `build/a.txt` and `build/b.txt` to authorize the link and the protected-set membership changes. When both targets remain independently protected, only the changed link record needs a declaration. This conservative rule avoids snapshotting every otherwise unprotected file.

The ordinary non-repair path, task declaration parsing, external paths, factory-owned records and project code remain outside this change. The previous real-path positive controls stay valid. Alias-only positive controls become refusals paired with actual-path positive controls; this is an explicit contract change, not a hidden relaxation of a failed assertion.

## Acceptance

Through the existing approving-model loop, in both supported modes:

1. Three protected folder aliases to one ignored target: two aliases declared refuses; all aliases declared also refuses; the actual target declared approves.
2. A protected folder alias or file alias permits a target-content edit only when the actual target is declared. An unchanged tree still approves.
3. A nested symlink reached through several folder aliases uses its stable actual entry path for retargeting permission, independent of traversal order. Target-content changes still require the target declaration. Retargeting between otherwise unprotected targets refuses with only the link declared and approves with the link plus both actual targets declared; verify unchanged target bytes in both cases.
4. `docs` linked to an ordinary build directory cannot hide an ignored `state/README.md`: fingerprint it, refuse an undeclared edit, and approve the unchanged control.
5. A real factory-owned `docs/state` target remains excluded through aliases, but retargeting a protected link outside it remains detected.
6. Keep the ignored-target deletion, protected alias into packages, unreadable path, dangling protected link, FIFO, ancestor cycle, deep-chain and branching-link performance controls.
7. Changing only the diagnostic witness alias leaves an object's fingerprint comparison unchanged. Distinct protected real hardlink paths cannot disappear behind inode deduplication.
8. A declared dependency bump that changes protected-named files in a root `.venv`/`site-packages` installation approves; the same change reached through a protected `infra` alias is refused unless the actual file is declared. Parameterize the corresponding controls for `.local`, `.tmp` and `.npm`, and preserve same-named ordinary files and protected package/cache symlink retargeting.
9. Task lifecycle and other existing genuine factory namespaces remain excluded by actual location. A logical alias whose prefix happens to spell a factory namespace must not suppress ordinary files elsewhere. Include a protected alias into `tasks/in_progress` and a nested memory-query log. These controls cover the traversal invariant as well as the package controls.

Run the focused folder-link and neighboring repair-round suites, then full integration and unit/orchestrator counts, only through `dell-test` without xdist. Reuse the recorded baseline failures by exact identity; any new failure requires diagnosis. Record exact commands, imports, commit identities and results in the existing private evidence folder.

The implementation review continues at round 4 with every previous finding and disposition. The earlier alias-only acceptance is explicitly superseded by this reviewed rule. The separate design checkpoint does not reset implementation history or accept the current code. Aim for one bounded repair followed by the assembled review; if another blocking defect requires a different rule, report that concrete scope before another speculative pass.
