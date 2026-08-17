"""Orchestration.

Modules never call downward across the dependency graph. Sequencing that spans
modules lives here, and this layer owns transaction boundaries.

Route handlers and background tasks are its only members. It composes module
services and holds no domain logic of its own. `import-linter` permits this
layer to import any module; no module may import it.

See docs/01-architecture.md section 3.
"""
