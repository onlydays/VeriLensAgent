"""网页搜索工具（DuckDuckGo，免费无需额外 key）。"""
from .base import Tool


def _get_ddgs_class():
    """兼容两种安装来源：ddgs 或 duckduckgo_search。"""
    try:
        from ddgs import DDGS
        return DDGS
    except ImportError:
        from duckduckgo_search import DDGS
        return DDGS


class SearchTool(Tool):
    name = "web_search"
    description = (
        "搜索互联网，返回相关结果的标题、链接和摘要。"
        "用于查找技术选型、官方文档、对比评测等信息。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {
                "type": "integer",
                "description": "返回结果数量，默认 5，最多 10",
            },
        },
        "required": ["query"],
    }

    def run(self, query: str, max_results: int = 5) -> str:
        DDGS = _get_ddgs_class()
        max_results = max(1, min(int(max_results), 10))

        lines = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    title = r.get("title", "")
                    href = r.get("href", "")
                    body = r.get("body", "")
                    lines.append(f"### {title}\n{href}\n{body}")
        except Exception as e:
            return f"搜索出错：{e}"

        if not lines:
            return "未找到相关结果"
        return "\n\n".join(lines)
