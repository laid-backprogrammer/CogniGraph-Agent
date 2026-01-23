import time


# 模拟语音识别（非流式）
def speech_recognition_non_streaming(audio_data):
    print("🔴 语音识别开始...")
    time.sleep(1.5)  # 模拟语音识别延迟
    text = "我想知道北京的天气"
    print(f"🟢 语音识别完成: {text}")
    return text


# 模拟 Agent 处理（非流式）
def agent_process_non_streaming(input_text):
    print("🔴 Agent 处理开始...")
    time.sleep(1)  # 模拟思考延迟

    # 决定调用天气查询工具
    print("🟡 Agent 决定调用天气查询工具")
    tool_name = "query_weather"
    tool_input = {"city": "北京"}
    print(f"🟢 Agent 处理完成，工具调用: {tool_name}({tool_input})")
    return (tool_name, tool_input)


# 模拟工具调用（非流式）
def tool_call_non_streaming(tool_name, tool_input):
    print(f"🔴 工具调用开始: {tool_name}")
    time.sleep(2)  # 模拟工具调用延迟
    result = "北京今天天气晴朗，温度 25°C"
    print(f"🟢 工具调用完成: {result}")
    return result


# 模拟语音输出（非流式）
def speech_output_non_streaming(text):
    print("🔴 语音输出开始...")
    time.sleep(1.5)  # 模拟语音合成延迟
    print(f"🟢 语音输出完成: '{text}'")
    return True


# 完整非流式流程
def full_non_streaming_flow(audio_data):
    print("\n=== 非流式处理流程开始 ===")
    start_time = time.time()

    # 1. 语音识别
    text = speech_recognition_non_streaming(audio_data)

    # 2. Agent 处理
    tool_name, tool_input = agent_process_non_streaming(text)

    # 3. 工具调用
    tool_result = tool_call_non_streaming(tool_name, tool_input)

    # 4. 语音输出
    speech_output_non_streaming(tool_result)

    end_time = time.time()
    print(f"=== 非流式处理流程结束 ===")
    print(f"总耗时: {end_time - start_time:.2f} 秒")


# 测试
full_non_streaming_flow("模拟音频数据")

import time
import asyncio


# 模拟语音识别（流式）
async def speech_recognition_streaming(audio_chunks):
    print("🔴 语音识别开始（流式）...")
    recognized_text = ""

    for i, chunk in enumerate(audio_chunks):
        await asyncio.sleep(0.3)  # 模拟每个音频块的识别延迟
        # 简单模拟：每个音频块识别为一个字
        char = ["我", "想", "知", "道", "北", "京", "的", "天", "气"][i]
        recognized_text += char
        print(f"🟡 语音识别实时结果: {recognized_text}")

    print(f"🟢 语音识别完成（流式）: {recognized_text}")
    return recognized_text


# 模拟 Agent 处理（流式）
async def agent_process_streaming(input_text_chunks):
    print("🔴 Agent 处理开始（流式）...")
    full_text = input_text_chunks

    try:
        print("🟡 Agent 决定调用天气查询工具")
        tool_name = "query_weather"
        tool_input = {"city": "北京"}
        print(f"🟢 Agent 处理完成，工具调用: {tool_name}({tool_input})")
        return (tool_name, tool_input)
    except:
        return (None, None)


# 模拟工具调用（异步）
async def tool_call_streaming(tool_name, tool_input):
    print(f"🔴 工具调用开始: {tool_name}")
    await asyncio.sleep(1.5)  # 模拟工具调用延迟
    result = "北京今天天气晴朗，温度 25°C"
    print(f"🟢 工具调用完成: {result}")
    return result


# 模拟语音输出（流式）
async def speech_output_streaming(text):
    print("🔴 语音输出开始（流式）...")

    for char in text:
        await asyncio.sleep(0.2)  # 模拟每个字的合成延迟
        print(f"🟡 语音实时输出: {char}", end="", flush=True)

    print()
    print("🟢 语音输出完成（流式）")
    return True


# 完整流式流程
async def full_streaming_flow():
    print("\n=== 流式处理流程开始 ===")
    start_time = time.time()

    # 模拟音频块流
    audio_chunks = [b"chunk1", b"chunk2", b"chunk3", b"chunk4", b"chunk5",
                    b"chunk6", b"chunk7", b"chunk8", b"chunk9"]

    # 1. 流式语音识别
    recognized_text = speech_recognition_non_streaming

    tool_name, tool_input = await agent_process_streaming(recognized_text)

    if tool_name:
        # 3. 异步工具调用
        tool_result = await tool_call_streaming(tool_name, tool_input)

        # 4. 流式语音输出
        await speech_output_streaming(tool_result)

    end_time = time.time()
    print(f"=== 流式处理流程结束 ===")
    print(f"总耗时: {end_time - start_time:.2f} 秒")


# 测试
asyncio.run(full_streaming_flow())
