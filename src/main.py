"""入口。

用法（在项目根目录 research-agent/ 下）：
    python -m src.main "帮我调研 Go 和 Rust 在云原生方向的现状对比"
"""
import sys

from dotenv import load_dotenv
from openai import (APIConnectionError, APITimeoutError, AuthenticationError,
                    BadRequestError, PermissionDeniedError, RateLimitError)

from .agent.llm import LLM
from .agent.loop import ResearchAgent
from .agent.tools.search import SearchTool


def _friendly_error(e: Exception) -> str:
    """把常见的上游错误翻译成可读提示，避免裸 traceback。"""
    if isinstance(e, AuthenticationError):
        return "API Key 无效或无权限：请检查 .env 中 LLM_API_KEY。"
    if isinstance(e, PermissionDeniedError):
        return "API Key 无权访问该模型：请检查模型名与账户权限。"
    if isinstance(e, RateLimitError):
        return "请求过于频繁或余额不足（限流）：请稍后重试或检查账户余额。"
    if isinstance(e, APITimeoutError):
        return "调用大模型超时：请重试；若持续出现请检查网络/代理。"
    if isinstance(e, APIConnectionError):
        return "无法连接大模型服务：请检查网络/代理与 LLM_BASE_URL。"
    if isinstance(e, BadRequestError):
        return f"请求被模型服务拒绝（{e}）：请检查 LLM_MODEL 是否填写正确。"
    return f"未预期错误：{type(e).__name__}: {e}"


def main():
    load_dotenv()  # 读取项目根目录的 .env

    if len(sys.argv) < 2:
        print('用法：python -m src.main "你的调研问题"')
        return

    question = sys.argv[1].strip()
    if not question:
        print("问题不能为空。")
        return

    llm = LLM()
    agent = ResearchAgent(llm=llm, tools=[SearchTool()])

    print(f"问题：{question}\n")
    try:
        report = agent.research(question)
    except Exception as e:  # 统一转可读提示，失败不裸崩
        print(f"❌ 调研失败：{_friendly_error(e)}")
        sys.exit(1)

    print("=" * 60)
    print(report.conclusion)


if __name__ == "__main__":
    main()
