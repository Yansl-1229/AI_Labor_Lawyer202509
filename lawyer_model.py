import dashscope
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role
import os
import json
import pandas as pd  # 导入用于时间戳
from abc import ABC, abstractmethod
from volcenginesdkarkruntime import Ark

# 模型适配器基类
class ModelAdapter(ABC):
    """模型适配器基类，定义统一的接口"""
    
    @abstractmethod
    def call_api(self, messages, model_name):
        """调用API的抽象方法"""
        pass
    
    @abstractmethod
    def format_response(self, response):
        """格式化响应的抽象方法"""
        pass

# DashScope模型适配器
class DashScopeAdapter(ModelAdapter):
    """DashScope API适配器"""
    
    def __init__(self):
        # 设置API密钥
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "sk-536e06bba87a456791d32486c7bd3393")
    
    def call_api(self, messages, model_name='qwen-max-latest'):
        """调用DashScope API"""
        response = Generation.call(
            model=model_name,
            messages=messages,
            result_format='message'
        )
        return response
    
    def format_response(self, response):
        """格式化DashScope响应"""
        if response.status_code == 200:
            content = response.output.choices[0].message.content
            return {
                'success': True,
                'content': content,
                'error': None
            }
        else:
            return {
                'success': False,
                'content': None,
                'error': f"API错误: {response.code} - {response.message}"
            }

# Doubao模型适配器
class DoubaoAdapter(ModelAdapter):
    """Doubao API适配器"""
    
    def __init__(self):
        # 初始化Doubao客户端
        self.client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=os.environ.get("ARK_API_KEY", "1b4bef68-37d5-4196-ba8b-17c9054ae9c5")
        )
    
    def call_api(self, messages, model_name='doubao-seed-1-6-250615', stream: bool = False):
        """调用Doubao API
        
        Args:
            messages (list): 对话消息列表（system/user/assistant）
            model_name (str): 模型名称或端点ID
            stream (bool): 是否以流式方式返回（默认False）
        
        Returns:
            若 stream=False，返回标准 Completion 响应对象；
            若 stream=True，返回一个可迭代的流对象（yield 块）。
        """
        # 转换消息格式以适配Doubao API
        formatted_messages = self._format_messages_for_doubao(messages)
        
        if stream:
            return self.client.chat.completions.create(
                model=model_name,
                messages=formatted_messages,
                thinking={"type": "disabled"},
                stream=True
            )
        else:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=formatted_messages,
                thinking={"type": "disabled"}
            )
            return response
    
    def format_response(self, response):
        """格式化Doubao响应"""
        try:
            content = response.choices[0].message.content
            return {
                'success': True,
                'content': content,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'content': None,
                'error': f"API错误: {str(e)}"
            }
    
    def _format_messages_for_doubao(self, messages):
        """将消息格式转换为Doubao API格式"""
        formatted = []
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            # 转换角色名称
            if role == Role.SYSTEM or role == 'system':
                formatted.append({"role": "system", "content": content})
            elif role == Role.USER or role == 'user':
                formatted.append({"role": "user", "content": content})
            elif role == Role.ASSISTANT or role == 'assistant':
                formatted.append({"role": "assistant", "content": content})
        
        return formatted

# 模型管理器
class ModelManager:
    """模型管理器，负责模型切换和调用"""
    
    def __init__(self, default_provider='dashscope'):
        self.adapters = {
            'dashscope': DashScopeAdapter(),
            'doubao': DoubaoAdapter()
        }
        self.current_provider = default_provider
        self.model_configs = {
            'dashscope': 'qwen-max-latest',
            'doubao': 'doubao-seed-1-6-250615'
        }
    
    def set_provider(self, provider):
        """设置当前使用的模型提供商"""
        if provider in self.adapters:
            self.current_provider = provider
        else:
            raise ValueError(f"不支持的模型提供商: {provider}")
    
    def get_available_providers(self):
        """获取可用的模型提供商列表"""
        return list(self.adapters.keys())
    
    def call_model(self, messages):
        """调用当前选择的模型"""
        adapter = self.adapters[self.current_provider]
        model_name = self.model_configs[self.current_provider]
        
        try:
            response = adapter.call_api(messages, model_name)
            return adapter.format_response(response)
        except Exception as e:
            return {
                'success': False,
                'content': None,
                'error': f"模型调用失败: {str(e)}"
            }

# 全局模型管理器实例
model_manager = ModelManager()

# 保持向后兼容的模型名称
lawyer_model = 'qwen-max-latest'

# 模型切换和管理的便捷函数
def set_model_provider(provider):
    """设置当前使用的模型提供商
    
    Args:
        provider (str): 模型提供商名称 ('dashscope' 或 'doubao')
    
    Returns:
        bool: 设置是否成功
    """
    try:
        model_manager.set_provider(provider)
        print(f"已切换到模型提供商: {provider}")
        return True
    except ValueError as e:
        print(f"切换失败: {str(e)}")
        return False

def get_current_provider():
    """获取当前使用的模型提供商
    
    Returns:
        str: 当前模型提供商名称
    """
    return model_manager.current_provider

def get_available_providers():
    """获取所有可用的模型提供商
    
    Returns:
        list: 可用的模型提供商列表
    """
    return model_manager.get_available_providers()

def get_model_info():
    """获取当前模型配置信息
    
    Returns:
        dict: 包含当前提供商和模型名称的信息
    """
    current_provider = model_manager.current_provider
    current_model = model_manager.model_configs[current_provider]
    return {
        'provider': current_provider,
        'model': current_model,
        'available_providers': model_manager.get_available_providers()
    }

def update_model_config(provider, model_name):
    """更新指定提供商的模型配置
    
    Args:
        provider (str): 模型提供商名称
        model_name (str): 新的模型名称
    
    Returns:
        bool: 更新是否成功
    """
    if provider in model_manager.model_configs:
        model_manager.model_configs[provider] = model_name
        print(f"已更新 {provider} 的模型配置为: {model_name}")
        return True
    else:
        print(f"不支持的模型提供商: {provider}")
        return False

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

def chat_with_lawyer(message, conversation_history=None, model_provider=None):
    """与律师AI进行对话
    
    Args:
        message (str): 用户输入的消息
        conversation_history (list, optional): 对话历史，如果为None则创建新对话
        model_provider (str, optional): 指定使用的模型提供商，如果为None则使用当前设置
    
    Returns:
        tuple: (回复内容, 更新后的对话历史, 是否对话结束)
    """
    if conversation_history is None:
        conversation_history = create_new_conversation()
    
    # 添加用户输入到历史
    conversation_history.append({'role': Role.USER, 'content': message})
    
    # 如果指定了模型提供商，临时切换
    original_provider = None
    if model_provider and model_provider != model_manager.current_provider:
        original_provider = model_manager.current_provider
        try:
            model_manager.set_provider(model_provider)
        except ValueError as e:
            return f"模型切换失败: {str(e)}", conversation_history, False
    
    try:
        # 使用模型管理器调用API
        api_response = model_manager.call_model(conversation_history)
        
        # 恢复原始模型提供商
        if original_provider:
            model_manager.set_provider(original_provider)
        
        if api_response['success']:
            lawyer_response = api_response['content']
            
            # 文本完整性检查和调试日志
            if not lawyer_response or not lawyer_response.strip():
                print(f"警告: API返回空响应")
                return "抱歉，系统暂时无法回复，请稍后重试。", conversation_history, False
            
            # 检查文本长度变化（调试用）
            original_length = len(lawyer_response)
            cleaned_response = lawyer_response.strip()
            if len(cleaned_response) != original_length:
                print(f"调试: 文本长度从 {original_length} 变为 {len(cleaned_response)}")
            
            # 确保文本编码正确
            try:
                # 验证文本可以正确编码和解码
                test_encode = cleaned_response.encode('utf-8').decode('utf-8')
                if test_encode != cleaned_response:
                    print(f"警告: 文本编码可能有问题")
            except UnicodeError as e:
                print(f"警告: 文本编码错误: {e}")
            
            conversation_history.append({'role': Role.ASSISTANT, 'content': cleaned_response})
            
            # 检查是否结束对话
            conversation_ended = "？" not in cleaned_response and "?" not in cleaned_response
            
            if conversation_ended:
                # 保存对话为ShareGPT格式
                save_conversation_to_json(conversation_history)
                return cleaned_response + "\n\n对话已结束，并保存为JSON文件。", conversation_history, True
            
            return cleaned_response, conversation_history, False
        else:
            return api_response['error'], conversation_history, False
            
    except Exception as e:
        # 恢复原始模型提供商
        if original_provider:
            model_manager.set_provider(original_provider)
        return f"系统错误: {str(e)}", conversation_history, False

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
    print("律师AI对话系统 - 多模型版本")
    print("="*50)
    print(f"当前模型提供商: {get_current_provider()}")
    print(f"可用提供商: {', '.join(get_available_providers())}")
    print("="*50)
    print("命令说明:")
    print("  'exit' - 退出程序")
    print("  'switch <provider>' - 切换模型提供商 (如: switch doubao)")
    print("  'info' - 查看当前模型信息")
    print("  'providers' - 查看可用的模型提供商")
    print("="*50)
    
    conversation_history = None
    
    while True:
        user_input = input("\n您: ")
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'info':
            info = get_model_info()
            print(f"当前提供商: {info['provider']}")
            print(f"当前模型: {info['model']}")
            print(f"可用提供商: {', '.join(info['available_providers'])}")
            continue
        elif user_input.lower() == 'providers':
            providers = get_available_providers()
            print(f"可用的模型提供商: {', '.join(providers)}")
            continue
        elif user_input.lower().startswith('switch '):
            provider = user_input[7:].strip()
            if set_model_provider(provider):
                # 重置对话历史，因为切换了模型
                conversation_history = None
            continue
            
        response, conversation_history, ended = chat_with_lawyer(user_input, conversation_history)
        print(f"律师: {response}")
        
        if ended:
            conversation_history = None  # 重置对话历史


if __name__ == "__main__":
    main()