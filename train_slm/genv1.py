import json
import random
import datetime
import uuid
from typing import List, Dict
from openai import OpenAI
from tqdm import tqdm

# ================= 配置区域 =================
OPENAI_API_KEY = "sk-"  # 替换你的 Key
OPENAI_BASE_URL = "https://api.v36.cm/v1"  # 如果用中转，请修改此地址
API_KEY = "sk-LzLhQbaHHTkldV2432F8D9631c67412283471dBeDe7b2461"  # 替换为你的 Key
BASE_URL = "https://api.v36.cm/v1"  # 如果用中转，请修改此处
MODEL_NAME = "gemini-2.5-flash"  # 
OUTPUT_FILE = "trainslm/fitness_schedule_train_data3.json"
TOTAL_SAMPLES = 500
BATCH_SIZE = 5  # 每次请求生成几条对话，节省交互次数

# 完整目录池 (用于随机抽取构建 System Prompt)
FULL_CATEGORY_POOL = {
    "fitness/workout": "力量训练 | 撸铁,器械,增肌",
    "fitness/cardio": "有氧运动 | 跑步,游泳,骑行,跳绳",
    "fitness/record": "身体数据 | 体重,体脂,打卡",
    "life/health": "健康医疗 | 就医,体检,吃药",
    "life/social": "社交活动 | 聚会,约会,家庭",
    "life/errand": "日常事务 | 购物,缴费,快递,办证",
    "life/rest": "休闲娱乐 | 电影,游戏,旅行",
    "study/course": "课程培训 | 上课,考试,网课",
    "study/read": "阅读笔记 | 读书,笔记",
    "study/skill": "技能提升 | 练习,刷题",
    "work/task": "日常任务 | 开发,设计,文档",
    "work/meeting": "会议 | 周会,面试,评审",
    "work/project": "项目节点 | 上线,deadline",
    "work/admin": "行政事务 | 报销,请假,出差",
    "money/income": "收入 | 工资,奖金,副业",
    "money/expense": "支出 | 餐饮,交通,购物",
    "money/invest": "投资理财 | 基金,股票",
    "money/transfer": "转账往来 | 还款,借出",
    "other": "其它 | 未分类事项"
}

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# ================= 辅助函数 =================

def get_random_time():
    """生成一个随机的当前时间（模拟）"""
    start_date = datetime.datetime(2024, 1, 1)
    end_date = datetime.datetime(2026, 12, 31)
    random_seconds = random.randint(0, int((end_date - start_date).total_seconds()))
    current_time = start_date + datetime.timedelta(seconds=random_seconds)
    # 格式化带星期几，帮助模型理解时间
    return current_time.strftime("%Y-%m-%d %H:%M:%S (%A)")


def get_random_categories(min_count=8, max_count=15):
    """
    随机抽取一部分目录结构，模拟用户自定义的不同环境。
    保证 'other' 总是存在。
    """
    keys = list(FULL_CATEGORY_POOL.keys())
    if "other" in keys: keys.remove("other")

    selected_count = random.randint(min_count, min(max_count, len(keys)))
    selected_keys = random.sample(keys, selected_count)
    selected_keys.append("other")  # 确保有兜底

    # 构建目录字符串
    cat_str_list = []
    for k in selected_keys:
        cat_str_list.append(f"{k} | {FULL_CATEGORY_POOL[k]}")

    # 随机打乱顺序
    random.shuffle(cat_str_list)
    return "\n".join(cat_str_list), selected_keys


def generate_batch(batch_size=5):
    """
    通过 Prompt 让 GPT-4o 生成一批训练数据。
    """

    # 1. 准备本次生成的环境
    current_time_str = get_random_time()
    categories_str, active_keys = get_random_categories()

    # 2. 构造 Meta-Prompt (指导 GPT 生成数据的 Prompt)
    system_instruction = f"""
    You are a synthetic data generator. Your task is to generate {batch_size} training examples for a fine-tuning task.

    ### Context
    The AI assistant helps users record life/work events into a structured format.

    ### Current Simulation Environment
    - **Current Time**: {current_time_str}
    - **Available Categories**:
    {categories_str}

    ### Generation Requirements
    Generate a JSON list containing {batch_size} items. Each item must simulate a user interaction.

    **Distribution:**
    - ~70% Positive Cases: The user input implies a recordable event (Schedule or Memory).
    - ~30% Negative Cases: The user input is chitchat, greeting, or vague complaints (Output "不需记录").

    **For Positive Cases:**
    1. `event`: Short title.
    2. `description`: Full detail.
    3. `class`: Choose strictly from the 'Available Categories' list above. If unsure, use 'other'.
    4. `is_schedule`: true if it's a future plan, false if it's a past record or general note.
    5. `remind_time`: 
       - If `is_schedule` is true, calculate the EXACT datetime string (YYYY-MM-DD HH:MM:SS) based on the user's input relative to '{current_time_str}'.
       - Example: If current is 2024-06-01 10:00:00 and user says "tomorrow afternoon 3pm", remind_time is "2024-06-02 15:00:00".
       - If `is_schedule` is false, leave empty string "".

    **For Negative Cases:**
    - User input: "Hello", "What's the weather", "I am sad without specific reason".
    - AI Output: "不需记录".

    ### Output Format (Strict JSON List)
    [
      {{
        "type": "positive",
        "user_input": "...",
        "tool_args": {{ "event": "...", "description": "...", "class": "...", "is_schedule": true, "remind_time": "..." }},
        "ai_response_text": "Confirmation message..."
      }},
      {{
        "type": "negative",
        "user_input": "...",
        "ai_response_text": "不需记录"
      }}
    ]
    """

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": "Generate the data batch now."}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        raw_content = completion.choices[0].message.content.strip()

        # --- 修复部分开始 ---

        # 1. 清理可能存在的 Markdown 标记 (有些模型即使设置了 json_object 也可能带 ```json)
        if raw_content.startswith("```"):
            raw_content = raw_content.replace("```json", "").replace("```", "").strip()

        # 2. 解析 JSON
        result_json = json.loads(raw_content)

        # 3. 类型判断：处理直接返回 List 或返回 Dict 的情况
        if isinstance(result_json, list):
            data_list = result_json
        elif isinstance(result_json, dict):
            # 尝试从常见的 key 中获取列表
            data_list = result_json.get("examples", result_json.get("data", []))
            # 兜底：如果是一个字典但没有 examples/data key，且看起来像单条数据，把它包进 list
            if not data_list and "user_input" in result_json:
                data_list = [result_json]
        else:
            data_list = []

        # --- 修复部分结束 ---

        return data_list, current_time_str, categories_str

    except Exception as e:
        print(f"Error generating batch: {e}")
        # 打印一下原始返回以便调试
        # print(f"Raw content was: {completion.choices[0].message.content}")
        return [], current_time_str, categories_str

# ================= 主流程 =================

def build_sharegpt_format(raw_item, current_time, category_str):
    """
    将生成器输出的原始数据转换为 ShareGPT 格式
    """
    # 构造 System Message
    tool_def = json.dumps([{
        "name": "Record",
        "description": "记录用户的日程安排事件",
        "parameters": {
            "type": "object",
            "properties": {
                "event": {"type": "string", "description": "事件名称"},
                "description": {"type": "string", "description": "事件详细描述"},
                "class": {"type": "string",
                          "description": f"分类路径，从以下目录中选择：{category_str.replace(chr(10), '; ')}"},
                "is_schedule": {"type": "boolean", "description": "是否为日程/待办"},
                "remind_time": {"type": "string",
                                "description": "如果是日程，填具体时间YYYY-MM-DD HH:MM:SS，否则填空字符串"}
            },
            "required": ["event", "description", "class", "is_schedule", "remind_time"]
        }
    }], ensure_ascii=False)

    system_content = f"Current Time: {current_time}\n\nList of tools: {tool_def}\n\nCategory Structure:\n{category_str}\n\n你的任务是判断用户输入是否是需要记录的日程安排信息。如果是，请调用Record工具记录；如果是闲聊、问候或其他不重要信息，请直接回复\"不需记录\"。"

    conversations = [
        {
            "from": "system",
            "value": system_content
        },
        {
            "from": "human",
            "value": raw_item['user_input']
        }
    ]

    if raw_item['type'] == 'negative':
        conversations.append({
            "from": "gpt",
            "value": "不需记录"
        })
    else:
        # Positive Case
        args = raw_item['tool_args']
        # 构造 Tool Call 字符串
        # 注意：这里模拟 Qwen/GLM 等常见的 tool call 格式，你可以根据你的具体 base model 调整 tag
        tool_call_str = f"<|tool_call_start|>[Record(event=\"{args['event']}\", description=\"{args['description']}\", class=\"{args['class']}\", is_schedule={str(args['is_schedule']).lower()}, remind_time=\"{args['remind_time']}\")]<|tool_call_end|>"

        conversations.append({
            "from": "gpt",
            "value": tool_call_str + "\n" + raw_item.get('ai_response_text', "已为您记录。")
        })

        # 模拟 Tool Result (Mock)
        conversations.append({
            "from": "tool",
            "value": json.dumps({"success": True, "message": "记录成功", "record_id": str(uuid.uuid4())[:8]})
        })

        # Final Response
        final_resp = f"记录完成。已归档至 {args['class']}。"
        if args['is_schedule']:
            final_resp += f" 提醒时间设定为 {args['remind_time']}。"

        conversations.append({
            "from": "gpt",
            "value": final_resp
        })

    return {
        "id": f"train_{uuid.uuid4().hex[:8]}",
        "conversations": conversations
    }


def main():
    all_data = []

    print(f"Start generating {TOTAL_SAMPLES} samples...")

    pbar = tqdm(total=TOTAL_SAMPLES)

    while len(all_data) < TOTAL_SAMPLES:
        batch_data, curr_time, cat_str = generate_batch(BATCH_SIZE)

        if not batch_data:
            continue

        for item in batch_data:
            try:
                formatted = build_sharegpt_format(item, curr_time, cat_str)
                all_data.append(formatted)
                pbar.update(1)
            except Exception as e:
                print(f"Skipping malformed item: {e}")

        # 实时保存，防止中断丢失
        if len(all_data) % 50 == 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
