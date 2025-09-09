import json
from datetime import datetime
from openai import OpenAI
from typing import Dict

class CaseAnalysisGenerator:
    def __init__(self, model: str = "deepseek-r1"):
        """
        初始化案例分析生成器
        
        Args:
            model: 使用的模型名称
        """
        # 使用单个API Key
        self.api_key = "sk-01005e75de5a46e996bbb973ff587e13"
        
        # 创建单个客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        self.model = model
    
    def load_single_json_file(self, json_file_path: str) -> Dict:
        """
        加载单个JSON文件
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            对话内容字典
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError as e:
            print(f"读取文件 {json_file_path} 时出错: {e}")
            return {}
        except Exception as e:
            print(f"加载文件 {json_file_path} 时出错: {e}")
            return {}
    
    def extract_conversation_content(self, conversation_data: Dict) -> str:
        """
        从对话数据中提取对话内容
        
        Args:
            conversation_data: 对话数据字典
            
        Returns:
            格式化的对话内容字符串
        """
        if not conversation_data or 'conversations' not in conversation_data[0]:
            return ""
        
        conversation_text = ""
        for conv in conversation_data[0]['conversations']:
            role = "用户" if conv['from'] == 'human' else "律师"
            content = conv['value']
            conversation_text += f"{role}: {content}\n\n"
        
        return conversation_text.strip()
    
    def generate_case_analysis(self, conversation_content: str) -> str:
        """
        使用AI生成案例分析
        
        Args:
            conversation_content: 对话内容
            
        Returns:
            生成的案例分析
        """
        prompt = f"""
当前时间为{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
你是一位资深的劳动法律师。你的任务是根据下方提供的"对话内容"，直接为你的当事人撰写一份专业的法律分析与后续行动建议。

**核心要求 - 语气与称谓（请务必遵守）：**
请全程使用第二人称"您"来称呼当事人，以律师直接对客户提供咨询和建议的口吻进行撰写。在分析内容中，请将"李某"或类似的第三方称谓替换为"您"。

**格式与结构要求（请严格遵守）：**
1.  **纯文本输出**：全文不得包含任何Markdown标记或特殊格式化符号，严禁使用星号（*）、井号（#）、竖线（|）、破折号（-）等。所有内容均以标准段落和文本呈现。
2.  **三段式结构**：报告必须严格按照以下三个部分展开，每个部分作为一个独立的自然段，段落之间用一个空行隔开。
3.  **固定标题**：请在每个部分的开头使用固定的中文全角方括号标题，即【案情分析】、【当前应对方案】和【维权与赔偿方案】。
4.  **字数控制**：总字数请控制在1000字以内。

请严格按照以下框架填充内容：

**【案情分析】**
（在此处结合法律法条，向您的当事人分析案件的基本事实、争议焦点，并阐述各方的权利义务关系。）

**【当前应对方案】**
（在此处基于现有情况，向您的当事人提出具体的应对策略，分析可能的风险和机会，并提供可操作的建议。）

**【维权与赔偿方案】**
（在此处向您的当事人详细阐述维权路径和步骤，说明可能获得的赔偿项目和金额计算方式，并给出证据收集与保全的建议。）

---
**对话内容：**
{conversation_content}
---
"""
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'user', 'content': prompt}
                ]
            )
            
            # 通过reasoning_content字段打印思考过程（如果有的话）
            # if hasattr(completion.choices[0].message, 'reasoning_content') and completion.choices[0].message.reasoning_content:
            #     print("思考过程：")
            #     print(completion.choices[0].message.reasoning_content)
            #     print("最终答案：")
            #     print(completion.choices[0].message.content)
            
            # 通过content字段获取最终答案
            return completion.choices[0].message.content
        
        except Exception as e:
            print(f"生成案例分析时出错: {e}")
            return "生成分析失败"
    
    def analyze_conversation(self, json_file_path: str) -> str:
        """
        分析单个对话文件并生成案例分析
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            生成的案例分析
        """
        print(f"正在分析对话文件: {json_file_path}")
        
        try:
            # 加载JSON文件
            conversation_data = self.load_single_json_file(json_file_path)
            if not conversation_data:
                print("JSON文件加载失败")
                return "文件加载失败"
            
            # 提取对话内容
            conversation_content = self.extract_conversation_content(conversation_data)
            if not conversation_content:
                print("对话内容为空")
                return "对话内容为空"
            
            # 生成案例分析
            analysis = self.generate_case_analysis(conversation_content)
            
            print("案例分析生成完成")
            return analysis
            
        except Exception as e:
            print(f"分析对话时出错: {e}")
            return "分析失败"


def main():
    """
    主函数
    """
    # 配置参数
    MODEL = "deepseek-r1"  # 请根据实际情况调整
    
    # 对话历史文件路径
    CONVERSATION_FILE = "conversation_history_demo.json"
    
    # 创建生成器实例
    generator = CaseAnalysisGenerator(
        model=MODEL
    )
    
    # 分析单个对话文件
    analysis_result = generator.analyze_conversation(CONVERSATION_FILE)
    
    print("\n=== 案例分析结果 ===")
    print(analysis_result)


if __name__ == "__main__":
    main()