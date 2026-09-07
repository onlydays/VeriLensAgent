"""手写 ReAct 循环：推理 → 调用工具 → 观察 → 再推理。"""
import json
from dataclasses import dataclass, field

from .llm import LLM, StepResult


SYSTEM_PROMPT = (
    "你是一个技术调研 Agent。你的任务是通过搜索工具收集、交叉验证信息，"
    "最后输出一份带来源引用的调研报告。\n"
    "规则：\n"
    "1. 先搜索，再决定是继续搜索还是给出结论；\n"
    "2. 关键结论必须标注来源 URL；\n"
    "3. 信息不足时继续搜索，不要凭空编造。"
)


@dataclass
class Report:
    conclusion: str
    claims: list = field(default_factory=list)  # 第一版暂空，评测阶段再细化


class ResearchAgent:
    def __init__(self, llm: LLM, tools: list, max_steps: int = 8):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.max_steps = max_steps

    def research(self, question: str) -> Report:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        tool_schemas = [t.to_openai_schema() for t in self.tools.values()]

        for _ in range(self.max_steps):
            result = self.llm.chat(messages, tool_schemas)
            if result.is_final:
                return Report(conclusion=result.text)

            # 把 assistant 的 tool_calls 写回对话，再逐个执行工具并回填结果
            messages.append(self._assistant_msg(result))
            for tc in result.tool_calls:
                obs = self._execute(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": obs,
                })

        # 达到最大步数仍未收敛：强制基于已有信息总结
        messages.append({
            "role": "user",
            "content": "已到最大步数，请基于当前已收集的信息，直接输出最终调研报告。",
        })
        final = self.llm.chat(messages, tool_schemas)
        return Report(conclusion=final.text)

    def _assistant_msg(self, result: StepResult) -> dict:
        """把 tool_calls 构造成 OpenAI 兼容的 assistant 消息。"""
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                    },
                }
                for tc in result.tool_calls
            ],
        }

    def _execute(self, tc: dict) -> str:
        """执行单个工具调用，失败时返回可读的错误文本，而不是直接崩溃。"""
        tool = self.tools.get(tc["name"])
        if tool is None:
            return f"错误：未知工具 {tc['name']}"
        try:
            return tool.run(**tc["arguments"])
        except TypeError as e:
            return f"工具参数错误：{e}"
        except Exception as e:
            return f"工具执行失败：{e}"
