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

当前仓库实现的是 MVP 基础骨架，已经具备一条最小可运行的 vertical slice：

- CodeX-side MCP 工具可以生成结构化 BlendeX 请求。
- Blender add-on 可以启动本地 WebSocket 服务。
- 本地协议层可以解析请求、返回结果和结构化错误。
- Blender 端可以扫描 Geometry Nodes 能力、检查场景、创建安全允许的节点。
- `geometry_nodes.create_node` 只允许写入 BlendeX 标记拥有的 Geometry Nodes modifier。
- 项目包含单元测试和 Blender background smoke test。

这还不是完整产品，但已经建立了后续扩展自然语言创作能力所需的插件、协议、安全和测试基础。

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

MVP 当前提供三个 CodeX-side 工具：

- `blendex_scan_capabilities`
  - 扫描连接中的 Blender runtime。
  - 返回 Blender 版本、Geometry Nodes 节点类型和当前真实支持的 BlendeX 操作。

- `blendex_inspect_scene`
  - 检查当前 Blender 场景和选中对象信息。

- `blendex_create_node`
  - 在指定对象的 BlendeX-owned Geometry Nodes modifier 中创建节点。
  - 当前要求传入 `object_id` 和 `node_type`，可选 `modifier_id` 和 `label`。

## 安全边界

BlendeX MVP 明确避免直接执行 AI 生成的任意 Python。

当前安全设计包括：

- 协议层拒绝未 allowlist 的操作，例如 `python.exec`。
- Blender 端只执行结构化操作，而不是执行自由形式代码字符串。
- WebSocket 服务绑定在 `127.0.0.1`。
- 服务请求在 Blender 环境中通过 main-thread dispatch 执行，避免 socket worker 线程直接触碰 Blender API。
- `create_node` 需要目标 Geometry Nodes modifier 已标记 `blendex_owned`。
- MCP server 会把 Blender 端 `ok: false` 的语义错误标记为 tool error。
- capability scanner 只宣告当前实际实现的操作，避免 CodeX 规划不存在的能力。

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
│       ├── capabilities.py
│       ├── executor.py
│       ├── logs.py
│       ├── server.py
│       ├── state.py
│       └── ui.py
├── codex_plugin/
│   └── blendex_mcp/
│       ├── blender_client.py
│       ├── catalog.py
│       ├── server.py
│       └── tools.py
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

- Geometry Nodes graph 操作
  - 创建 Geometry Nodes modifier。
  - 连接 socket。
  - 设置 socket 默认值。
  - 标记节点 ownership。
  - 检查和返回更完整的 node tree 结构。

- 自然语言规划层
  - 让 CodeX 根据用户描述选择节点、构造图结构、分批执行。
  - 引入 dry-run 和 operation preview。
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
