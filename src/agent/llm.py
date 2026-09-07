"""LLM 调用封装（OpenAI 兼容协议，DeepSeek / 豆包通用）。

通过 base_url 切换服务商：
- DeepSeek: base_url=https://api.deepseek.com, model=deepseek-chat
- 豆包(火山方舟): base_url=https://ark.cn-beijing.volces.com/api/v3, model=接入点ID/模型名
"""
import json
import os
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass
class StepResult:
    """Agent 单步决策结果：要么调用工具，要么给出最终答案。"""
    is_final: bool
    text: str = ""
    tool_calls: list = field(default_factory=list)  # [{"id", "name", "arguments"}]


class LLM:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.client = OpenAI(
            api_key=api_key or os.getenv("LLM_API_KEY"),
            base_url=base_url or os.getenv("LLM_BASE_URL"),
        )
        self.model = model or os.getenv("LLM_MODEL")
        if not self.model:
            raise ValueError("缺少 LLM_MODEL，请在 .env 或环境变量中配置")

    def chat(self, messages: list, tools: list = None) -> StepResult:
        """发一轮对话。tools 为 OpenAI 格式的 tool schema 列表。"""
        kwargs = dict(model=self.model, messages=messages, temperature=0.2)
        if tools:
            kwargs["tools"] = tools

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        # 模型决定调用工具
        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}  # 参数 JSON 解析失败时兜底为空，交由上层处理
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                })
            return StepResult(is_final=False, tool_calls=tool_calls)

        # 模型直接给出最终答案
        return StepResult(is_final=True, text=msg.content or "")
