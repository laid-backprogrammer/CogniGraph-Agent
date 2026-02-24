import json
import os

# def rename_keys_in_conversations(data):
#     """
#     递归地遍历 JSON 数据，将 'from' 键替换为 'role'，将 'value' 键替换为 'content'。
#     """
#     if isinstance(data, dict):
#         new_dict = {}
#         for key, value in data.items():
#             if key == "from":
#                 new_key = "role"
#             elif key == "value":
#                 new_key = "content"
#             else:
#                 new_key = key
#             new_dict[new_key] = rename_keys_in_conversations(value)
#         return new_dict
#     elif isinstance(data, list):
#         return [rename_keys_in_conversations(item) for item in data]
#     else:
#         return data


def rename_keys_in_conversations(data):
    """
    递归地遍历 JSON 数据：
    1. 将 'from' 键替换为 'role'。
    2. 将 'value' 键替换为 'content'。
    3. 如果 'role' 键的值是 'human'，则替换为 'user'。
    4. 如果 'role' 键的值是 'gpt'，则替换为 'assistant'。
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            # 首先处理键的重命名
            if key == "from":
                new_key = "role"
            elif key == "value":
                new_key = "content"
            else:
                new_key = key

            # 递归处理值
            processed_value = rename_keys_in_conversations(value)

            # 在这里添加针对 'role' 键值的转换逻辑
            if new_key == "role":
                if processed_value == "human":
                    processed_value = "user"
                elif processed_value == "gpt":
                    processed_value = "assistant"

            new_dict[new_key] = processed_value
        return new_dict
    elif isinstance(data, list):
        return [rename_keys_in_conversations(item) for item in data]
    else:
        return data  # 非字典非列表的数据直接返回
# 遍历当前文件夹
# 用于存储所有处理过的 JSON 数据
all_merged_data = []

# 遍历当前文件夹
for filename in os.listdir("./"):
    if filename.endswith(".json"):
        print(f"正在处理文件：{filename}")
        filepath = os.path.join("./", filename)  # 获取完整文件路径
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)

                # 调用函数进行数据转换
                converted_data = rename_keys_in_conversations(data)

                # 假设每个 JSON 文件都是一个包含多个对话对象的列表
                # 或者，如果每个文件只包含一个对话对象，也可以直接 extend
                if isinstance(converted_data, list):
                    all_merged_data.extend(converted_data)
                else:  # 如果文件内容是一个单独的字典对象，则将其放入列表中
                    all_merged_data.append(converted_data)

                print(f"文件 {filename} 处理并添加到合并列表。")

            except json.JSONDecodeError as e:
                print(f"错误：无法解析文件 {filename}。{e}")
            except Exception as e:
                print(f"处理文件 {filename} 时发生未知错误：{e}")

# 所有文件处理完毕后，将合并的数据写入一个新的 JSON 文件
output_filename = "merged_output.json"
if all_merged_data:
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_merged_data, f, indent=4, ensure_ascii=False)
    print(f"\n所有 JSON 文件已合并到 {output_filename}。")
else:
    print("\n没有找到有效的 JSON 文件进行合并。")

print("所有 JSON 文件处理完毕。")

