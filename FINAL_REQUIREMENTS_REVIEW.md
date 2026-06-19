# CTF Agent Skills 最终需求回顾与设计总结

日期：2026-06-18  
套件版本：`0.39.0`  
产物目录：`/Users/bytedance/Documents/CTF UP！/ctf-agent-skills`

## 1. 总体结论

最开始的目标是：围绕“如何让 AI / Agent 更丝滑地打 CTF”做升华性质研究，并最终把研究成果固化为一套可安装、可复用、带工具/MCP/脚本/状态机/安全边界的 skills。

客观评估：主体目标已经达成，并形成了一个工程化 skill suite。它不是单个“自动解题脚本”，而是一套围绕成熟 code agent 的 CTF 工作系统：

- 9 个 installable skills，覆盖 master 路由、Web、Pwn/Rev、Forensics/Crypto、Specialty、工具 preflight、知识蒸馏、反注入、handoff/report。
- 30+ 个辅助脚本，覆盖 state/profile/evidence/gate/checkpoint、工具检查、路由、报告、forward-test、benchmark、release audit。
- 需求 traceability、source matrix、phase-two research report、reflection audit、release gate、unit tests、synthetic demos、benchmark run 均已落地。
- 默认 completion audit 保持诚实：strict fresh-agent verified pass 仍是 partial；根据用户明确决策，最终 v4 fresh-agent rerun 被 waiver 接受，当前目标按 user-waived completion 收口。

换句话说：这套产物已经可以作为“成熟 code agent + CTF skills + 工具适配 + 状态机 + 知识库 + 安全边界”的第一版工程体系使用。仍不应夸大为“所有 CTF 类别都已实战证明高 solve-rate”。

## 2. 原始目标逐项达成评估

| 原始需求 | 达成程度 | 如何达成 | 主要证据 |
|---|---|---|---|
| 让 AI 更丝滑连接和使用 MCP、插件、bash、自定义脚本，减少工具/环境报错和上下文爆炸 | 基本达成 | 建立 `ctf-tool-preflight`、ToolCard、MCP adapter reference、环境 preflight、长输出摘要、失败分类、release gate 中的工具验证 | `skills/ctf-tool-preflight/`, `skills/ctf-master/scripts/summarize_output.py`, `scripts/audit_quality.py` |
| 高效理解题意，进行白盒代码审计或定位关键文件信息 | 达成 | 建立 `ChallengeProfile`、artifact triage、deep-topic router、category skill triage checklist、状态机和 evidence gate | `skills/ctf-master/references/state-schema.md`, `route_topic.py`, category skill references |
| 通过网络搜索或知识库搜集信息，保证知识颗粒度和匹配度 | 达成工程框架，未绑定单一在线搜索实现 | 建立 `ctf-knowledge`、source matrix、distillation rules，强调 source rating、fit rating、skill conversion；避免把大 payload/writeup 原样塞进上下文 | `skills/ctf-knowledge/`, `research/seed-source-matrix.md`, `scripts/audit_source_matrix.py` |
| 系统规划解题流程，随时总结进展、处理卡壳、异常、错误、选择工具/搜索/人工介入/继续深入 | 达成 | 建立 `CTFRunState`、checkpoint、phase gates、acceptance gates、handoff template、reflection renderer；将卡壳恢复从主观判断转为状态机 | `ctf-loop.md`, `phase-gates.md`, `gate_state.py`, `checkpoint_state.py`, `ctf-handoff-report/` |
| 对抗出题人反 AI 措施：隐藏 prompt、误导、强 GUI/视觉、超大文本、复杂混淆 | 部分到基本达成 | Prompt injection、fake flag、tool poisoning、long-output/visual/OCR 边界已固化；强 GUI/视觉场景被归入 browser/MCP/human intervention 工作流，但未实现通用视觉求解器 | `ctf-anti-injection/`, `visual-and-longtext.md`, `browser-workflow.md`, `scan_untrusted_text.py` |
| 根据模型特征选择模型，应对不同任务，考虑安全护栏差异 | 按后续要求弱化，部分达成 | 没做复杂模型路由，也没有构建“规避安全护栏”的模型选择策略；改为通过 handoff packet、fresh-agent packet、固定总结模板支持换模型/换人工继续 | `ctf-handoff-report/`, `forward-tests/`, `audit_completion.py` |
| 宏观上选择成熟 code agent + skills 还是专用安全 Agent，重模型还是重系统结构 | 达成 | 研究结论选择短中期混合路线：成熟 code agent 为主，skills、MCP/tool adapter、状态机、证据门禁增强；专用平台作为未来路线 | `research/phase-two-research-report.md`, `research/requirements-traceability.md` |
| 比赛/题目有本地环境、设备、网络、VPS/OOB 等需求时快速部署和判断 | 达成框架 | 环境 preflight 覆盖 VPN、proxy、Docker、VM、browser、IDA/Ghidra、Sage/z3、VPS/OOB 等；通过 `ChallengeProfile` 记录 target/scope/credentials | `environment-preflight.md`, `ctf_preflight.py`, `update_profile.py` |

## 3. 分阶段目标达成情况

### 阶段一：需求理解与研究框架

状态：已达成。

达成方式：

- 将目标从“自动解题脚本”重述为“成熟 code agent + CTF skills + MCP/tools + 状态机 + 知识库 + 安全边界”的工程体系。
- 明确安全边界：合法 CTF、授权靶场、授权研究、本地隔离环境。
- 提前定义核心接口：`ChallengeProfile`、`ToolCard`、`CTFRunState`、`EvidenceRecord`、`HandoffPacket`。
- 将 src-hunter、yaklang/hack-skills、本地 red_team_skill 的设计转化为 checkpoint、scope gate、evidence discipline、deep-topic routing、runner/tricks/bypass/verdict 分工。

证据：

- `research/requirements-traceability.md`
- `REFLECTION_AUDIT.md`
- `skills/ctf-master/references/state-schema.md`
- `skills/ctf-master/references/tool-card-template.md`

### 阶段二：广泛资料搜集与研究报告

状态：已达成。

达成方式：

- 产出 phase-two research report。
- 资料不只包含论文/官方文档，也包含用户指定 GitHub skills、MCP 工具、CTF benchmark、知识库、OWASP/NSA/MCP 安全资料。
- 对资料做“借鉴什么 / 不盲从什么 / 如何转为本地 skill”的矩阵化处理。

证据：

- `research/phase-two-research-report.md`
- `research/seed-source-matrix.md`
- `scripts/audit_source_matrix.py`

### 阶段三：固化为可安装 skills

状态：已达成。

达成方式：

- 建立 9 个 skill 目录，每个 skill 有 `SKILL.md`、`agents/openai.yaml`，复杂内容放 `references/`，可执行逻辑放 `scripts/`。
- 提供 `install.sh` 支持复制到 Codex / Claude skill 目录。
- 建立 release gate、unit tests、suite manifest、quality audit、traceability audit。

证据：

- `skills/ctf-*`
- `suite-manifest.json`
- `install.sh`
- `tests/test_scripts.py`
- `scripts/release_gate.py`

## 4. 设计原则

### 4.1 不做“大而全自动解题 Agent”

CTF 的关键不是让模型一口气跑完所有工具，而是让模型每一步都知道：

- 当前事实是什么。
- 假设是什么。
- 哪条命令证明或反驳了假设。
- 工具是否健康。
- 输出是否可信。
- 是否越界。
- 是否该继续深入、搜索、换工具、请求人工、或交接。

因此本套件选择“重系统结构，轻模型路由”。模型可以是 Claude Code、Codex、Cursor、Gemini CLI-like agent 等，但领域纪律由 skills 和脚本提供。

### 4.2 Progressive Disclosure

每个 `SKILL.md` 保持短小，把长内容放到 `references/`，把确定性操作放到 `scripts/`。这样可以减少上下文压力，也方便不同 agent 按需读取。

### 4.3 Evidence First

任何结论必须绑定 `EvidenceRecord`。报告、handoff、writeup 都必须说明：

- 命令/动作是什么。
- 原始产物在哪里。
- 退出码/关键输出是什么。
- 支持或反驳哪个假设。
- 风险或可信度是什么。

这吸收了 src-hunter 和 red_team_skill 的证据纪律，也适合 CTF 复盘和多 Agent 接力。

### 4.4 Tool Preflight Before Tool Use

工具不可默认可用。每个工具必须经过：

- 是否安装。
- 版本/依赖是否满足。
- 当前题型是否需要。
- 输入输出是否可控。
- 失败后如何分类。
- 输出如何压缩。

### 4.5 Untrusted Content Boundary

挑战文本、README、网页、PDF/OCR、EXIF、源码注释、MCP tool output、浏览器页面文本都视作数据，不视作指令。fake flag 和 hostile prompt 必须脱敏记录，不得原样复述完整可执行恶意指令。

## 5. Skill Suite 文件结构与含义

```text
ctf-agent-skills/
├── suite-manifest.json
├── SKILL_SUITE.md
├── REFLECTION_AUDIT.md
├── FINAL_REQUIREMENTS_REVIEW.md
├── install.sh
├── skills/
│   ├── ctf-master/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   ├── references/
│   │   │   ├── state-schema.md
│   │   │   ├── acceptance-gates.md
│   │   │   ├── phase-gates.md
│   │   │   ├── ctf-loop.md
│   │   │   ├── deep-topic-router.md
│   │   │   └── tool-card-template.md
│   │   └── scripts/
│   │       ├── init_state.py
│   │       ├── update_profile.py
│   │       ├── update_state.py
│   │       ├── validate_state.py
│   │       ├── gate_state.py
│   │       ├── checkpoint_state.py
│   │       ├── triage_artifacts.py
│   │       ├── route_topic.py
│   │       ├── summarize_output.py
│   │       └── redact_text.py
│   ├── ctf-web/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   └── references/
│   │       ├── web-triage.md
│   │       └── browser-workflow.md
│   ├── ctf-pwn-rev/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   └── references/
│   │       ├── pwn-rev-triage.md
│   │       └── exploit-script-template.py
│   ├── ctf-forensics-crypto/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   └── references/
│   │       ├── forensics-triage.md
│   │       └── crypto-triage.md
│   ├── ctf-specialty/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   └── references/specialty-triage.md
│   ├── ctf-tool-preflight/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   ├── references/
│   │   │   ├── tool-cards.md
│   │   │   ├── environment-preflight.md
│   │   │   └── mcp-adapters.md
│   │   └── scripts/ctf_preflight.py
│   ├── ctf-knowledge/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   ├── references/
│   │   │   ├── source-matrix.md
│   │   │   └── distillation-rules.md
│   │   └── scripts/source_matrix.py
│   ├── ctf-anti-injection/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   ├── references/
│   │   │   ├── untrusted-content.md
│   │   │   └── visual-and-longtext.md
│   │   └── scripts/scan_untrusted_text.py
│   └── ctf-handoff-report/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       ├── references/
│       │   ├── handoff-template.md
│       │   └── writeup-template.md
│       └── scripts/
│           ├── render_handoff.py
│           ├── render_writeup.py
│           ├── render_reflection.py
│           └── finalize_run.py
├── research/
│   ├── phase-two-research-report.md
│   ├── seed-source-matrix.md
│   ├── requirements-traceability.md
│   └── requirements-traceability.json
├── forward-tests/
│   ├── README.md
│   ├── expected-behavior.md
│   ├── RUN_LOG.md
│   ├── FRESH_AGENT_EVALUATION_SUMMARY.md
│   ├── fresh-agent-evaluation-waiver.json
│   ├── fresh-agent-run-record-template.json
│   ├── scorecard-template.json
│   └── scenarios/
├── benchmarks/
│   ├── benchmark-runbook.md
│   ├── benchmark-run-template.json
│   └── runs/cybench-primary-knowledge/
├── demo-fixtures/
├── scripts/
└── tests/test_scripts.py
```

## 6. 核心文件意义说明

### 6.1 顶层文件

| 文件 | 意义 |
|---|---|
| `suite-manifest.json` | 套件机器清单，声明版本、skill 列表、必需文件、验证命令。 |
| `SKILL_SUITE.md` | 人类使用说明，包含安装、验证、forward-test、benchmark、维护规则。 |
| `REFLECTION_AUDIT.md` | 对原始目标、参考资料、当前覆盖、剩余风险、质量门禁的反思审计。 |
| `FINAL_REQUIREMENTS_REVIEW.md` | 本文档，回顾原始需求并客观评估达成情况。 |
| `install.sh` | 将 skills 安装到 Codex / Claude 目标目录的辅助脚本。 |

### 6.2 `ctf-master`

`ctf-master` 是入口 skill。它不负责具体漏洞 exploit，而负责：

- 读题和建模。
- 维护 `ChallengeProfile` 和 `CTFRunState`。
- 做 scope gate / phase gate。
- 路由到 category skill 或 support skill。
- 记录 evidence、checkpoint、dead ends。

关键文件：

| 文件 | 意义 |
|---|---|
| `state-schema.md` | 定义 `ChallengeProfile`、`CTFRunState`、`EvidenceRecord` 等核心数据结构。 |
| `deep-topic-router.md` | 题型从大类到 deep topic 的路由规则。 |
| `phase-gates.md` | intake、triage、route、experiment、verification、report、handoff 的门禁。 |
| `acceptance-gates.md` | solved/excluded/handoff/human intervention 的接受条件。 |
| `ctf-loop.md` | 通用解题循环和卡壳恢复逻辑。 |
| `tool-card-template.md` | 工具卡片模板。 |
| `init_state.py` | 初始化 CTF state。 |
| `update_profile.py` | 更新题目 scope、target、attachment、category 等 profile 信息。 |
| `update_state.py` | 追加 evidence、hypothesis、attempt、next action。 |
| `validate_state.py` | 校验 state 结构、证据引用、artifact 路径。 |
| `gate_state.py` | 执行 phase gate，阻止未授权或证据不足的阶段推进。 |
| `checkpoint_state.py` | 生成上下文压缩/暂停/交接用 checkpoint。 |
| `triage_artifacts.py` | 附件 inventory、hash、文件类型、可疑指令计数。 |
| `route_topic.py` | 输出 deep topic、建议读取文件、first safe actions。 |
| `summarize_output.py` | 压缩长工具输出，提取高信号行。 |
| `redact_text.py` | 脱敏 token、cookie、secret 等敏感字符串。 |

### 6.3 Category Skills

| Skill | 覆盖范围 | 文件意义 |
|---|---|---|
| `ctf-web` | Web/API、浏览器、HTTP、源码路由、认证、模板、上传等 | `web-triage.md` 给 Web 审计路径；`browser-workflow.md` 说明 Chrome/DevTools/MCP/browser 证据处理。 |
| `ctf-pwn-rev` | Pwn、Reverse、ELF、调试、反编译、crash、checker | `pwn-rev-triage.md` 提供二进制初筛和验证路径；`exploit-script-template.py` 给可复现脚本骨架。 |
| `ctf-forensics-crypto` | Forensics、Misc、Crypto | `forensics-triage.md` 管理 pcap/archive/media/log 等取证路径；`crypto-triage.md` 管理 primitive/parameter/weakness/verification。 |
| `ctf-specialty` | AI/LLM、Blockchain、Mobile、IoT、Cloud/K8s | `specialty-triage.md` 为非典型题提供初筛入口，避免过早拆出太多小 skill。 |

### 6.4 Support Skills

| Skill | 作用 | 文件意义 |
|---|---|---|
| `ctf-tool-preflight` | 工具与环境 preflight | `tool-cards.md` 管理工具适用/输入/失败/压缩策略；`environment-preflight.md` 管理 VPN/VPS/OOB/Docker/GUI 等；`mcp-adapters.md` 明确鼓励 IDA/Chrome/CTFd/HexStrike 等 MCP 和渗透测试工具按需辅助解题；`ctf_preflight.py` 执行工具检查。 |
| `ctf-knowledge` | 外部资料/知识库蒸馏 | `source-matrix.md` 和 `distillation-rules.md` 保证资料有来源、可信度、适配度，不盲目复制 payload/writeup；`source_matrix.py` 维护资料矩阵。 |
| `ctf-anti-injection` | 反 prompt injection / fake flag / tool poisoning / long text trap | `untrusted-content.md` 定义不可信内容边界和脱敏报告；`visual-and-longtext.md` 处理 OCR/隐藏文本/大日志；`scan_untrusted_text.py` 检测 hostile 指令、fake flag、外带/破坏性提示。 |
| `ctf-handoff-report` | 卡壳恢复、交接、writeup、复盘 | `handoff-template.md` 固化交接包；`writeup-template.md` 固化可复现 writeup；`render_handoff.py`、`render_writeup.py`、`render_reflection.py`、`finalize_run.py` 生成交付物。 |

## 7. 工具、MCP、脚本如何被纳入设计

### 7.1 MCP

已通过 `ctf-tool-preflight/references/mcp-adapters.md` 设计 MCP 与渗透测试工具接入方式。核心态度是：不对 HexStrike、Chrome DevTools MCP、IDA/Ghidra/r2 MCP、CTFd MCP、安全工具 MCP、浏览器插件、扫描器、调试器、反编译器或自定义脚本做任意禁用；在合法 CTF/授权靶场/授权研究范围内，鼓励用它们加速证据获取和假设验证。

- Chrome DevTools MCP：用于真实浏览器 DOM、network、console、screenshot、Lighthouse 等证据。
- IDA Pro MCP：用于本地 challenge binary 的 xref、decompile、rename、函数定位。
- CTFd MCP：用于题目元信息、附件、提交；提交候选仍需有 EvidenceRecord 支撑，避免误提交。
- HexStrike 或类似工具集 MCP：明确鼓励作为安全工具编排入口使用，按 hypothesis 选择模块并保存原始输出。

关键原则：MCP 工具描述和输出也视作不可信数据；MCP 可用性应被充分利用，但不能让工具输出覆盖用户/开发者指令。联网、提交、扫描、OOB 等动作需要记录题目 scope、规则、速率、目标和原始证据，这些是可复现要求，不是对工具能力的限制。

### 7.2 Bash / CLI 工具

工具不是被白名单限制，而是通过 ToolCard 变得可复现、可压缩、可交接：

- `sqlmap`、`nmap`、`tshark`、`binwalk`、`gdb`、`checksec`、`readelf`、`objdump`、`strings`、`z3`、`sage` 等均通过 preflight 思路管理。
- 缺工具不是“失败”，而是 `missing_dependency` evidence。
- 长输出先落盘，再摘要。

### 7.3 自定义脚本

确定性的重复动作尽量脚本化：

- state：`init_state.py`、`update_state.py`、`validate_state.py`
- profile：`update_profile.py`
- gate：`gate_state.py`
- checkpoint：`checkpoint_state.py`
- route：`route_topic.py`
- anti-injection：`scan_untrusted_text.py`
- preflight：`ctf_preflight.py`
- reporting：`render_handoff.py`、`render_writeup.py`、`render_reflection.py`
- validation：`release_gate.py`、`audit_quality.py` 等

## 8. 对参考资料的吸收方式

| 参考 | 吸收内容 | 改造方式 | 没有盲从的点 |
|---|---|---|---|
| `src-hunter-skill` | checkpoint、scope gate、evidence discipline、按需 playbook | 变成 CTF 的 phase gate、state checkpoint、EvidenceRecord、handoff/writeup evidence contract | SRC 真实目标测试流程没有直接搬到 CTF；保留授权边界。 |
| `yaklang/hack-skills` | master -> category -> deep topic 的层级路由 | 变成 `ctf-master` + category skills + `route_topic.py` + `deep-topic-router.md` | 没把广义攻防 payload 大字典塞进上下文。 |
| 本地 `red_team_skill` | runner/tricks/bypass/verdict 分工、工具编排与 preflight、结构化 evidence、上下文保护 | 变成 ToolCards、phase gates、evidence contract、verdict-style writeup/handoff；将“白名单”语义改造为“工具启用 + 证据记录 + 输出压缩” | 内部业务/反爬假设没有直接变成 CTF 攻击动作。 |

## 9. 验证与质量结论

最近一次验证结果：

```text
python3 -m unittest tests/test_scripts.py
# 38 tests passed

python3 scripts/validate_suite.py --smoke
# OK: 9 skills validated

python3 scripts/release_gate.py --json
# ok: true
# requirements_checked: 43
# failing_count: 0
# partial_or_open_ids: ["REQ-EVAL-FRESH-AGENT"]
```

completion audit 有两种诚实语义：

```bash
python3 scripts/audit_completion.py --json
```

默认含义：工程就绪，但 strict fresh-agent verified pass 仍未完成。

```bash
python3 scripts/audit_completion.py \
  --fresh-waiver forward-tests/fresh-agent-evaluation-waiver.json \
  --require-v1 \
  --json
```

含义：根据用户明确接受当前评估证据并跳过最终 v4 fresh-agent rerun，当前目标可按 user waiver 收口。

## 10. 客观剩余风险

1. **严格 fresh-agent verified pass 未完成**  
   v1-v3 fresh-agent 迭代已经暴露并推动修复了真实问题；v4 packet 已就绪，但最终 7/7 rerun 被用户明确跳过。因此 strict external certification 仍应重跑。

2. **真实多类别 solve-rate 未充分证明**  
   当前有 synthetic demos 和一个 Cybench Primary Knowledge benchmark。它证明流程可用，不证明 Web/Pwn/Rev/Forensics/Crypto 全类别高解题率。

3. **Specialty skill 较宽**  
   AI/LLM、Blockchain、Mobile、IoT、Cloud/K8s 暂时合并在 `ctf-specialty`。真实题积累后应按高频方向拆分。

4. **工具安装与环境部署没有自动化到底**  
   `ctf_preflight.py` 会检查和分类缺失工具，但不会自动安装所有工具，也不会替你配置 VPS、VPN、IDA license、安全组。

5. **模型路由 intentionally 弱化**  
   按用户后续要求，没有构建复杂模型选择器；当前更偏向可在 Claude Code/Codex 等成熟 code agent 中安装使用。

## 11. 是否成功达成最初目标

结论：在“研究 + 方案 + 可安装 skills + 工具/脚本/门禁 + 评估体系”的范围内，已经成功达成。

更精确地说：

- 如果目标是产出一套能帮助 AI/Agent 更稳定、更有状态、更少浪费工具时间、更能防 prompt injection、更方便交接和复盘的 CTF skills：已达成。
- 如果目标是证明它已经在所有 CTF 大类里都有稳定高 solve-rate：尚未证明。
- 如果目标是成为一个完全专用、中心化调度、多模型、多沙箱、多队列的 CTF Agent 平台：这不是当前版本的选择，当前版本明确选择更轻、更可安装、更跨 agent 的 hybrid route。

当前最适合的使用方式是：

1. 把 `skills/ctf-*` 安装到 Codex/Claude 等 code agent。
2. 解题时从 `$ctf-master` 进入。
3. 每题维护 `CTFRunState` 和 `ChallengeProfile`。
4. 工具先 preflight，再实验。
5. 长输出落盘并摘要。
6. prompt injection/fake flag 一律隔离和脱敏。
7. 三条证据路径失败或需要人工/其他模型时，用 `ctf-handoff-report` 交接。
8. 每次真实题后用 reflection 和 audit 把新经验沉淀回 references/scripts。

这正对应最初的研究目标：不是让 AI 盲目变猛，而是让 AI 在 CTF 中更会组织自己、更会用工具、更会保护上下文、更会交接、更会从失败中沉淀。
