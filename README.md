# BlendeX

BlendeX 是一个正在开发中的 Blender add-on 与 CodeX plugin 项目，目标是把自然语言创作能力连接到 Blender 的 Geometry Nodes 程序化建模系统。

用户在 CodeX App 中描述想要创建的程序化内容，CodeX 将需求转换成结构化 BlendeX 操作，再通过本地 WebSocket 连接发送给 Blender。Blender 中的 BlendeX add-on 只执行 allowlisted、可验证、可审计的 Geometry Nodes 操作，不执行任意 AI 生成 Python。

## 项目愿景

Blender 的 Geometry Nodes 很强，但学习成本高。BlendeX 想让用户用自然语言表达创作意图，同时保持 Blender 场景变更明确、可预览、可确认、可检查，并在安全路径存在时可撤销。

长期目标不是“让 AI 随便写 Blender Python”，而是构建一套可扩展的 split bridge：

- CodeX 负责理解意图、扫描能力、规划结构化操作。
- CodeX-side plugin 暴露 MCP 工具并连接本地 Blender 服务。
- Blender add-on 在本地安全边界内执行 Geometry Nodes graph mutation。
- 共享协议层定义操作、错误、校验和安全约束。

## 当前状态

当前开发线已经进入 v0.5 semantic Geometry Nodes reasoning 轨道。

当前版本：`0.50.0`。

BlendeX v0.5 是一个 Geometry Nodes reasoning system：CodeX-side semantic graph planner 会先解析程序化建模意图，再依据节点语义、字段/属性/实例规则、typed graph IR、静态验证和修复循环，合成结构化 Geometry Nodes 操作。v0.4 的六个固定 recipes 仍作为兼容路径保留，但 v0.5 的达标依据不是“更多模板”。

v0.5 readiness 结果：

- held-out benchmark: 20/20 valid graph plans。
- property pass: 20/20 for expected effects and minimum graph complexity。
- Anti-Template Requirement: held-out prompts 通过 semantic graph planner、node semantics、typed graph IR、validation 和 repair 解决，不依赖 recipe id 作为答案。
- release metadata synchronized at `0.50.0`。

## v0.5 Development Track

0.5 轨道按十个小阶段推进：

- `0.41`: reasoning specification、anti-template benchmark fixture。
- `0.42`: runtime node introspection v2。
- `0.43`: planner-ready node semantics knowledge base。
- `0.44`: procedural intent model。
- `0.45`: typed graph IR and static validation。
- `0.46`: backward semantic graph planner。
- `0.47`: graph validation and repair loop。
- `0.48`: held-out procedural modeling benchmark。
- `0.49`: advanced fields、attributes、instances、group inputs。
- `0.50`: version sync、release docs、readiness audit。

设计与计划文档：

- `docs/superpowers/specs/2026-06-19-blendex-v0-5-geometry-nodes-reasoning-design.md`
- `docs/superpowers/plans/2026-06-19-blendex-v0-5-geometry-nodes-reasoning.md`

## Supported v0.5 Reasoning Scope

semantic graph planner 当前支持这些程序化建模能力域：

- Architecture and modular repetition.
- Scatter and point distribution.
- Instance on Points and Realize Instances.
- Field-driven deformation and selection masks.
- Attribute capture and Store Named Attribute.
- Material assignment with procedural selections.
- Dynamic group input metadata and validation.

Simulation zones、photoreal characters、arbitrary Blender Python、marketplace packaging、asset-store workflows are out of scope for v0.5.

## BlendeX Workflow

1. Install the packaged Blender add-on zip or enable the add-on from the source tree.
2. Start the BlendeX service in the Blender sidebar.
3. Copy the session token from the Blender sidebar.
4. Start CodeX with `BLENDEX_SESSION_TOKEN` or `BLENDEX_TOKEN` set to that token.
5. Ask CodeX to inspect Blender or plan a supported semantic Geometry Nodes goal.
6. Review the dry-run confirmation summary.
7. Execute the confirmed batch.
8. Inspect the resulting Geometry Nodes tree.
9. Use undo last batch when a safe undo path is available.

## MCP Tools

Current tool surface:

- `blendex_scan_capabilities`
- `blendex_inspect_scene`
- `blendex_create_carrier_mesh`
- `blendex_create_modifier`
- `blendex_inspect_tree`
- `blendex_create_node`
- `blendex_set_socket_value`
- `blendex_link_sockets`
- `blendex_label_node`
- `blendex_validate_batch`
- `blendex_dry_run`
- `blendex_execute_confirmed_batch`
- `blendex_batch_history`
- `blendex_inspect_batch`
- `blendex_undo_last_batch`
- `blendex_list_recipes`
- `blendex_build_recipe_batch`
- `blendex_plan_goal`

## Safety Boundary

BlendeX 明确避免把自然语言直接变成 arbitrary Python 代码运行。

当前安全设计包括：

- 协议层拒绝未 allowlist 的操作，例如 `python.exec`。
- Blender 端只执行结构化操作，不执行自由形式代码字符串。
- WebSocket 服务绑定在 `127.0.0.1`。
- 服务请求通过 Blender main-thread dispatch 执行。
- 本地 WebSocket 连接需要 session token。
- mutation 操作需要目标 Geometry Nodes modifier 和 node group 已标记 `blendex_owned`。
- `blendex_validate_batch` 和 `blendex_dry_run` 使用只读校验路径。
- MCP server 会把 Blender 端 `ok: false` 的语义错误标记为 tool error。
- capability scanner 只宣告当前实际实现的操作。
- batch history 支持检查最近操作，并在可安全回滚时提供 conservative undo。

## Troubleshooting

- `AUTH_REQUIRED`: set `BLENDEX_SESSION_TOKEN` or `BLENDEX_TOKEN`.
- `AUTH_FAILED`: copy the current token from Blender and restart the CodeX plugin process.
- `BLENDER_NOT_CONNECTED`: start the Blender service from the sidebar.
- `PLANNER_UNSUPPORTED_REQUEST`: ask for a supported procedural modeling domain or narrow the request.
- `NODE_TYPE_NOT_FOUND`: refresh capabilities or choose a recipe supported by the active Blender runtime.
- `UNDO_UNAVAILABLE`: the latest batch has no safe recorded undo path.

## Local Development

Run unit tests:

```bash
./scripts/run_unit_tests.sh
```

Run the MCP server probe:

```bash
PYTHONPATH=src:. python3 scripts/mcp_probe.py
```

Run Blender smoke test:

```bash
BLENDER=/path/to/blender python3 scripts/run_blender_smoke.py
```

When `BLENDER` is set, the smoke test executes a basic node batch plus one architecture recipe (`architecture.grid_tower`) and one scattering recipe (`scatter.ground_points`) in Blender background mode. Set `BLENDEX_GENERATED_GRAPH_SMOKE=1` as well to include a bounded generated-graph smoke pass.

If `BLENDER` is not set, the smoke script prints a clear skip message and exits successfully:

```text
SKIP: set BLENDER=/path/to/blender to run the Blender smoke test
```

Run release checks:

```bash
./scripts/run_release_checks.sh
```

The release check wrapper runs unit tests, Blender smoke, MCP probe, and `git diff --check`.

## Local Beta Add-on Package

Build an installable Blender add-on zip:

```bash
python3 scripts/package_blender_addon.py
```

The script writes `dist/blendex-0.50.0-blender-addon.zip`. Install that zip from Blender Preferences > Add-ons > Install from Disk. The package includes both the Blender add-on (`blendex`) and the shared protocol package (`blendex_protocol`).

## Demo Prompts

See `docs/demo-prompts.md` for copy-pasteable prompts covering the compatibility recipes and the dry-run, confirm, inspect, and undo flow. The v0.5 held-out reasoning benchmark lives in `docs/benchmarks/v0-5-heldout-prompts.json`.

## Source Tree Add-on Loading

During development, point Blender at the repository `blender_addon` directory. The add-on bootstraps the sibling `src` directory onto Python path so Blender can import `blendex_protocol`.

## Project Structure

```text
.
├── .codex-plugin/
│   └── plugin.json
├── blender_addon/
│   └── blendex/
├── codex_plugin/
│   └── blendex_mcp/
├── docs/
│   └── superpowers/
├── scripts/
├── src/
│   └── blendex_protocol/
└── tests/
```

## v0.5 Readiness

The final readiness audit is available at `docs/readiness-audit-v0.5.md`. v0.5 is ready for semantic Geometry Nodes reasoning within the documented procedural modeling scope.

## License

本仓库包含 GitHub 初始化时创建的开源许可证文件。发布前应确认许可证与项目计划保持一致。
