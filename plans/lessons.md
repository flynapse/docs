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
