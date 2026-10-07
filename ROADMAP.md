# Roadmap

This roadmap keeps the project focused on a small set of useful, testable improvements.

## v0.2.0 — reliable large-file analysis

Target: make the reusable CLI more practical for real BTS-style datasets while preserving current behavior.

- [x] Accept documented official BTS uppercase column aliases.
- [x] Add a Turkish local-analysis quickstart.
- [ ] Complete and review memory-bounded CSV analysis for large files.
- [ ] Ensure streaming mode matches in-memory behavior for uppercase aliases, mixed aliases, cancellations, delay reasons, and ambiguity errors.
- [ ] Run the full Windows/Linux CI matrix on the final v0.2.0 candidate.
- [ ] Add release notes and a changelog entry.
- [ ] Tag the first maintained release after the checklist is complete.

## After v0.2.0

Keep future work evidence-driven and small in scope:

- Improve reproducible BTS data acquisition and provenance documentation.
- Add end-to-end validation against freshly downloaded official data without committing restricted or uncertain-source datasets.
- Improve packaging and release automation only after the CLI behavior is stable.
- Consider additional operational metrics only when they have a clear definition, test fixture, and user value.

## Contribution principles

- Prefer small pull requests with regression tests.
- Preserve backwards compatibility unless a change is explicitly discussed.
- Use synthetic data in tests.
- Do not add credentials, private data, or third-party datasets without clear redistribution rights.
- Keep metric definitions explicit so results are reproducible.
