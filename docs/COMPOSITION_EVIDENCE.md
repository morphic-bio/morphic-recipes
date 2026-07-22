# Composition evidence

Canonical recipes can reference Workbench composition evidence through the
`composition_examples` field in `catalog.yaml`. These references let humans and
agents inspect how a recipe or component was assembled in a source workflow or
completed MorPhiC run without making that example an automatic execution plan.

The evidence catalog and contract are maintained in `agentic-workbench`:

```text
examples/composition_evidence/catalog.json
docs/RUNBOOK_COMPOSITION_EVIDENCE_CATALOG.md
```

Each recipe reference contains:

- `graph_id`: stable Workbench evidence graph identifier;
- `evidence_kind`: source architecture, observed provenance, or example
  composition;
- `provenance_run`: supporting path in `morphic-provenance`, when applicable.

Evidence graphs are explicitly non-runnable. Agents may use them as compositor
hints, but must retain source and validation levels and request review before
turning a modified graph into an execution recipe.

When adding a reference:

1. Regenerate the Workbench catalog from the pinned source or provenance run.
2. Confirm the graph ID and evidence hashes are stable.
3. Confirm no credentials, command contents, or host-local artifact paths were
   embedded.
4. Add the reference to `catalog.yaml`.
5. Run `python3 scripts/render_recipe_catalog.py`.
6. Run `python3 scripts/validate_composition_evidence_refs.py` with sibling
   `agentic-workbench` and `morphic-recipes` checkouts, or pass explicit
   `--evidence` and `--recipes` paths.
