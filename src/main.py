"""入口。

用法（在项目根目录 research-agent/ 下）：
    python -m src.main "帮我调研 Go 和 Rust 在云原生方向的现状对比"
"""
import sys

from dotenv import load_dotenv

from .agent.llm import LLM
from .agent.loop import ResearchAgent
from .agent.tools.search import SearchTool


def main():
    load_dotenv()  # 读取项目根目录的 .env

    if len(sys.argv) < 2:
        print('用法：python -m src.main "你的调研问题"')
        return

    question = sys.argv[1]
    llm = LLM()
    agent = ResearchAgent(llm=llm, tools=[SearchTool()])

    print(f"问题：{question}\n")
    report = agent.research(question)

    print("=" * 60)
    print(report.conclusion)


if __name__ == "__main__":
    main()
