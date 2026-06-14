# BlendeX

BlendeX 是一个正在开发中的 Blender 插件与 CodeX 插件项目，目标是把自然语言创作能力连接到 Blender 的 Geometry Nodes 程序化建模系统。

用户未来可以在 CodeX App 中用自然语言描述想要创建的内容，CodeX 将需求转换成结构化操作，再通过本地连接发送给 Blender。安装在 Blender 中的 BlendeX add-on 会接收这些操作，并在安全边界内创建或修改 Geometry Nodes 节点网络。

## 项目愿景

Blender 本身拥有强大的程序化创作能力，尤其是 Geometry Nodes。但节点系统的学习成本较高，用户往往需要理解大量节点、socket、modifier、数据流和 Blender Python API。

BlendeX 想解决的问题是：

- 让用户用自然语言表达创作意图。
- 让 CodeX 理解 Blender 当前可调用的节点、工具和安全操作。
- 让 Blender 本地插件执行结构化、可验证、可回滚的 Geometry Nodes 操作。
- 避免让 AI 直接执行任意 Python，从而降低误改场景、破坏工程或执行危险代码的风险。

这个项目的长期目标不是简单地“让 AI 写 Blender Python”，而是构建一套可扩展的桥接协议：CodeX 负责理解与规划，Blender 插件负责受控执行，二者通过明确的能力扫描和结构化消息协作。

## 当前状态

当前仓库实现的是 v0.3 early-user creative workflow，已经具备一条从规划到确认执行再到检查和撤销的可运行 Geometry Nodes 操作链：

- CodeX-side MCP 工具可以生成结构化 BlendeX 请求。
- Blender add-on 可以启动本地 WebSocket 服务。
- 本地协议层可以解析请求、返回结果和结构化错误。
- Blender 端可以扫描 Geometry Nodes 能力、检查场景、创建承载 mesh、创建 Geometry Nodes modifier、创建节点、设置 socket value、连接 socket、设置 label，并返回 node tree 结构。
- Geometry Nodes mutation 只允许写入 BlendeX 标记拥有的 modifier 和 node group。
- 批处理 validate / dry-run 可以在执行前预览对象、modifier、节点、socket value 和 link 变化。
- 本地连接需要会话 token，避免未授权客户端直接驱动 Blender。
- CodeX-side recipe 和 planner 可以把受支持的自然语言目标转换为可确认的操作 batch。
- confirmed batch 会写入历史记录，并支持撤销最近一次 BlendeX batch。
- 项目包含单元测试和 Blender background smoke test。

这仍然是 early-user 版本，而不是完整产品。它的目标是让早期用户可以安全试用一组明确支持的程序化创作路径，并为后续更开放的自然语言建模能力打基础。

## Development Track

BlendeX v0.3 is the early-user creative workflow track.
The current loop is: plan, dry-run, confirm, execute, inspect, retry, and undo BlendeX-owned Geometry Nodes changes from CodeX.

## BlendeX v0.3 Early User Workflow

1. Enable the Blender add-on from the source tree.
2. Start the BlendeX service in Blender.
3. Copy the session token from the Blender sidebar.
4. Start CodeX with `BLENDEX_SESSION_TOKEN` set to that token.
5. Ask CodeX to run `blendex_plan_goal`.
6. Review the dry-run confirmation summary.
7. Execute the confirmed batch.
8. Inspect the resulting Geometry Nodes tree.
9. Use undo last batch when needed.

## Supported v0.3 Creative Paths

- Modular grid tower.
- Procedural wall panel.
- Simple modular building.
- Random stone scatter.
- Ground point distribution.
- Simple grass scatter.

## Troubleshooting

- `AUTH_REQUIRED`: set `BLENDEX_SESSION_TOKEN`.
- `AUTH_FAILED`: copy the current token from Blender.
- `PLANNER_UNSUPPORTED_REQUEST`: ask for one of the supported v0.3 creative paths.
- `UNDO_UNAVAILABLE`: no safe BlendeX batch undo is available.

## 架构概览

BlendeX 采用 Split Bridge 架构：

```text
CodeX App
  |
  | MCP tools
  v
CodeX BlendeX plugin
  |
  | local WebSocket / structured protocol
  v
Blender BlendeX add-on
  |
  | guarded bpy / Geometry Nodes operations
  v
Blender scene and Geometry Nodes node trees
```

核心分层：

- `src/blendex_protocol`
  - 共享协议层。
  - 定义请求、响应、错误码、操作白名单和基础校验。

- `blender_addon/blendex`
  - Blender add-on。
  - 提供 UI 面板、运行状态、操作日志、本地 WebSocket 服务、能力扫描和 Geometry Nodes executor。

- `codex_plugin/blendex_mcp`
  - CodeX 插件侧 MCP server。
  - 暴露工具定义，并把工具调用转换成 BlendeX 结构化操作。

- `tests`
  - 协议、Blender add-on fake runtime、MCP server/client 和集成 smoke 的测试。

## 当前 MCP 工具

v0.3 目标工具面包括：

- `blendex_scan_capabilities`
  - 扫描连接中的 Blender runtime。
  - 返回 Blender 版本、Geometry Nodes 节点类型、socket metadata、语义 catalog 匹配和真实支持的 BlendeX 操作。

- `blendex_inspect_scene`
  - 检查当前 Blender 场景、选中对象、modifier、Geometry Nodes node group 和 BlendeX ownership。

- `blendex_create_carrier_mesh`
  - 创建一个用于承载程序化 Geometry Nodes 图的基础 mesh object。

- `blendex_create_modifier`
  - 在目标对象上创建 BlendeX-owned Geometry Nodes modifier。

- `blendex_inspect_tree`
  - 检查目标 Geometry Nodes tree 的 nodes、sockets、links、labels 和 ownership metadata。

- `blendex_create_node`
  - 在 BlendeX-owned Geometry Nodes modifier 中创建节点。

- `blendex_set_socket_value`
  - 设置节点 input socket 默认值，并在写入前做 socket 与 value 类型校验。

- `blendex_link_sockets`
  - 连接 output socket 到 input socket，并在写入前做方向和基础类型校验。

- `blendex_label_node`
  - 设置节点 label，帮助 CodeX 创建可读图结构。

- `blendex_validate_batch`
  - 验证一组结构化操作，不修改 Blender 场景。

- `blendex_dry_run`
  - 返回一组结构化操作的预览，包括将创建的节点、链接和 socket value 变化。

- `blendex_execute_confirmed_batch`
  - 在用户确认后执行 batch，并写入 batch history。

- `blendex_batch_history`
  - 列出最近的 BlendeX batch 执行记录。

- `blendex_inspect_batch`
  - 根据 batch id 检查一次已记录的 BlendeX batch。

- `blendex_undo_last_batch`
  - 在可用时撤销最近一次安全的 BlendeX batch。

- `blendex_list_recipes`
  - 列出可用的 v0.3 本地 recipe。

- `blendex_build_recipe_batch`
  - 根据 recipe 和参数生成可 dry-run / confirmed execute 的操作 batch。

- `blendex_plan_goal`
  - 根据自然语言目标选择受支持的 recipe，或返回带 retry hint 的 unsupported planner error。

## 安全边界

BlendeX v0.3 明确避免直接执行 AI 生成的任意 Python，也就是避免把自然语言直接变成 arbitrary Python 代码运行。

当前安全设计包括：

- 协议层拒绝未 allowlist 的操作，例如 `python.exec`。
- Blender 端只执行结构化操作，而不是执行自由形式代码字符串。
- WebSocket 服务绑定在 `127.0.0.1`。
- 服务请求在 Blender 环境中通过 main-thread dispatch 执行，避免 socket worker 线程直接触碰 Blender API。
- mutation 操作需要目标 Geometry Nodes modifier 和 node group 已标记 `blendex_owned`。
- `blendex_validate_batch` 和 `blendex_dry_run` 使用只读校验路径，不创建节点、不连接 socket、不写 socket value。
- MCP server 会把 Blender 端 `ok: false` 的语义错误标记为 tool error。
- capability scanner 只宣告当前实际实现的操作，避免 CodeX 规划不存在的能力。
- 本地 WebSocket 连接需要 Blender UI 中显示的 session token。
- mutation batch 必须经过 confirmed execution 入口。
- batch history 支持检查最近操作，并提供 conservative undo last batch。

后续版本仍需要继续加强权限、确认、批处理验证、撤销和打包安装流程。

## 本地开发

### 运行单元测试

```bash
./scripts/run_unit_tests.sh
```

当前测试覆盖协议、MCP 工具映射、WebSocket client/server、Blender add-on 状态、Geometry Nodes executor 和安全边界。

### 运行 Blender smoke test

如果本机安装了 Blender，可以指定 Blender 可执行文件：

```bash
BLENDER=/path/to/blender python3 scripts/run_blender_smoke.py
```

如果没有设置 `BLENDER`，脚本会输出 skip 信息并以状态码 0 退出：

```text
SKIP: set BLENDER=/path/to/blender to run the Blender smoke test
```

v0.3 smoke test 会覆盖：

- 创建 BlendeX-owned Geometry Nodes modifier。
- 创建至少两个 Geometry Nodes 节点。
- inspect tree 返回创建后的节点结构。
- 执行一个 confirmed batch。
- 撤销最近一次 BlendeX batch。

### Source tree 方式加载 Blender add-on

开发阶段可以让 Blender 指向仓库中的 `blender_addon` 目录。add-on 在 source tree 中运行时会自动把同级 `src` 目录加入 Python path，从而让 Blender 端可以导入共享协议包 `blendex_protocol`。

## 当前项目结构

```text
.
├── .codex-plugin/
│   └── plugin.json
├── blender_addon/
│   └── blendex/
│       ├── __init__.py
│       ├── batches.py
│       ├── capabilities.py
│       ├── executor.py
│       ├── history.py
│       ├── logs.py
│       ├── safety.py
│       ├── scene.py
│       ├── server.py
│       ├── state.py
│       └── ui.py
├── codex_plugin/
│   └── blendex_mcp/
│       ├── blender_client.py
│       ├── catalog.py
│       ├── planner.py
│       ├── recipes.py
│       ├── server.py
│       ├── tools.py
│       ├── version.py
│       └── workflow.py
├── docs/
│   └── superpowers/
│       ├── plans/
│       └── specs/
├── scripts/
│   ├── run_blender_smoke.py
│   └── run_unit_tests.sh
├── src/
│   └── blendex_protocol/
└── tests/
```

## 后续路线图

接下来可以继续扩展这些方向：

- 自然语言规划层
  - 让 CodeX 根据用户描述选择节点、构造图结构、分批执行。
  - 使用 dry-run 和 operation preview 先发现明显失败，再执行真实 mutation。
  - 在失败时给出可恢复的 retry hint。

- Blender 端能力扫描
  - 扫描节点 socket 模板。
  - 扫描当前对象、modifier、node group 和 selection。
  - 提供更适合模型规划的语义 catalog。

- 安全和可靠性
  - 更完整的 ownership 规则。
  - 操作批处理验证。
  - undo last batch。
  - 用户确认机制。
  - 本地连接鉴权。

- 产品化
  - Blender add-on 打包安装。
  - CodeX plugin marketplace 安装流程。
  - 更友好的 Blender UI 状态和日志。
  - 示例项目和演示场景。

## License

本仓库包含 GitHub 初始化时创建的开源许可证文件。后续发布前应确认许可证与项目计划保持一致。
