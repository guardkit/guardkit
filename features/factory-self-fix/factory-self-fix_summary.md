# Feature Spec Summary: Factory self-fix — durable receipts, command oracles, bounded judge input

**Stack**: python · **Generated**: 2026-07-25T14:35:00Z · **Scenarios**: 12 (3 smoke) ·
**Assumptions**: 5 (all low — --auto; Rich's curation lands as a dated commit) · **Review required**: Yes

## Scope
Three receipted defects from the 2026-07-25 FEAT-8737 build, fixed in guardkit by the factory
itself: (A) shadow receipts must survive immediate run shutdown; (B) `behavioural_oracle.command`
— runtime checks any tech stack can declare, same result shape, file-glob precedence, loud
timeout; (C) an env-tunable, loudly-truncating budget on the coach synthesis prompt so
task-work bundles fit the crash-tested 98,304 seat. Binding spec:
docs/factory-self-fix-scope-and-buildplan.md (§3 constraints verbatim — normal coach topology,
hermetic tests only, zero net-new failures).

## Integration with /feature-plan
    /feature-plan "Factory self-fix (three verification-layer bugs)" \
      --context features/factory-self-fix/factory-self-fix_summary.md \
      --context docs/factory-self-fix-scope-and-buildplan.md
