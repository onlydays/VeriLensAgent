# VeriLens Spec —— 带评测与可观测性的技术调研 Agent（完整规格）

> 版本：v1.0　日期：2026-09-07　状态：开发中（Phase 1 已启动）
> 关联文档：`开题文档.md`（简明版）、`前端交接文档.md`（给 kimi 生成前端的完整契约）
> 代码入口：`src/main.py`（Phase 1 命令行）

---

## 0. 变更记录（决策日志）

| 日期 | 决策 |
|---|---|
| 2026-09-07 | 定位从「Research Agent 生成报告」翻转为「**带评测与可观测性的 Agent**」：评测体系是主角、可复用；Agent 是被评测对象（2026 年通用 Agent demo 已卷烂，可信/可量化才是差异化）。 |
| 2026-09-07 | 技术栈：Python + OpenAI 兼容协议，**DeepSeek / 豆包可切换**（`base_url` 切换，一套代码）。 |
| 2026-09-07 | API key 由用户提供：请求参数覆盖 `.env` 默认值。 |
| 2026-09-07 | 前端：后期由 kimi 生成，通过 FastAPI HTTP 接口对接（见 `前端交接文档.md`），后端不做 UI。 |
| 2026-09-07 | 分发策略：以 **GitHub 开源**为"惠及他人"载体；**不做** exe/多平台安装包（过度工程、对求职无帮助）；不做公网服务器托管（持续付费、超出个人项目范围）。 |
| 2026-09-07 | Go 后端投递线放弃，集中精力于「C++/工业保底 + AI 应用发展」。 |

---

## 1. 产品一句话与定位

> 一个技术调研 Agent，但**主角不是 Agent，而是给它配套的评测 + 可观测性体系**——不做「又一个 Agent」，做「一个能被证明可靠的 Agent」，用自研评测工具把可靠性量化成数字。

- **被评测对象（Agent 层）**：输入一个问题 → 自主规划检索 → 搜索 → 抓取网页 → 交叉验证 → 输出带来源引用的调研报告。
- **主角（评测层）**：独立可复用的评测工具（eval harness），任何实现 `AgentProtocol` 的 Agent 都能被它评测。
- **过程层（可观测性）**：每步 trace 落盘，失败/耗时/token 可定位、可分析。

## 2. 它解决什么问题（大白话）

**给用户**：输入一个需要翻很多资料才能回答的问题（如"调研 Go 与 Rust 在云原生方向的现状对比"），Agent 自动完成「搜索 → 打开网页读正文 → 交叉验证 → 写报告」，输出**每条结论都带可点回原文的来源引用**的调研报告。

| 对比 | 搜索引擎 | 普通 ChatGPT | VeriLens |
|---|---|---|---|
| 给什么 | 一列链接 | 一段可能编造的文字 | **综合好、带来源、可核查**的报告 |
| 谁花时间 | 用户（2-3 小时） | 用户自行核对真伪 | Agent（几分钟）+ 用户抽查引用 |

**给求职的自己**：这是一个能证明「理解 LLM 不可靠性 + 具备工程治理能力」的 2026 年差异型项目。

**谁会用到**：求职者/学生（技术选型、公司调研）、开发者（陌生技术快速上手）、产品/分析师（竞品与市场调研）。

## 3. 范围

### 3.1 MVP 功能清单（P0 = 必做，按 Phase 推进）

| 优先级 | 功能 |
|---|---|
| P0 | Agent 最小闭环：ReAct 循环 + 搜索工具 + 输出带引用小结 |
| P0 | 评测工具：`AgentProtocol` + `EvalHarness` + 4 指标 + 评测集 ≥20 条 |
| P0 | 量化迭代：改进前 vs 改进后两组真实指标 |
| P0 | 可观测性：每步 trace 落盘（推理/工具/输入输出/token/耗时） |
| P1 | 网页抓取工具（多工具） |
| P1 | 上下文管理（token 预算、超长压缩） |
| P1 | HTTP API（`/api/research`）+ Web UI（kimi 前端对接） |
| P2 | SSE 流式（前端实时看步骤）、回归对比自动化、换第二个 Agent 验证评测工具通用性 |
| P2 | 评测集扩充到 50 条；trace 可视化；demo 录屏 + README + GitHub 发布 |

### 3.2 非目标（明确不做，写进简历面试口径）

- ❌ 不做 exe / 多平台安装包分发（阶段外；见 §11 分发策略）。
- ❌ 不做公网部署、多用户、鉴权、计费（本地/个人工具定位）。
- ❌ 不做 LLM token 级流式输出（我们流的是"步骤事件"，不是 token）。
- ❌ 不直接用 LangChain/LangGraph 包循环（手写 ReAct，机制是自己的）。
- ❌ 不做本地文档 RAG、多 Agent 编排（远期可选，不影响主叙事）。
- ❌ 不编造评测数字：所有指标必须来自真实评测集。

## 4. 系统架构

```
                    ┌──────────────────────────────────────┐
   用户（CLI/WebUI）▶│  API 层（Phase 4+）                   │
                    │  FastAPI：/api/research(+stream)     │
                    └──────────────┬───────────────────────┘
                                   ▼
                    ┌──────────────────────────────────────┐
                    │  Agent 层（被评测对象）                 │
                    │  ReAct 循环 / 工具 / 上下文 / 报告      │
                    │  src/agent/…                          │
                    └──────────────┬───────────────────────┘
                                   │ 产出 Report（结论+引用）
                                   ▼
        ┌───────────────────────────────────────────────────┐
        │  评测层（独立可复用，主角）                           │
        │  AgentProtocol → EvalHarness → 4 指标打分           │
        │  src/eval/…                                        │
        └───────────────┬───────────────────────────────────┘
                        │ 量化结果 + 失败定位
                        ▼
        ┌───────────────────────────────────────────────────┐
        │  可观测性层：每步 trace（推理/工具/token/耗时）        │
        │  src/observability/… → logs/*.jsonl                │
        └───────────────────────────────────────────────────┘
```

**一次请求生命周期（时序）**：用户提问 →（API 层校验、注入 LLM 配置）→ Agent 循环多轮（LLM 决策 → 工具执行 → 观察回填）→ Report 组装（结论 + 引用）→ 返回/落盘 → 评测/观测层全程记录。

**评测与观测分工（面试必讲）**：评测 = 结果层（结果好不好）；可观测 = 过程层（过程发生了什么）。

## 5. 技术选型与理由

| 层 | 选型 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | AI 生态、上手快 |
| LLM 协议 | OpenAI 兼容（`openai` SDK） | **一套代码，DeepSeek/豆包仅切 `base_url`** |
| 供应商 A | DeepSeek（`https://api.deepseek.com`，`deepseek-chat`） | 稳定、支持 function calling、便宜 |
| 供应商 B | 豆包（火山方舟 `https://ark.cn-beijing.volces.com/api/v3`，模型填接入点 ID） | 用户备选 |
| 搜索 | DuckDuckGo（`ddgs`） | **免费、无需额外 key**；后续可加 Tavily/博查 |
| 抓取（W2） | `trafilatura` + `requests` | 正文提取 |
| 判定（W3） | 规则 + LLM-as-judge 双通道 + 人工抽样 | 防"LLM 判 LLM"偏差 |
| API 服务（P1） | FastAPI + uvicorn | 轻量、契约清晰、同源托管前端 |
| 可观测 | `logging` + JSONL 落盘 | 零依赖、可 grep |
| 依赖管理 | `pip + venv`（可选 `uv`） | 简单 |

**配置优先级（全局约定）**：请求参数（api_key/base_url/model） > `.env` 环境变量 > 默认值。

## 6. 模块设计

### 6.1 LLM 封装 `src/agent/llm.py`（已实现）
- `LLM(base_url, api_key, model)` 均可选，缺省读 `.env`（`LLM_BASE_URL/LLM_API_KEY/LLM_MODEL`）。
- `chat(messages, tools) -> StepResult`：`StepResult(is_final, text, tool_calls)`；tool 参数 JSON 解析失败兜底为空 dict，交由上层自愈。
- 错误处理约定：网络/鉴权/余额/限流错误统一抛出并**分类**（见 §8.4 错误码表），由上层映射为 HTTP 错误。

### 6.2 工具层 `src/agent/tools/`
```python
class Tool(ABC):
    name: str; description: str; parameters: dict   # JSON Schema
    def run(self, **kwargs) -> str: ...             # 返回观察文本
    def to_openai_schema(self) -> dict: ...
```
- `SearchTool`（已实现）：DuckDuckGo 文本搜索，兼容 `ddgs` / `duckduckgo_search` 两个包名；异常不崩溃，返回错误文本。
- `FetchTool`（W2）：抓 URL → 正文提取，返回截断正文（按 token 预算）。

### 6.3 Agent 循环 `src/agent/loop.py`（已实现骨架）
- 手写 ReAct：`chat → 若 tool_calls 则执行并回填 tool 消息 → 再 chat`；`is_final` 则输出。
- 终止条件：模型给出最终答案；或达 `max_steps`（默认 8）后强制总结。
- 健壮性：未知工具/参数错误/执行异常 → 返回可读错误文本给 LLM 继续（不崩溃）。
- W2 增强：上下文 token 预算 + 超长摘要压缩；循环检测（重复工具调用计数）；抓取正文截断。

### 6.4 数据模型（核心）
```python
@dataclass
class Report:
    conclusion: str            # 最终报告（markdown，结论带 [n] 引用编号）
    claims: list["Claim"]      # 结论拆成的可校验断言（评测阶段启用）
@dataclass
class Claim:
    text: str
    refs: list[str]            # 支持该断言的来源 URL

# 观测（每步）——
Step = {index, kind: "reasoning"|"tool_call"|"tool_result"|"final",
        content, tool?: {name, args}, ok?: bool,
        tokens?: int, duration_ms?: int, ts: ISO时间}
# 评测输出——
EvalCase = {id, question, key_facts: [str], refs: [权威来源URL]}
EvalReport = {case_id, scores: {metric: float}, failures: [失败断言+原因]}
```

### 6.5 评测层 `src/eval/`（W3 核心，主角）
- `AgentProtocol(Protocol)`: `def research(self, question: str) -> Report` —— **Harness 只依赖此协议，不依赖 Agent 内部实现** → 评测工具可复用于任何同类 Agent。
- `EvalHarness(dataset, metrics)`：`run(agent) -> EvalReport`；`compare(before, after)` 回归对比。
- 指标（定义 + 算法）：

| 指标 | 定义 | 算法 | 判定通道 |
|---|---|---|---|
| 引用准确率 CitationAccuracy | 断言有引用、且引用确实支持该断言 | 有支持引用断言数 / 总断言数 | 规则 + LLM-as-judge + 人工抽样 |
| 事实正确率 Factuality | 断言与标准事实点一致 | 一致断言 / 总断言 | 人工标注 key_facts 比对 |
| 覆盖度 Coverage | 标准事实点被报告覆盖比例 | 覆盖 key_facts / 总 key_facts | 规则（关键词）+ 抽样 |
| 忠实度 Faithfulness | 断言忠于引用来源、未编造 | 忠实断言 / 总断言 | 规则 + judge 双通道 |

- 判定原则：先规则（引用 URL 有效、出现在抓取内容中），再 LLM-as-judge（"引用是否支持该断言"，要求输出 支持/不支持/不确定 + 一句话理由），人工抽样 ≥20% 校准，校准分歧计入报告。
- 评测集规范：20 条起步（P1 扩到 50）；每题标注 3–5 个 `key_facts` + 权威 `refs`；**评测集与 prompt 调优过程隔离**（防过拟合）；版本化存储 `datasets/*.json`。

### 6.6 可观测层 `src/observability/`（W4）
- `Tracer`：Agent 循环每步调用 `tracer.step(Step)`，追加写入 `logs/trace-<runid>.jsonl`。
- `Analyzer`：聚合失败类型、平均耗时、token 消耗、最长步数 → 定位短板（如"哪类问题引用差"）→ 反哺 Agent 改进 → 再用 Harness 复测（形成闭环）。

### 6.7 API 服务层 `src/api/`（Phase 4+）
- FastAPI：`server.py` + `schemas.py`（Pydantic 模型）。
- 端点总览：

| 方法 | 路径 | 说明 | 阶段 |
|---|---|---|---|
| GET | `/api/health` | 存活探测 | P1 |
| POST | `/api/research` | 同步执行一次调研，返回报告 | P1 |
| POST | `/api/research/stream` | SSE 流式：逐步推送事件 | P2 |
| GET | `/` | （可选）静态托管 kimi 前端 `frontend/index.html` | P1 |

- CORS：开发期放开（`allow_origins=["*"]`），支持 `file://` 直接打开前端联调。
- 并发：demo 场景数并发即可，不做排队；不做鉴权（**本地工具定位，严禁裸奔公网**）。

> **API 完整契约（请求/响应/错误码/SSE 事件格式）见 `前端交接文档.md` §4—§7，该文档是前后端对接的唯一事实来源。**

## 7. 里程碑与验收（Phase 0 已完成）

| Phase | 内容 | 验收标准（DoD） | 状态 |
|---|---|---|---|
| 0 | 骨架代码 + 开题/Spec | ReAct 循环 + 搜索工具可运行 | ✅ 代码已生成 |
| 1 | 填 key 跑通命令行 | `python -m src.main "问题"` 输出带引用小结 | ⏳ 待你实测 |
| 2 | 抓取工具 + 上下文管理 + 健壮性 | 自主多轮「搜索→抓取→再搜索」，单次失败不崩 | |
| 3 | 评测工具 + 20 条评测集 | `EvalHarness.run(任意实现协议的 Agent)` 出 4 指标分 | |
| 4 | 可观测 + 量化迭代 | 改进前后两组真实指标，形成 X%→Y% | |
| 5 | FastAPI + kimi 前端对接 | Web UI 输入问题→出报告，端到端可用 | |
| 6 | GitHub 发布 | README + demo 录屏 + 开源仓库 | |

**时间盒提醒**：若 Phase 3 做不完，宁可「Agent 简单 + 评测扎实」，不要「Agent 花哨 + 评测空壳」——评测才是卖点。

## 8. 错误处理与异常约定

| 场景 | 处理 |
|---|---|
| LLM 网络失败/超时 | 分类为上游错误，重试 ≤2 次（指数退避）后返回可读错误 |
| LLM 鉴权失败（key 无效） | 明确报 401 类错误，前端提示"检查 API Key" |
| 余额不足/限流 | 映射 429/402 语义错误，提示用户 |
| 工具调用参数 JSON 解析失败 | 兜底空参数 → 让 LLM 重试或报"参数错误" |
| 搜索无结果/超时 | 返回可读文本给 LLM（不中断循环），最多连续 3 次空结果后建议结束 |
| 达到最大步数 | 强制总结并标注"受步数限制，建议人工复核" |
| **全链路红线** | 日志/返回给用户的内容不出现明文完整 key（脱敏 `sk-***`）；`.env` 永不入库 |

## 9. 版本管理、GitHub 与隐私红线

1. `git init`（在 `D:\boss\research-agent\`），`main` 分支 + 简单提交（中文/英文均可，信息要完整）。
2. `.gitignore` 必含：`.env`、`logs/`、`__pycache__/`、`.venv/`。
3. **隐私红线**：仓库内禁止出现——任何真实 API key、实习公司源码/文档/图片、公司名与现场信息。项目定位是"个人开源作品"，必须与实习内容完全隔离。
4. README 结构（Phase 6 完善）：项目名 + 一句话 + demo 动图/截图 → 特性（重点写评测体系）→ 架构图 → 快速开始（clone/装依赖/填 key/跑）→ 评测集说明 → 截图 → License(MIT) → 致谢。
5. 仓库名建议：`verilens`（本地目录名不改，GitHub 仓库名可独立）。

## 10. 分发与"惠及他人"边界（决策记录）

- **现在/近期**：GitHub 开源 = 别人 `git clone → pip install → 填自己 key → 跑起来`。这就是"惠及他人"的现实形态，也是 GPT Researcher 等知名项目的形态。零边际成本。
- **明确不做**：PyInstaller 打 exe、多平台安装包——体积大、依赖坑多、对求职无加分；做"多版本安装包"是在为一个还不存在的用户群付费。
- **远期（若真有用户）**：可考虑 ① 一键启动脚本（`run.bat`）降低门槛；② 租服务器 + 自付 API 费提供公共实例（持续成本，届时再评估）；③ 加本地模型兜底（Ollama）实现真正"免 key"。

## 11. 风险与对策

| 风险 | 对策 |
|---|---|
| DuckDuckGo 国内网络不稳定 | search.py 已兜底为错误文本；备选 Tavily/博查（需 key） |
| 豆包模型 function calling 格式差异 | 先 DeepSeek 验证代码，再切豆包；协议层统一在 `llm.py` 收敛 |
| 评测集质量差 → 数字失真 | 人工标注 + 抽样校准 + 评测集评审（他人试跑） |
| 时间不够 | 时间盒：评测优先于 UI；Agent 可简化 |
| LLM 判 LLM 有偏差 | 双通道 + 人工抽样 ≥20%，分歧记录在案 |
| 面试被问"2026 做 Agent 不新鲜" | 口径：卖点是评测/可观测/可量化，Agent 只是载体（见 §12） |

## 12. 求职联动（简历与面试口径）

- 简历条目核心句式（Phase 4 拿到真实数字后定稿）：「为 X Agent 自建评测与可观测体系：4 指标量化，引用准确率从 A% 提升至 B%；评测工具实现为与 Agent 解耦的 Harness，可复用于任意同类 Agent」。
- 面试深挖点见 `开题文档.md` §11（含评测客观性、防过拟合、LLM-as-judge 偏差、手写 ReAct 理由等）。
- 时间线口径：VeriLens 为独立个人项目（与实习无关的原创代码），GitHub 可公开。

## 13. 目录结构（目标态）

```
verilens/
├── SPEC.md / 开题文档.md / 前端交接文档.md
├── README.md / requirements.txt / .env.example / .env(忽略) / .gitignore
├── src/
│   ├── agent/（loop.py llm.py context.py report.py tools/）
│   ├── eval/（protocol.py harness.py metrics.py judge.py dataset.py）
│   ├── observability/（tracer.py analyzer.py）
│   └── api/（server.py schemas.py）          # Phase 4+
├── frontend/index.html                        # kimi 交付物，Phase 5
├── datasets/*.json  ├── logs/  ├── tests/
```
