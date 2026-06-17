import re
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from src.tools import TOOLS, TOOLS_SCHEMA, search_docs_with_sources

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"]
)

def build_system_prompt(stm32_model: str) -> str:
    return f"""You are an expert STM32 embedded systems AI assistant specialized in {stm32_model}.

IMPORTANT RULES:
- Never output raw JSON or function call syntax in your text response.
- Always use the provided tools directly via the function calling mechanism.
- You MUST call search_docs BEFORE calling generate_code or explain_register. No exceptions.
- Never skip search_docs, even if you think you already know the answer.

You have access to three tools:
- search_docs: Search STM32 reference manuals and datasheets for relevant context
- generate_code: Generate {stm32_model} HAL C code
- explain_register: Get a detailed breakdown of any STM32 register

Mandatory workflow for EVERY question:
Step 1. ALWAYS call search_docs first with a relevant query to find documentation
Step 2. If the user wants a register explained, call explain_register
Step 3. If the user wants code, call generate_code using knowledge from step 1
Step 4. Give your final answer, citing which parts of the documentation you used

Target everything specifically for {stm32_model}.
"""

def _parse_inline_tool_call(text: str):
    match = re.search(
        r'\{[\s\S]*?"name"\s*:\s*"(\w+)"[\s\S]*?"parameters"\s*:\s*(\{[\s\S]*?\})\s*\}',
        text
    )
    if not match:
        return None
    try:
        name = match.group(1)
        params = json.loads(match.group(2))
        return {"name": name, "params": params}
    except Exception:
        return None


def run_agent(
    question: str,
    history: list,
    stm32_model: str = "STM32F103",
    max_iterations: int = 6
):
    """
    Returns: (final_answer, steps, updated_history, all_sources, iterations_used)
    """
    messages = [{"role": "system", "content": build_system_prompt(stm32_model)}]
    messages += history
    messages.append({"role": "user", "content": question})

    steps = []
    all_sources = []
    final_answer = ""
    iterations_used = 0

    MODELS = [
        "meta/llama-3.3-70b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.1-70b-instruct",
    ]

    def call_llm(msgs, use_tools=True):
        last_err = None
        for model in MODELS:
            try:
                kwargs = dict(model=model, messages=msgs, temperature=0.2, max_tokens=2048)
                if use_tools:
                    kwargs["tools"] = TOOLS_SCHEMA
                    kwargs["tool_choice"] = "auto"
                return client.chat.completions.create(**kwargs)
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"All models failed. Last error: {last_err}")

    def execute_tool(tool_name, tool_args):
        if tool_name == "search_docs":
            query = tool_args.get("query", "")
            k = int(tool_args.get("k", 5))
            result, sources = search_docs_with_sources(query, k)
            all_sources.extend(sources)
            preview = str(result)[:120].replace("\n", " ")
            steps.append(f"📄 **搜尋結果**：找到 {len(sources)} 筆相關文件片段")
            steps.append(f"💡 **內容摘要**：{preview}…")
            return result
        elif tool_name == "generate_code":
            description = tool_args.get("description", "")
            model_arg = tool_args.get("stm32_model", stm32_model)
            result = TOOLS["generate_code"](description, model_arg)
            steps.append(f"💻 **生成程式碼**：針對 `{model_arg}`，描述：{description[:80]}")
            return result
        elif tool_name == "explain_register":
            result = TOOLS["explain_register"](**tool_args)
            reg = tool_args.get("register_name", "")
            preview = str(result)[:120].replace("\n", " ")
            steps.append(f"📖 **解析暫存器**：`{reg}` bit-field 拆解完成")
            steps.append(f"💡 **暫存器摘要**：{preview}…")
            return result
        elif tool_name in TOOLS:
            try:
                result = TOOLS[tool_name](**tool_args)
                steps.append(f"✅ **{tool_name}** 執行完成")
                return result
            except Exception as e:
                steps.append(f"❌ **{tool_name}** 執行失敗：{e}")
                return f"Tool execution error: {e}"
        else:
            steps.append(f"❌ 未知工具：`{tool_name}`")
            return f"Error: unknown tool '{tool_name}'"

    steps.append(f"🚀 **開始處理**：目標晶片 `{stm32_model}`")
    steps.append(f"❓ **使用者問題**：{question}")

    for iteration in range(max_iterations):
        iterations_used = iteration + 1
        steps.append("---")
        steps.append(f"### 🔄 第 {iteration + 1} 輪推理")

        res = call_llm(messages, use_tools=True)
        msg = res.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            content = msg.content or ""
            inline_call = _parse_inline_tool_call(content)
            if inline_call and iteration < max_iterations - 1:
                name = inline_call["name"]
                params = inline_call["params"]
                steps.append(f"⚠️ **偵測到 inline tool call**，自動執行 `{name}`")
                steps.append(f"🔧 **呼叫工具**：`{name}({json.dumps(params, ensure_ascii=False)})`")
                tool_result = execute_tool(name, params)
                if isinstance(tool_result, str) and len(tool_result) > 3000:
                    tool_result = tool_result[:3000] + "\n...[truncated]"
                messages.append({"role": "user", "content": f"Tool result for {name}:\n{tool_result}"})
                continue

            preview = content[:200].replace("\n", " ")
            steps.append(f"💬 **LLM 決定直接回答**")
            steps.append(f"📝 **答案預覽**：{preview}{'…' if len(content) > 200 else ''}")
            final_answer = content
            break

        tool_names = [tc.function.name for tc in msg.tool_calls]
        steps.append(f"🧠 **LLM 推理**：決定呼叫 `{'`、`'.join(tool_names)}`")

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            steps.append(f"🔧 **呼叫工具**：`{tool_name}({json.dumps(tool_args, ensure_ascii=False)})`")
            tool_result = execute_tool(tool_name, tool_args)

            if isinstance(tool_result, str) and len(tool_result) > 3000:
                tool_result = tool_result[:3000] + "\n...[truncated]"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result)
            })

    else:
        steps.append("---")
        steps.append(f"⚠️ **達到最大迭代次數（{max_iterations}）**，強制總結")
        messages.append({"role": "user", "content": "Please summarize your findings and give the final answer now."})
        res = call_llm(messages, use_tools=False)
        final_answer = res.choices[0].message.content or ""
        steps.append("💬 **強制總結完成**")

    steps.append("---")
    steps.append(f"✅ **完成**：共執行 {iterations_used} 輪，引用 {len(all_sources)} 筆來源文件")

    updated_history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": final_answer}
    ]
    if len(updated_history) > 20:
        updated_history = updated_history[-20:]

    # 明確回傳 5 個值
    return final_answer, steps, updated_history, all_sources, iterations_used