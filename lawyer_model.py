import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role
import os
import json
import pandas as pd  # 导入用于时间戳

# 设置API密钥
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "sk-536e06bba87a456791d32486c7bd3393")

# 模型名称
lawyer_model = 'qwen-max-latest'

# 律师模型 system prompt
def load_lawyer_prompt():
    """从文件加载律师系统提示词"""
    try:
        with open('Lawyer_Prompt.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        # 如果文件不存在，使用默认提示词
        return "作为专精劳动法的资深律师，您在对话中必须始终以共情、专业的方式引导用户梳理案件细节。"

LAWYER_SYSTEM_PROMPT = load_lawyer_prompt()

def create_new_conversation():
    """创建新的对话历史"""
    return [{'role': Role.SYSTEM, 'content': LAWYER_SYSTEM_PROMPT}]

def chat_with_lawyer(message, conversation_history=None):
    """与律师AI进行对话
    
    Args:
        message (str): 用户输入的消息
        conversation_history (list, optional): 对话历史，如果为None则创建新对话
    
    Returns:
        tuple: (回复内容, 更新后的对话历史, 是否对话结束)
    """
    if conversation_history is None:
        conversation_history = create_new_conversation()
    
    # 添加用户输入到历史
    conversation_history.append({'role': Role.USER, 'content': message})
    
    # 调用API
    response = Generation.call(
        model=lawyer_model,
        messages=conversation_history,
        result_format='message'
    )
    
    if response.status_code == 200:
        lawyer_response = response.output.choices[0].message.content
        conversation_history.append({'role': Role.ASSISTANT, 'content': lawyer_response})
        
        # 检查是否结束对话
        conversation_ended = "？" not in lawyer_response and "?" not in lawyer_response
        
        if conversation_ended:
            # 保存对话为ShareGPT格式
            save_conversation_to_json(conversation_history)
            return lawyer_response + "\n\n对话已结束，并保存为JSON文件。", conversation_history, True
        
        return lawyer_response, conversation_history, False
    else:
        return f"API错误: {response.code} - {response.message}", conversation_history, False

def save_conversation_to_json(conversation_history):
    """保存对话历史为ShareGPT格式的JSON文件"""
    sharegpt_data = []
    current_conversation_messages = []
    system_prompt_for_current_conversation = None

    for msg in conversation_history:
        role = msg['role']
        content = msg['content']

        if role == Role.SYSTEM or role == 'system':
            if current_conversation_messages:
                sharegpt_data.append({
                    "system_prompt": system_prompt_for_current_conversation if system_prompt_for_current_conversation else LAWYER_SYSTEM_PROMPT,
                    "conversations": current_conversation_messages
                })
                current_conversation_messages = []
            system_prompt_for_current_conversation = content
        elif role == Role.USER or role == 'user':
            current_conversation_messages.append({"from": "human", "value": content})
        elif role == Role.ASSISTANT or role == 'assistant':
            current_conversation_messages.append({"from": "gpt", "value": content})
    
    if current_conversation_messages:
        sharegpt_data.append({
            "system_prompt": system_prompt_for_current_conversation if system_prompt_for_current_conversation else LAWYER_SYSTEM_PROMPT,
            "conversations": current_conversation_messages
        })

    # 确保目录存在
    os.makedirs("./conversation_datasets", exist_ok=True)
    
    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    sharegpt_filename = f"./conversation_datasets/sharegpt_conversation_manual_{timestamp}.json"
    with open(sharegpt_filename, 'w', encoding='utf-8') as f:
        json.dump(sharegpt_data, f, ensure_ascii=False, indent=2)
    
    return sharegpt_filename


def main():
    """示例用法"""
    print("律师AI对话系统")
    print("输入 'exit' 退出程序")
    
    conversation_history = None
    
    while True:
        user_input = input("\n您: ")
        if user_input.lower() == 'exit':
            break
            
        response, conversation_history, ended = chat_with_lawyer(user_input, conversation_history)
        print(f"律师: {response}")
        
        if ended:
            conversation_history = None  # 重置对话历史


if __name__ == "__main__":
    main()