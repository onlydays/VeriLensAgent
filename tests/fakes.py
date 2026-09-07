# -*- coding: utf-8 -*-
"""可编程的假 LLM / 假工具：让单元测试不依赖真实 API 与网络。"""
from src.agent.llm import StepResult
from src.agent.tools.base import Tool


class ScriptedLLM:
    """按预设脚本依次返回 StepResult；记录每次 chat 的 messages 与 tools 参数。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []        # 每次 chat 收到的 messages
        self.tools_seen = []   # 每次 chat 收到的 tools（用于断言强制总结轮不带工具）

    def chat(self, messages, tools=None):
        self.calls.append(list(messages))
        self.tools_seen.append(tools)
        if not self.script:
            return StepResult(is_final=True, text="（脚本耗尽）")
        return self.script.pop(0)


class FixedTool(Tool):
    """返回固定观察文本的假工具。"""

    name = "fixed_tool"
    description = "固定返回结果的假工具"
    parameters = {"type": "object", "properties": {}}

    def __init__(self, text="固定观察结果"):
        self.text = text

    def run(self, **kwargs) -> str:
        return self.text


class BoomTool(Tool):
    """执行必然抛异常的假工具：验证循环的错误兜底。"""

    name = "boom_tool"
    description = "总是失败的假工具"
    parameters = {"type": "object", "properties": {}}

    def run(self, **kwargs) -> str:
        raise RuntimeError("工具内部爆炸")
