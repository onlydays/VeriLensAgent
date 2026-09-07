# -*- coding: utf-8 -*-
"""ReAct 循环单元测试：不依赖真实 LLM 与网络。"""
from src.agent.llm import StepResult
from src.agent.loop import ResearchAgent

from fakes import BoomTool, FixedTool, ScriptedLLM

TOOL_CALL = lambda name, args, cid="call_1": {"id": cid, "name": name, "arguments": args}


def _tool_msgs(messages):
    """取出对话中所有 role=tool 的消息。"""
    return [m for m in messages if m.get("role") == "tool"]


def test_final_answer_immediately_when_no_tools_needed():
    """问题简单到模型直接回答：只调用一次 LLM，结论原样返回。"""
    llm = ScriptedLLM([StepResult(is_final=True, text="直接回答")])
    report = ResearchAgent(llm=llm, tools=[FixedTool()]).research("q")

    assert report.conclusion == "直接回答"
    assert len(llm.calls) == 1


def test_single_tool_call_then_final():
    """模型先调用一次工具，观察结果回填后再给结论。"""
    tool = FixedTool("搜索到 3 条结果")
    llm = ScriptedLLM([
        StepResult(is_final=False, tool_calls=[TOOL_CALL("fixed_tool", {})]),
        StepResult(is_final=True, text="结论：A 更优"),
    ])
    report = ResearchAgent(llm=llm, tools=[tool]).research("测试问题")

    assert report.conclusion == "结论：A 更优"
    second = llm.calls[1]
    tool_msgs = _tool_msgs(second)
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["tool_call_id"] == "call_1"
    assert tool_msgs[0]["content"] == "搜索到 3 条结果"


def test_parallel_tool_calls_generate_multiple_tool_messages():
    """模型一次请求两个工具：必须回填两条 tool 消息，id 一一对应。"""
    tool = FixedTool("结果")
    llm = ScriptedLLM([
        StepResult(is_final=False, tool_calls=[
            TOOL_CALL("fixed_tool", {}, "call_a"),
            TOOL_CALL("fixed_tool", {}, "call_b"),
        ]),
        StepResult(is_final=True, text="完成"),
    ])
    report = ResearchAgent(llm=llm, tools=[tool]).research("q")

    assert report.conclusion == "完成"
    tool_msgs = _tool_msgs(llm.calls[1])
    assert len(tool_msgs) == 2
    assert {m["tool_call_id"] for m in tool_msgs} == {"call_a", "call_b"}


def test_unknown_tool_returns_error_text_without_crashing():
    """模型请求不存在的工具：错误文本回填给模型，循环继续。"""
    tool = FixedTool("结果")
    llm = ScriptedLLM([
        StepResult(is_final=False, tool_calls=[TOOL_CALL("no_such_tool", {})]),
        StepResult(is_final=True, text="继续完成"),
    ])
    report = ResearchAgent(llm=llm, tools=[tool]).research("q")

    assert report.conclusion == "继续完成"
    content = _tool_msgs(llm.calls[1])[0]["content"]
    assert "未知工具" in content


def test_tool_exception_returns_error_text_without_crashing():
    """工具内部抛异常：异常被吞成可读文本，循环不崩。"""
    tool = BoomTool()
    llm = ScriptedLLM([
        StepResult(is_final=False, tool_calls=[TOOL_CALL("boom_tool", {})]),
        StepResult(is_final=True, text="已处理失败"),
    ])
    report = ResearchAgent(llm=llm, tools=[tool]).research("q")

    assert report.conclusion == "已处理失败"
    content = _tool_msgs(llm.calls[1])[0]["content"]
    assert "工具执行失败" in content


def test_max_steps_forces_final_without_tools():
    """回归（曾修复的 bug）：达到 max_steps 后最后一次调用不得携带 tools，
    避免模型继续要求调工具导致结论为空。"""
    tool = FixedTool("结果")
    always_tool = StepResult(is_final=False, tool_calls=[TOOL_CALL("fixed_tool", {})])
    llm = ScriptedLLM([always_tool] * 3)
    agent = ResearchAgent(llm=llm, tools=[tool], max_steps=3)

    report = agent.research("q")

    assert report.conclusion != ""            # 强制总结必须给出结论
    assert llm.tools_seen[-1] is None         # 最后一轮不带 tools
    last_user = [m["content"] for m in llm.calls[-1] if m.get("role") == "user"]
    assert any("最大步数" in c for c in last_user)


def test_forced_final_falls_back_when_model_returns_empty():
    """极端兜底：即使强制总结轮模型仍返回空，也要给出可读结论而非空串。"""
    tool = FixedTool("结果")
    always_tool = StepResult(is_final=False, tool_calls=[TOOL_CALL("fixed_tool", {})])
    llm = ScriptedLLM([always_tool] * 4)  # 第 4 次（强制轮）仍返回非 final
    agent = ResearchAgent(llm=llm, tools=[tool], max_steps=3)

    report = agent.research("q")

    assert report.conclusion != ""
    assert "达到步数上限" in report.conclusion
