# 阶段二研究报告：面向 CTF 的 Agent Skills 工程体系

## Executive Summary

本报告的结论是：短中期最可落地的 CTF Agent 路线不是从零构建一个庞大的专用多智能体平台，而是采用“成熟 code agent + 可安装 skills + MCP/工具适配 + 状态机 + 证据日志 + 知识蒸馏 + 安全边界”的混合工程体系。

原因有三点。第一，Claude Code、Codex、Cursor、Gemini CLI 等成熟 code agent 已经具备代码阅读、shell 编排、文件编辑、浏览器/工具调用能力；真正缺的是领域流程、状态纪律、工具卡片、证据门禁和反注入边界。第二，Agent Skills 这种结构可以把长知识拆成 `SKILL.md`、`references/`、`scripts/`，既能跨工具复用，又能避免把大段 writeup/payload 塞进上下文。第三，CTF 解题的成败高度依赖环境、证据和卡壳恢复；如果没有 `CTFRunState`、`EvidenceRecord`、preflight、handoff 和 writeup，单次推理能力再强也容易失忆式乱试。

本仓库中的 `ctf-agent-skills/` 已将该路线固化为 9 个可安装 skills：`ctf-master`、`ctf-web`、`ctf-pwn-rev`、`ctf-forensics-crypto`、`ctf-specialty`、`ctf-tool-preflight`、`ctf-knowledge`、`ctf-anti-injection`、`ctf-handoff-report`。这些 skills 当前覆盖合法边界、题目 intake、深层 topic 路由、工具 preflight、知识蒸馏、状态机、反提示注入、卡壳恢复、handoff/report、synthetic demo，以及一个已验证的 Cybench 本地 benchmark run。仍未证明的 v1 门槛是 fresh-agent forward-test；多类别 solve-rate 仍需要更多真实题验证。

## 资料矩阵

| 来源 | 类型 | 主题 | 相关度 | 可借鉴设计 | 不应盲从 | Skill 转化 | 证据链接 | 可信度/时效性 |
|---|---|---|---|---|---|---|---|---|
| OpenAI Codex Agent Skills | 官方文档 | Codex skills 打包模型 | 高 | skills 包含 instructions/resources/scripts；适合可安装能力包 | 不直接解决 CTF 状态机和工具安全 | `SKILL.md` 瘦身、`references/` 和 `scripts/` 分层 | [OpenAI Codex Skills](https://developers.openai.com/codex/skills) | 官方，当前 |
| Agent Skills Specification | 标准/规范 | `SKILL.md` 结构 | 高 | `SKILL.md` + optional scripts/references/assets | 标准只定义包装，不定义领域流程 | 所有 skill 目录遵守 name/description/frontmatter | [Agent Skills spec](https://agentskills.io/specification) | 标准性高 |
| Claude Agent Skills | 官方文档 | 跨 agent skills 概念 | 中高 | skills 是模块化能力包，触发后加载 | 平台差异需要安装适配 | `install.sh --codex/--claude` | [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | 官方，当前 |
| src-hunter-skill | GitHub skill | SRC/漏洞挖掘流程 | 高 | checkpoint、scope gate、evidence discipline、按需 playbook | SRC 不等同 CTF；不能照搬真实目标测试流程 | `ctf-master` scope/evidence gates、`ctf-knowledge` 蒸馏 | [src-hunter-skill](https://github.com/MyuriKanao/src-hunter-skill) | 高，用户指定 |
| yaklang/hack-skills | GitHub skills | 安全知识分层路由 | 高 | master -> category -> deep topic；知识索引化 | 广义攻防知识会造成 CTF 过度动作 | `deep-topic-router.md`、`route_topic.py`、category skills | [yaklang/hack-skills](https://github.com/yaklang/hack-skills) | 高，用户指定 |
| 本地 red_team_skill | 本地 skill 集 | runner/tricks/bypass/verdict | 高 | 强门禁、工具白名单、结构化 evidence、上下文保护 | 内部业务/反爬假设不适合公共 CTF 直接复用 | ToolCards、`CTFRunState`、handoff/report 分工 | `/Users/bytedance/red_team_skill` | 高，本地实物 |
| Model Context Protocol | 协议/官方 | 工具/资源/上下文接入 | 高 | 标准化连接工具和数据源 | MCP 可用不等于可信；工具描述可投毒 | `mcp-adapters.md`、工具白名单、安全门禁 | [MCP GitHub](https://github.com/modelcontextprotocol), [MCP auth](https://modelcontextprotocol.io/docs/tutorials/security/authorization) | 官方/生态核心 |
| NSA MCP Security Design Considerations | 政府安全指南 | MCP 安全设计 | 高 | secure-by-default、实现严谨、验证工具、部署安全 | 面向组织部署，CTF 场景需轻量化 | MCP preflight、最小权限、日志留痕 | [NSA MCP security PDF](https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf?ver=bmgiSbNQLP6Z_GiWtRt6bg%3D%3D) | 高，2026 |
| OWASP LLM01 Prompt Injection | 安全指南 | 直接/间接 prompt injection | 高 | 外部网页/文件可注入指令；必须隔离数据与指令 | OWASP 是应用安全视角，需转成 CTF artifact 流程 | `ctf-anti-injection`、scan 脚本、fake flag 门禁 | [OWASP LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | 高，持续更新 |
| OWASP Prompt Injection Cheat Sheet | 安全指南 | 防护策略 | 高 | 明确说明自然语言指令和数据混合是核心风险 | 不能幻想完全消除风险 | untrusted-content policy、tool output boundary | [OWASP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) | 高，当前 |
| Microsoft indirect prompt injection guidance | 厂商安全实践 | MCP/agent 间接注入 | 中高 | 把外部内容当不可信；降低工具风险 | 厂商实现细节不全部可复用 | 反注入、MCP tool poisoning 检查 | [Microsoft MCP injection blog](https://developer.microsoft.com/blog/protecting-against-indirect-injection-attacks-mcp) | 高，近年 |
| Chrome DevTools MCP | 官方/GitHub 工具 | 浏览器自动化、DOM/网络/审计 | 高 | 真实浏览器交互、DevTools 证据、Lighthouse | 浏览器状态可能泄露隐私；页面文本不可信 | `browser-workflow.md`、MCP adapter ToolCard | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp), [Chrome DevTools agents](https://developer.chrome.com/docs/devtools/agents) | 高，活跃 |
| IDA Pro MCP | GitHub 工具 | 逆向工程 MCP | 中高 | 让 agent 读 IDA 数据库、xref、反编译上下文 | 反编译输出是 hypothesis，不是事实 | `ctf-pwn-rev`、MCP adapter reference | [ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp) | 中高，工具活跃 |
| HexStrike AI MCP | GitHub 工具 | 大量安全工具 MCP 编排 | 中 | 展示 MCP 连接安全工具的上限 | 自动化攻击面太大；需要强 scope/rate gate | 工具白名单、不要一口气暴露 150+ 工具 | [hexstrike-ai](https://github.com/0x4m4/hexstrike-ai) | 中，需安全改造 |
| CTFd MCP Server | GitHub/工具 | CTF 平台接入 | 中 | challenge intake、附件下载、提交 | 自动提交有误用和频率风险 | 未来 `ctf-master`/CTFd adapter | [CTFd MCP server](https://mcpservers.org/servers/tomek7667/ctfd-mcp-server) | 中 |
| Cybench | Benchmark/论文/代码 | 40 个专业 CTF 任务和 subtasks | 高 | 完整任务 + subtasks，适合评测 agent 能力 | 评测不等于运行流程；仍需技能工程 | v1 benchmark 目标、forward-test 设计 | [Cybench](https://cybench.github.io/), [arXiv](https://arxiv.org/html/2408.08926v2), [GitHub](https://github.com/andyzorigin/cybench) | 高 |
| NYU CTF Bench | Benchmark/论文/代码 | 200 个 dockerized CSAW 题 | 高 | 多类别、可部署、适合真实端到端验证 | 需要环境成本，不能短路为 synthetic demo | v1 real/benchmark CTF gate | [NYU CTF Bench](https://nyu-llm-ctf.github.io/), [GitHub](https://github.com/NYU-LLM-CTF/NYU_CTF_Bench), [paper](https://arxiv.org/abs/2406.05590) | 高 |
| CAISI Cyber Evaluations | 政府/GitHub eval | cyber benchmarks/agents | 中 | 标准化运行 agentic cyber benchmark | 范围大于 CTF，需要筛选 | 未来 eval harness 参考 | [CAISI cyber evals](https://github.com/usnistgov/caisi-cyber-evals) | 高，政府/开源 |
| CTF Wiki | 知识库 | 多方向 CTF 基础/进阶知识 | 高 | 按方向组织知识，适合 topic reference | 内容大，不应整本塞上下文 | `ctf-knowledge` 资料矩阵、topic router | [CTF Wiki](https://ctf-wiki.org/en/), [GitHub](https://github.com/ctf-wiki/ctf-wiki) | 高，社区长期 |
| HackTricks | 知识库 | CTF/真实应用技巧 | 高 | 技术点、检查清单、方法论 | 真实环境 pentest 内容会越界；需 scope gate | category references、source distillation | [HackTricks](https://github.com/HackTricks-wiki/hacktricks) | 高，更新快 |
| PayloadsAllTheThings | GitHub 知识库 | Web payload/bypass 集 | 中高 | payload 索引和漏洞分类 | 不应把 payload 字典注入上下文；CTF 需最小测试 | `ctf-knowledge`：仅转 signal -> test -> proof | [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings) | 高，社区 |
| Hello CTF | 中文知识库 | 新手友好 CTF 学习与工具生态 | 中 | 中文分类、工具/题目配套、Docker/source 思维 | 教程型内容不等同 agent 流程 | 环境 preflight、知识库标签 | [Hello CTF](https://hello-ctf.com/hc-preface/about/), [GitHub topic](https://github.com/topics/ctf) | 中高 |

## 当前 CTF Agent / Skills / MCP / Tooling 生态分析

### 1. Skills 生态

Agent Skills 已形成“轻量目录 + `SKILL.md` + 可选资源”的通用模式。OpenAI、Anthropic/Claude 和 Agent Skills 标准都把 skills 定位为可触发、可携带脚本和参考材料的能力包。这对 CTF 特别合适，因为 CTF 的关键知识不是单个 prompt，而是一组可复用工作流：

- 初始 intake：题目、附件、远程、规则、flag 格式。
- 工具 preflight：健康检查、版本检查、依赖检查、dry-run。
- 题型路由：master -> category -> deep topic。
- 状态机：事实、假设、实验、证据、失败路径、下一步。
- 报告：handoff、writeup、复盘、skill 迭代。

本套件采用多 skill 而非单一大 skill：`ctf-master` 只做入口、状态、路由、门禁；category skills 做领域 triage；support skills 做工具、知识、反注入和交接。这样符合 progressive disclosure，也避免“万能大 prompt”拖垮上下文。

### 2. MCP 与工具生态

MCP 解决的是工具接入的 N x M 问题：一个标准协议让 agent 接浏览器、IDA、CTFd、文件系统、数据库、代理/抓包、安全工具。但 CTF 场景不能把 MCP 当成“工具越多越好”。Chrome DevTools MCP 可以提供真实浏览器 DOM/网络/控制台证据，但它也能暴露浏览器状态；IDA MCP 能增强逆向上下文，但反编译结果仍然需要动态验证；HexStrike 这类大工具 MCP 证明了编排潜力，也暴露了自动化攻击面过大的风险。

因此本报告建议 MCP 采用“adapter + ToolCard + scope gate”模式：

1. MCP 只暴露当前题型需要的最小工具集。
2. 每个 MCP tool 必须有输入、输出、失败分类、危险操作、压缩策略。
3. MCP tool description 和 tool output 都视作不可信内容。
4. GUI/browser/IDA 输出必须保存原始 artifact，再写摘要。
5. 任何联网、扫描、提交、外带、写文件动作必须过授权/规则边界。

### 3. Benchmark 与评测生态

Cybench 和 NYU CTF Bench 都说明 CTF agent 评测不能只看“最终是否出 flag”。Cybench 引入 subtasks，让中间步骤可评估；NYU CTF Bench 提供 dockerized、多类别、可部署的真实 CTF 题。对本套件来说，synthetic demo 只能证明工作流和脚本健康，不能证明真实 solve-rate。v1 必须至少跑一个真实或 benchmark CTF，并保存 `CTFRunState`、raw artifacts、handoff/writeup 和复盘后的 skill 修改建议。

## CTF Agent 能力分层模型

本报告将 CTF Agent 能力拆成 8 层：

1. **边界层**：合法 CTF、授权靶场、授权研究、本地隔离；规则、速率、提交频率、AI 使用限制。
2. **环境层**：VPN、代理、DNS、Docker、VM、浏览器、IDA/Ghidra、pwndbg、Sage/z3、VPS/OOB、磁盘、时间同步。
3. **工具层**：MCP、CLI、浏览器、调试器、反编译器、solver、抓包/流量工具；每个工具都有 ToolCard。
4. **题目理解层**：CTFd 元信息、附件清单、文件类型、源码框架、远程目标、flag 格式、hint、规则。
5. **路由层**：master -> category -> deep topic；不把平台标签当事实，用证据评分。
6. **解题循环层**：hypothesis -> experiment -> evidence -> update state -> next action。
7. **知识层**：外部资料可信度、时效性、可复现性、与 CTF 匹配度；转成 checklist/script，不复制全文。
8. **协作与复盘层**：handoff、writeup、forward-test、benchmark、skill 迭代。

当前套件对应关系：

- 层 1/4/5/6：`ctf-master`
- 层 2/3：`ctf-tool-preflight`
- 层 4/5：category skills 与 `route_topic.py`
- 层 7：`ctf-knowledge`
- 层 8：`ctf-handoff-report`
- 横切安全：`ctf-anti-injection`

## 工具工程方案

### ToolCard 标准

每个工具卡必须包含：

- Applies when：什么信号证明需要该工具。
- Allowed tools：允许的 binary/MCP/script/browser capability。
- Preflight：版本、依赖、权限、网络、GUI、license 检查。
- Minimal command：最小可产出证据命令。
- Failure：tool_not_found、bad_argument、dependency_missing、target_unavailable、scope_or_rate_limit、output_overload、hypothesis_failed。
- Retry：只有失败类别改变才重试。
- Output handling：先保存 raw output，再摘要。
- Compression：路径、关键行、数量、异常、候选 flag、下一步。

### 工具顺序

默认顺序是轻量到重型：

1. 读题和附件 inventory。
2. 反注入扫描。
3. 文件类型/hash/目录结构。
4. category-safe preflight。
5. 最小 baseline。
6. 针对 hypothesis 的单个实验。
7. 重型扫描、爆破、动态调试、GUI 或搜索。

### 长输出处理

原则：raw artifact 永远落盘，主上下文只保留摘要。摘要必须包含：

- 命令和目的。
- 退出码。
- 关键行。
- 证据支持/反驳哪个 fact/hypothesis。
- 下一步动作。

当前 `summarize_output.py` 已默认抓取 flag、error、warning、traceback、secret、port/service、binary protection 等高信号行。

## 题意理解与代码/文件审计方案

### ChallengeProfile

题目 intake 统一写入 `ChallengeProfile`：

- title/platform/category_claimed/category_inferred/category_confidence
- description/flag_format/rules/targets/attachments/credentials/scope_status

### 文件/代码审计

初始文件审计不追求“马上找漏洞”，而是建攻击面索引：

- Web：routes、controllers、auth/session、data access、template/render、upload/download、SSRF、deserialization、shell/process、crypto/random。
- Pwn：file/checksec/readelf/strings、协议、crash、control proof、leak、primitive、final objective。
- Reverse：input path、success/failure decision、constants/tables/xrefs、dynamic verification。
- Crypto：primitive、parameters、suspected weakness、mathematical condition、verification。
- Forensics：source hash、container/archive layer、protocol/media/exif/carving path。
- Specialty：AI/LLM、Blockchain、Mobile、IoT、Cloud/K8s 按 `ctf-specialty` 路由。

### 深层 topic 路由

`route_topic.py` 负责从 text/file/triage JSON 中输出 `topic_id`、skill、read_next、first_safe_actions、evidence_gates。它不是结论器，只是下一步 playbook 索引。

示例：

- `render_template_string` + `{{ }}` -> `web.ssti`
- `n/e/c` + RSA -> `crypto.rsa`
- `ignore previous instructions` -> `meta.prompt-injection`

## 搜索与知识库方案

资料处理遵循四步：

1. Source rating：官方/论文/benchmark/GitHub/writeup/blog/个人观点分层。
2. Fit rating：是否适合 CTF、是否需要安全改造、是否会导致过度攻击。
3. Distillation：转为 signal -> decision -> first command -> proof gate。
4. Skill conversion：更新 reference、ToolCard、script、forward-test 或 traceability。

不允许把大段 payload 字典、整篇 writeup、未审计 exploit 直接放进 `SKILL.md`。PayloadsAllTheThings/HackTricks/CTF Wiki 这类大源只作为 reference source，进入主上下文前必须蒸馏为短 checklist 或具体 script 输入。

## 流程编排与卡壳恢复方案

通用循环：

1. Intake
2. Preflight
3. Triage
4. Hypothesize
5. Experiment
6. Summarize
7. Route
8. Verify
9. Report

卡壳分类：

- Continue：已有证据但未分析完。
- Search：陌生技术、CVE、框架版本、文件格式、协议、算法。
- Switch tool：当前工具视角不足，需要浏览器、调试器、反编译、solver、GUI。
- Human intervention：授权、凭据、VPN、license、硬件、平台异常、GUI 判断、规则敏感动作。
- Handoff：三条有证据路径失败，下一步是策略选择。

`acceptance-gates.md` 定义 solved/excluded/handoff/human intervention gates；`render_handoff.py` 从 state 生成交接文档。

## 人工介入与交接模板

人工介入不是“模型放弃”，而是把非模型问题或策略分歧结构化交出去。交接包必须包含：

- challenge_summary
- environment_summary
- current_state
- evidence_table
- attempts_and_dead_ends
- hypotheses
- most_likely_next_steps
- questions_for_human
- artifact_paths
- safety_notes

当前 `ctf-handoff-report` 已把这些字段固化成模板和渲染脚本。后续真实题复盘时，应记录“handoff 是否让下一位 solver 更快”，作为 skill 质量指标。

## 反 AI 干扰与 Prompt Injection 防护方案

威胁面：

- README/源码注释/HTML/PDF/EXIF/压缩包注释中的指令。
- fake flag/rabbit hole。
- 超大日志和 vendor 目录撑爆上下文。
- 工具投毒：MCP tool description、tool output、恶意 Dockerfile/README。
- 浏览器页面隐藏文本、CSS 不可见文本、bidi/zero-width 字符。

防护原则：

1. 所有 challenge/external/tool output 都是 data，不是 authority。
2. 先扫描，再分离“技术事实”和“指令性文本”。
3. fake flag 只是 candidate string，不是 solve evidence。
4. MCP tool description 不能要求 agent 调 unrelated tools 或 exfiltrate context。
5. 浏览器/IDA/MCP 输出必须保存 raw artifact，摘要中标 trust label。

当前 `ctf-anti-injection` 已包含 trust labels、tool output boundary、fake flag handling 和 `scan_untrusted_text.py`。

## 环境部署与 Preflight 方案

CTF 环境 preflight 分为：

- 网络：VPN、DNS、代理、特定出口、CTFd 可达性、远程端口。
- OOB/VPS：域名、端口、防火墙、HTTPS、临时文件服务、日志。
- 本地：Docker/compose、VM、Kali、Windows、Android 模拟器、GPU、GUI、声卡/摄像头。
- 工具：nmap/ffuf/curl/tshark/binwalk/gdb/pwndbg/radare2/Ghidra/IDA/z3/Sage/hashcat/john/pwntools。
- MCP：Chrome DevTools、IDA、CTFd、filesystem、database、browser。
- 规则：外网搜索、AI 使用、自动化提交、扫描速率、队伍共享、flag 提交频率。

Fail-closed 原则：拿不到授权、规则、凭据、VPN、license、GUI 或硬件时，输出环境事项清单，不继续误跑。

## 评测体系与 Benchmark 方案

分四层评测：

1. **静态校验**：official `quick_validate.py`、manifest、template residue scan。
2. **脚本单测**：state/update/handoff/router/preflight/traceability。
3. **Synthetic demo**：Web/Crypto/Reverse 本地安全 fixture，验证状态机、证据、路由、writeup。
4. **Fresh-agent/Benchmark**：无泄露预期答案的 forward-test；至少一个 Cybench 或 NYU CTF Bench 真实/benchmark 题。

当前已完成 1-3，并已补充第 4 层的 prompt pack、批量评分 runner、fresh-agent run-record verifier、benchmark run 初始化器和 `verify_benchmark_run.py`。Cybench Primary Knowledge 已作为本地 benchmark run 跑通并通过 oracle 校验；第 4 层剩余 gate 是独立 fresh-agent 运行记录和更多类别覆盖。

建议评分：

- Correct routing
- State discipline
- Tool discipline
- Untrusted content boundary
- Evidence quality
- Handoff quality
- Solve/reproduce outcome
- Post-run skill update

## 短期、中期、长期落地路线

### 短期

- 安装 9 个 skills。
- 在本地 synthetic demo 和 forward-tests 上跑回归。
- 对真实 CTF 题开启 `ctf-master`，强制记录 state/evidence。
- 对每次工具失败补 ToolCard。

### 中期

- 跑至少 1 个 Cybench/NYU CTF Bench 题。
- 记录完整 `CTFRunState`、writeup、handoff、复盘。
- 把真实误路由、误触发、工具失败转成 router/test/ToolCard。
- 扩展 category references：Web SSRF/upload/JWT、Pwn heap/ROP、Crypto RSA/lattice/PRNG、Forensics PCAP/stego。

### 长期

- 增加轻量 coordinator：题目状态 DB、artifact store、CTFd adapter、eval dashboard。
- 允许多 agent 分工，但以 state/evidence 为同步协议。
- 为高风险 MCP 建立 manifest allowlist、隔离浏览器 profile、只读 reverse session。
- 形成离线知识包版本管理和 source freshness audit。

## 风险、限制、合规与安全边界

### 风险

- MCP/tool poisoning：工具描述或输出诱导 agent。
- 自动化误用：未授权扫描、过高频率、误提交。
- Context overload：长日志、vendor、payload 字典。
- False confidence：synthetic demo 通过但真实题失败。
- Tool hallucination：工具不存在、参数错、环境不满足。

### 限制

- 本报告不提供真实目标攻击操作。
- 不研究未授权横向移动、隐蔽持久化、真实系统滥用提交。
- 不把 payload 字典作为主要能力。
- 不把模型路由作为主线。

### 合规边界

所有 workflows 仅限：

- 合法 CTF
- 授权靶场
- 授权漏洞研究
- 本地隔离实验

任何 remote action 之前必须确认 scope、rules、rate、target 和 evidence logging。

## 当前结论、未解决问题、下一阶段计划

### 当前结论

CTF Agent 的核心工程问题不是“让模型更会猜”，而是让 agent 在证据、状态、工具、知识和安全边界上可控。当前 `ctf-agent-skills` 已经把研究结论转成可安装 skills 和脚本，具备从 intake 到 demo writeup 的闭环。

### 未解决问题

- 还没有 fresh-agent/subagent forward-test 运行记录。
- 真实/benchmark CTF 端到端 solve 证据目前只有 Cybench Primary Knowledge 一题，不能代表多类别 solve-rate。
- category references 仍偏 triage，深 payload/playbook 需要真实题反馈后逐步扩展。
- `ctf-specialty` 覆盖面较广，后续可能拆成 AI/Blockchain/Mobile/Cloud 子 skill。

### 下一阶段计划

1. 执行 fresh-agent forward-test，不泄露预期答案，只提供 skill 路径和场景 prompt。
2. 选择更多安全 benchmark CTF 题，至少覆盖 Web/Pwn/Reverse/Forensics/Crypto 中的多个方向。
3. 从真实 run 中继续提炼 ToolCard、anti-injection 规则或 deep-topic router 修正。
4. 更新 traceability 和 `REFLECTION_AUDIT.md`，决定是否达到 v1.0。
