"""工具抽象：统一 Tool 接口，新增工具只需继承并实现 run()。"""
from abc import ABC, abstractmethod


class Tool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema，供 LLM 生成调用参数

    @abstractmethod
    def run(self, **kwargs) -> str:
        """执行工具，返回字符串形式的观察结果。"""

    def to_openai_schema(self) -> dict:
        """转成 OpenAI function calling 需要的 tool schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
