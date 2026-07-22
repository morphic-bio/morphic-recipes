#!/usr/bin/env python3
"""Validate recipe composition references against a Workbench evidence catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


REPO = Path(__file__).resolve().parent.parent
DEFAULT_RECIPE_CATALOG = REPO / "catalog.yaml"
DEFAULT_EVIDENCE_CATALOG = REPO.parent / "agentic-workbench" / "examples" / "composition_evidence" / "catalog.json"


def validate_references(recipe_catalog: dict[str, Any], evidence_catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if evidence_catalog.get("schema") != "morphic.composition_evidence_catalog/v1":
        errors.append("unsupported Workbench composition evidence catalog schema")
        return errors
    graphs = {
        str(graph.get("graph_id")): graph
        for graph in evidence_catalog.get("graphs") or []
        if isinstance(graph, dict) and graph.get("graph_id")
    }
    for recipe in recipe_catalog.get("recipes") or []:
        if not isinstance(recipe, dict):
            continue
        recipe_id = str(recipe.get("id") or "<missing-id>")
        references = recipe.get("composition_examples") or []
        if not isinstance(references, list):
            errors.append(f"recipe {recipe_id}: composition_examples must be a list")
            continue
        for reference in references:
            if not isinstance(reference, dict):
                errors.append(f"recipe {recipe_id}: composition example must be an object")
                continue
            graph_id = str(reference.get("graph_id") or "")
            graph = graphs.get(graph_id)
            if graph is None:
                errors.append(f"recipe {recipe_id}: unknown graph_id {graph_id or '<missing>'}")
                continue
            expected_kind = str(reference.get("evidence_kind") or "")
            if expected_kind != str(graph.get("evidence_kind") or ""):
                errors.append(
                    f"recipe {recipe_id}: graph {graph_id} kind is {graph.get('evidence_kind')}, not {expected_kind}"
                )
            if expected_kind == "observed_provenance":
                source = graph.get("source_manifest") if isinstance(graph.get("source_manifest"), dict) else {}
                expected_run = f"runs/{source.get('project')}/{source.get('run_id')}"
                if str(reference.get("provenance_run") or "") != expected_run:
                    errors.append(
                        f"recipe {recipe_id}: graph {graph_id} provenance_run must be {expected_run}"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipes", type=Path, default=DEFAULT_RECIPE_CATALOG)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE_CATALOG)
    args = parser.parse_args()

    recipes = yaml.safe_load(args.recipes.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    errors = validate_references(recipes, evidence)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    reference_count = sum(len(recipe.get("composition_examples") or []) for recipe in recipes.get("recipes") or [])
    print(f"Validated {reference_count} recipe composition references against {evidence.get('graph_count')} graphs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
