# Design lessons

## Product-agnostic document ingestion — 2026-10-08

- Do not connect a provider synchronization pipeline to Document Hub merely because both handle documents;
  establish ownership from the requested product boundary first.
- Do not invent source-level publication or activation when documents are intended to remain independently
  usable. Separate document outcomes from run reporting.
- Keep a shared package independent of its first product consumer. Compose the shared runner and the product
  adapter in the execution host rather than importing the product into the shared package.
- Prefer the requested operational surface. A post-run email report can replace a dashboard when configuration
  is internal and the process is product-agnostic.
- Do not expand the first release to cover every missed-run or monitoring edge case unless it protects a stated
  requirement.
- Before adding a feature-specific table, inventory existing generic run records and product document stores.
  Reuse them when they already own the lifecycle; add only the smallest relation needed for an uncovered
  invariant.
- Keep provider/source revision truth separate from product revision strategy. The shared ingestion layer may
  carry source ordinals and opaque outcomes, but parser-specific publication, visibility, removal, and rollback
  belong to the consuming product.
- Do not freeze a product binding table or cutover algorithm before tracing every existing parser family's
  persistence and retrieval paths.
- When a later task is implemented out of order, immediately reconcile earlier plan tasks with the files,
  names, dependencies, and interfaces that now exist. Mark partial scaffolding explicitly instead of asking a
  future implementer to recreate it.
- Verify plan commands in the environment and dependency state where they will actually run. A sibling package
  is not importable from the API environment before its path dependency is installed unless the plan supplies
  the temporary local import path.
- When reusing a recoverable worker primitive, carry its native execution fence end to end. A retry counter is
  useful context but may not uniquely identify a live execution; here `OneShotTake.started_at` must guard
  shared settlement, run-result writes, reporting, and product handoff.
