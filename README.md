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

当前开发线从 v0.3 early-user workflow 进入 v0.4 local beta 轨道。

v0.3 已完成的基础能力包括：

- CodeX-side MCP 工具可以生成结构化 BlendeX 请求。
- Blender add-on 可以启动本地 WebSocket 服务。
- 本地连接使用 Blender 面板显示的 session token。
- 协议层可以解析请求、返回结果和结构化错误。
- Blender 端可以扫描 Geometry Nodes 能力、检查场景、创建 carrier mesh、创建 BlendeX-owned Geometry Nodes modifier、创建节点、设置 socket value、连接 socket、设置 label，并返回 node tree 结构。
- Geometry Nodes mutation 只允许写入 BlendeX 标记拥有的 modifier 和 node group。
- 批处理 validate / dry-run 可以在执行前预览对象、modifier、节点、socket value 和 link 变化。
- mutating batch 必须通过 confirmed execution 入口执行。
- confirmed batch 会写入历史记录，并在存在安全回滚路径时支持撤销最近一次 BlendeX batch。
- CodeX-side recipe 和 planner 可以把受支持的目标转换为可确认的操作 batch。
- 项目包含单元测试、MCP probe 和 Blender background smoke test。

v0.4 的目标是把这些能力推进到 fully usable local beta：内置 recipe 要生成完整、连接、可见的 Geometry Nodes 图，而不是只创建几个未连接的节点；planner 要能提取简单参数并按 runtime capability 做安全选择；README、脚本和 smoke test 要让早期测试者可以自己安装、连接、执行、检查和撤销。

## v0.4 Development Track

当前版本：`0.38.0`。

0.4 轨道按十个小阶段推进：

- `0.31`: v0.4 baseline、release criteria、MCP probe、release check、README 清理。
- `0.32`: graph recipe DSL 与完整 batch builder。
- `0.33`: 完整 architecture / hard-surface recipes。
- `0.34`: 完整 nature / scattering recipes。
- `0.35`: planner 参数提取与 capability gating。
- `0.36`: full graph dry-run、confirmation summary、execution summary。
- `0.37`: link 和 socket value 的扩展 undo。
- `0.38`: Blender UI 与 local beta add-on packaging。
- `0.39`: real Blender smoke 与 demo prompt flows。
- `0.40`: 最终版本元数据、release docs 和 readiness audit。

设计与计划文档：

- `docs/superpowers/specs/2026-06-19-blendex-v0-4-usable-product-design.md`
- `docs/superpowers/plans/2026-06-19-blendex-v0-4-implementation.md`

## Supported v0.3 Creative Paths

当前 recipe/planner 支持这些路径，但在 v0.31 起它们仍处于 v0.4 加强前的状态：

- Modular grid tower.
- Procedural wall panel.
- Simple modular building.
- Random stone scatter.
- Ground point distribution.
- Simple grass scatter.

v0.4 会把这些路径升级成完整连接、参数化、可见的 Geometry Nodes graph batches。

## BlendeX Workflow

1. Install the packaged Blender add-on zip or enable the add-on from the source tree.
2. Start the BlendeX service in the Blender sidebar.
3. Copy the session token from the Blender sidebar.
4. Start CodeX with `BLENDEX_SESSION_TOKEN` or `BLENDEX_TOKEN` set to that token.
5. Ask CodeX to inspect Blender or plan a supported BlendeX goal.
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
- `PLANNER_UNSUPPORTED_REQUEST`: ask for one of the supported creative paths or narrow the request.
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

The script writes `dist/blendex-0.38.0-blender-addon.zip`. Install that zip from Blender Preferences > Add-ons > Install from Disk. The package includes both the Blender add-on (`blendex`) and the shared protocol package (`blendex_protocol`).

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

## v0.4 Remaining Work

- Expand real Blender smoke to cover one architecture recipe and one scattering recipe.
- Write the final readiness audit before declaring v0.4 complete.

## License

本仓库包含 GitHub 初始化时创建的开源许可证文件。发布前应确认许可证与项目计划保持一致。
