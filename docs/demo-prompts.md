# BlendeX Demo Prompts

These local beta prompts are intended for a Blender session with the BlendeX add-on running and a valid session token configured for the CodeX-side plugin.

## Flow

1. Ask BlendeX to plan one supported prompt.
2. Run a dry-run and review the target, node count, links, socket values, warnings, and confirmation summary.
3. Confirm the batch only if the dry-run matches the intended scene change.
4. Inspect the resulting Geometry Nodes tree.
5. Use undo last batch when the batch reports a safe undo path.

## Architecture

- `architecture.grid_tower`: "Make a 12 level grid tower with 6 columns."
- `architecture.wall_panel`: "Create a procedural facade wall panel with 9 segments."
- `architecture.modular_building`: "Block out a simple modular building with 5 floors."

Expected behavior: each prompt should produce a carrier mesh, a BlendeX-owned Geometry Nodes modifier, visible module nodes, socket values that reflect the prompt parameters, and connected graph links.

## Scattering

- `scatter.stones`: "Scatter stones on the ground with density 45 seed 9."
- `scatter.ground_points`: "Create points on ground with density 80 seed 4."
- `scatter.grass`: "Create a grass scatter field with density 100 scale 1.5."

Expected behavior: each prompt should produce a carrier mesh, a BlendeX-owned Geometry Nodes modifier, distribution or instance nodes, parameterized density/seed/scale socket values, and connected graph links.

## Copy-Paste Session

Use this sequence for each recipe:

1. Plan: "Plan `architecture.grid_tower` from this prompt: make a 12 level grid tower with 6 columns."
2. Dry-run: "Dry-run the planned BlendeX batch and summarize what will change."
3. Confirm: "Confirm and execute the dry-run batch."
4. Inspect: "Inspect the BlendeX Geometry node tree on the generated object."
5. Undo: "Undo the last BlendeX batch."

Repeat the same dry-run, confirm, inspect, and undo flow for the remaining recipe IDs listed above.
