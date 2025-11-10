#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI劳动法律师举证分析功能 - 主程序入口

实现六阶段多轮对话流程：
1. 案件信息收集阶段
2. 证据需求生成阶段
3. 证据收集指导阶段
4. 证据清单收集阶段
5. 证据分析评估阶段
6. 证据分析对话阶段
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# 添加modules目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

try:
    from case_parser import CaseParser
    from evidence_generator import EvidenceGenerator
    from chat_handler import ChatHandler
    from evidence_analyzer import EvidenceAnalyzer
    from report_generator import ReportGenerator
except ImportError as e:
    print(f"模块导入失败: {e}")
    print("请确保所有模块文件都已正确创建")
    sys.exit(1)


class EvidenceAnalysisSystem:
    """AI劳动法律师举证分析系统主类"""
    
    def __init__(self):
        """初始化系统"""
        self.case_id = None
        self.case_info = None
        self.evidence_list = None
        self.chat_history = []
        self.analysis_results = []
        self.user_evidence_inventory = []  # 用户持有的证据清单
        self.sharegpt_data = {"conversations": []}  # 存储ShareGPT格式的对话数据
        self.system_prompt_added = False  # 标记系统提示词是否已添加
        
        # 初始化各功能模块
        self.case_parser = CaseParser()
        self.evidence_generator = EvidenceGenerator()
        self.chat_handler = ChatHandler()
        self.evidence_analyzer = EvidenceAnalyzer()
        self.report_generator = ReportGenerator()
        
        # 确保必要目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = ['data', 'uploads', 'reports', 'modules']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _print_stage_header(self, stage_num: int, stage_name: str):
        """打印阶段标题"""
        print("\n" + "="*60)
        print(f"阶段 {stage_num}: {stage_name}")
        print("="*60)
    
    def _print_separator(self):
        """打印分隔线"""
        print("-" * 60)
    
    def _generate_case_context(self) -> str:
        """生成案件背景信息用于Alpaca格式"""
        if not self.case_info:
            return "案件信息未知"
        
        basic_info = self.case_info.get('basic_info', {})
        dispute_info = self.case_info.get('dispute_info', {})
        
        context = f"""案件背景：
- 当事人：{basic_info.get('employee_name', '未知')}
- 公司名称：{basic_info.get('company_name', '未知')}
- 争议类型：{dispute_info.get('type', '未知')}
- 月薪：{basic_info.get('monthly_salary', '未知')}元
- 入职日期：{basic_info.get('hire_date', '未知')}
- 解除日期：{basic_info.get('termination_date', '未知')}
- 解除理由：{dispute_info.get('reason_given', '未知')}"""
        
        return context
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词
        
        Returns:
            系统提示词内容
        """
        if not self.case_info or not self.evidence_list:
            return "你是一位专业的劳动法律师，正在为当事人提供法律咨询服务。"
        
        # 提取案件关键信息
        company_name = self.case_info.get('basic_info', {}).get('company_name', '某公司')
        dispute_type = self.case_info.get('dispute_info', {}).get('type', '劳动争议')
        monthly_salary = self.case_info.get('basic_info', {}).get('monthly_salary', '未知')
        
        # 提取证据清单摘要
        evidence_items = self.evidence_list.get('evidence_items', [])
        core_evidence = [item['type'] for item in evidence_items if item.get('importance') == '核心']
        
        prompt = f"""你是一位专业的劳动法律师，正在为当事人提供法律咨询服务。

【案件背景】
- 争议对象：{company_name}
- 争议类型：{dispute_type}
- 月薪水平：{monthly_salary}元
- 核心证据：{', '.join(core_evidence) if core_evidence else '待收集'}

【咨询原则】
1. 提供专业、准确的法律建议
2. 结合具体案件情况给出针对性指导
3. 重点关注证据收集和维权策略
4. 语言通俗易懂，避免过多法律术语
5. 给出具体可操作的建议

【回复要求】
- 直接回答用户问题，不要重复问题
- 结合案件实际情况
- 提供具体的操作建议
- 如涉及法律条文，简要说明
- 控制回复长度在200字以内

请基于以上信息回答用户的法律咨询问题。"""
        
        return prompt
    
    def _save_sharegpt_data_entry(self, user_message: str, ai_reply: str, stage: str = ""):
        """保存单条ShareGPT格式的对话数据
        
        Args:
            user_message: 用户消息
            ai_reply: AI回复
            stage: 当前阶段名称
        """
        try:
            # 如果是第一次保存对话且系统提示词还未添加，先添加系统提示词
            if not self.system_prompt_added and self.case_info and self.evidence_list:
                system_prompt = self._get_system_prompt()
                self.sharegpt_data["conversations"].append({
                    "from": "system",
                    "value": system_prompt
                })
                self.system_prompt_added = True
            
            # 添加用户消息
            self.sharegpt_data["conversations"].append({
                "from": "human",
                "value": user_message
            })
            
            # 添加AI回复
            self.sharegpt_data["conversations"].append({
                "from": "gpt", 
                "value": ai_reply
            })
            
        except Exception as e:
            print(f"保存ShareGPT数据失败: {e}")
    
    def _save_sharegpt_data_to_file(self):
        """将ShareGPT数据保存到文件"""
        if not self.case_id or not self.sharegpt_data["conversations"]:
            return
        
        try:
            sharegpt_file_path = os.path.join('data', f'{self.case_id}_sharegpt_data.json')
            with open(sharegpt_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.sharegpt_data, f, ensure_ascii=False, indent=2)
            
            print(f"ShareGPT格式对话数据已保存到: {sharegpt_file_path}")
            
        except Exception as e:
            print(f"保存ShareGPT数据文件失败: {e}")
    
    def stage1_case_info_collection(self) -> bool:
        """阶段一：案件信息收集"""
        self._print_stage_header(1, "案件信息收集")
        
        try:
            # 读取并解析conversation.json文件
            conversation_path = os.path.join('data', 'conversation.json')
            if not os.path.exists(conversation_path):
                print(f"错误：找不到对话记录文件 {conversation_path}")
                return False
            
            print("正在解析对话记录文件...")
            self.case_info = self.case_parser.parse_conversation_file(conversation_path)
            
            if not self.case_info:
                print("错误：无法解析案件信息")
                return False
            
            # 生成案件ID
            self.case_id = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            self.case_info['case_id'] = self.case_id
            
            # 显示提取的案件信息
            print("\n案件信息提取完成：")
            print(f"案件ID: {self.case_id}")
            print(f"当事人: {self.case_info.get('basic_info', {}).get('employee_name', '未知')}")
            print(f"公司名称: {self.case_info.get('basic_info', {}).get('company_name', '未知')}")
            print(f"争议类型: {self.case_info.get('dispute_info', {}).get('type', '未知')}")
            print(f"月薪: {self.case_info.get('basic_info', {}).get('monthly_salary', '未知')}元")
            
            # 保存案件信息
            case_info_path = os.path.join('data', f'{self.case_id}_case_info.json')
            with open(case_info_path, 'w', encoding='utf-8') as f:
                json.dump(self.case_info, f, ensure_ascii=False, indent=2)
            
            print(f"\n案件信息已保存到: {case_info_path}")
            return True
            
        except Exception as e:
            print(f"案件信息收集失败: {e}")
            return False
    
    def stage2_evidence_list_generation(self) -> bool:
        """阶段二：证据需求生成"""
        self._print_stage_header(2, "证据需求生成")
        
        try:
            print("正在调用Qwen-MAX分析案件，生成证据清单...")
            
            # 生成案件摘要
            case_summary = self.case_parser.generate_case_summary(self.case_info)
            print(f"\n案件摘要:\n{case_summary}")
            
            # 调用Qwen-MAX生成证据清单
            self.evidence_list = self.evidence_generator.generate_evidence_list(
                case_summary, self.case_info
            )
            
            if not self.evidence_list:
                print("错误：无法生成证据清单")
                return False
            
            # 显示生成的证据清单
            print("\n证据清单生成完成：")
            self._print_separator()
            
            for i, evidence in enumerate(self.evidence_list.get('evidence_items', []), 1):
                print(f"{i}. {evidence.get('type', '未知类型')} ({evidence.get('importance', '未知重要性')})")
                print(f"   描述: {evidence.get('description', '无描述')}")
                print(f"   收集方法: {evidence.get('collection_method', '无方法')}")
                print(f"   法律依据: {evidence.get('legal_basis', '无依据')}")
                print()
            
            # 保存证据清单
            evidence_list_path = os.path.join('data', f'{self.case_id}_evidence_list.json')
            with open(evidence_list_path, 'w', encoding='utf-8') as f:
                json.dump(self.evidence_list, f, ensure_ascii=False, indent=2)
            
            print(f"证据清单已保存到: {evidence_list_path}")
            return True
            
        except Exception as e:
            print(f"证据清单生成失败: {e}")
            return False
    
    def stage3_evidence_collection_guidance(self) -> bool:
        """阶段三：证据收集指导"""
        self._print_stage_header(3, "证据收集指导")
        
        print("欢迎进入证据收集指导阶段！")
        print("您可以根据上述证据清单询问您疑惑的地方，我将为您进行解答，如果没有问题，请回答'没有'，我们将跳转到证据清单收集阶段。")
        print("输入 'quit' 退出系统。")
        
        try:
            while True:
                self._print_separator()
                user_input = input("\n请输入您的问题: ").strip()
                
                if user_input.lower() in ['没有', '无', 'no']:
                    print("进入证据清单收集阶段...")
                    break
                elif user_input.lower() == 'quit':
                    print("感谢使用AI劳动法律师举证分析系统！")
                    return False
                elif not user_input:
                    print("请输入有效的问题。")
                    continue
                
                # 调用对话处理模块
                response = self.chat_handler.handle_chat(
                    user_input, self.case_info, self.evidence_list, self.chat_history
                )
                
                if response:
                    ai_reply = response.get('reply', '抱歉，无法生成回复')
                    print(f"\nAI律师回复:\n{ai_reply}")
                    

                    
                    # 保存对话历史
                    self.chat_history.append({
                        'role': 'user',
                        'content': user_input,
                        'timestamp': datetime.now().isoformat()
                    })
                    self.chat_history.append({
                        'role': 'assistant',
                        'content': ai_reply,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # 保存ShareGPT格式数据
                    self._save_sharegpt_data_entry(user_input, ai_reply, "证据收集指导")
                    
                    # 询问是否还有其他问题
                    print("\n是否还有其它问题？如果没有其它问题，我们将跳转到证据清单收集阶段。如果没有问题，请回答'没有'。")
                    
                else:
                    print("抱歉，无法处理您的问题，请重新输入。")
            
            return True
            
        except KeyboardInterrupt:
            print("\n用户中断操作")
            return False
        except Exception as e:
            print(f"证据收集指导失败: {e}")
            return False
    
    def stage4_evidence_inventory(self) -> bool:
        """阶段四：证据清单收集"""
        self._print_stage_header(4, "证据清单收集")
        
        print("欢迎进入证据清单收集阶段！")
        print("我是您的AI律师，现在需要了解您目前持有的证据情况。")
        
        # 证据类型名称映射
        evidence_type_names = {
            'contract': '劳动合同', 'payslip': '工资单', 'attendance': '考勤记录',
            'injury': '工伤鉴定', 'recording': '录音', 'chat': '聊天记录', 'other': '其他'
        }
        
        try:
            while True:
                self._print_separator()
                print("\n请告诉我您目前手上持有哪些证据？")
                # print("例如：我目前手上有劳动合同，解除劳动合同通知书，银行流水")
                print("输入 'quit' 退出系统。")
                
                user_input = input("\n您的回答: ").strip()
                
                if user_input.lower() == 'quit':
                    print("感谢使用AI劳动法律师举证分析系统！")
                    return False
                elif not user_input:
                    print("请输入您持有的证据信息。")
                    continue
                
                # 使用LLM解析用户回答
                print("\n正在分析您的证据清单...")
                parsed_evidence = self._parse_evidence_with_llm(user_input)
                
                if not parsed_evidence:
                    print("抱歉，无法解析您的证据信息，请重新描述。")
                    continue
                
                # 显示解析结果
                print("\n根据您的描述，我为您整理了以下证据清单：")
                self._print_separator()
                for i, evidence in enumerate(parsed_evidence, 1):
                    type_name = evidence_type_names.get(evidence['type'], evidence['type'])
                    print(f"{i}. {evidence['name']} ({type_name})")
                    if evidence.get('description'):
                        print(f"   描述: {evidence['description']}")
                
                # 询问用户确认
                self._print_separator()
                confirm = input("\n以上证据清单是否正确？(是/否/重新输入): ").strip().lower()
                
                if confirm in ['y', 'yes', '是', '正确']:
                    self.user_evidence_inventory = parsed_evidence
                    print("\n证据清单确认完成！进入证据分析评估阶段...")
                    break
                elif confirm in ['n', 'no', '否', '不正确']:
                    print("\n请重新描述您的证据：")
                    continue
                else:
                    print("\n请重新描述您的证据：")
                    continue
            
            # 保存证据清单到文件
            if self.case_id and self.user_evidence_inventory:
                try:
                    inventory_path = os.path.join('data', f'{self.case_id}_evidence_inventory.json')
                    with open(inventory_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            'case_id': self.case_id,
                            'inventory': self.user_evidence_inventory,
                            'created_time': datetime.now().isoformat()
                        }, f, ensure_ascii=False, indent=2)
                    print(f"\n证据清单已保存到: {inventory_path}")
                except Exception as e:
                    print(f"保存证据清单失败: {e}")
            
            return True
            
        except KeyboardInterrupt:
            print("\n用户中断操作")
            return False
        except Exception as e:
            print(f"证据清单收集失败: {e}")
            return False
    
    def _parse_evidence_with_llm(self, user_input: str) -> list:
        """使用LLM解析用户的证据描述"""
        try:
            from openai import OpenAI
            import os
            import json
            
            # 初始化OpenAI客户端（使用Qwen API）
            client = OpenAI(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            
            # 构建prompt
            prompt = f"""你是一个专业的法律助手，需要将用户描述的证据转换为结构化的JSON格式。

用户描述：{user_input}

请将用户提到的每个证据解析为JSON格式，包含以下字段：
- name: 证据名称
- type: 证据类型，必须是以下之一：contract(劳动合同), payslip(工资单), attendance(考勤记录), injury(工伤鉴定), recording(录音), chat(聊天记录), other(其他)
- description: 简要描述
- added_time: 当前时间戳

请根据证据名称智能推断类型：
- 劳动合同、合同 -> contract
- 工资单、工资条、银行流水、工资流水 -> payslip  
- 考勤记录、打卡记录 -> attendance
- 工伤鉴定、伤残鉴定 -> injury
- 录音、通话录音 -> recording
- 聊天记录、微信记录、QQ记录 -> chat
- 其他无法分类的 -> other

只返回JSON数组格式，不要其他解释：
[{{"name": "证据名称", "type": "证据类型", "description": "描述", "added_time": "{datetime.now().isoformat()}"}}]"""
            
            # 调用LLM
            completion = client.chat.completions.create(
                model="qwen-max-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的法律助手，擅长解析和整理证据信息。"},
                    {"role": "user", "content": prompt}
                ],
                extra_body={"enable_thinking": False},
            )
            
            # 解析LLM响应
            response_content = completion.choices[0].message.content.strip()
            
            # 尝试解析JSON
            try:
                # 清理响应内容，移除可能的markdown标记
                if response_content.startswith('```json'):
                    response_content = response_content[7:]
                if response_content.endswith('```'):
                    response_content = response_content[:-3]
                response_content = response_content.strip()
                
                parsed_data = json.loads(response_content)
                
                # 验证数据格式
                if isinstance(parsed_data, list):
                    valid_evidence = []
                    for item in parsed_data:
                        if isinstance(item, dict) and 'name' in item and 'type' in item:
                            # 确保时间戳正确
                            item['added_time'] = datetime.now().isoformat()
                            valid_evidence.append(item)
                    return valid_evidence
                else:
                    return []
                    
            except json.JSONDecodeError:
                print(f"LLM响应解析失败: {response_content}")
                return []
                
        except Exception as e:
            print(f"LLM解析失败: {e}")
            return []
    
    def stage5_evidence_analysis(self) -> bool:
        """阶段五：证据分析评估"""
        self._print_stage_header(5, "证据分析评估")
        
        print("欢迎进入证据分析阶段！")
        print("我将根据您在阶段4中提供的证据清单，引导您逐一上传和分析证据。")
        
        # 检查是否有证据清单
        if not hasattr(self, 'user_evidence_inventory') or not self.user_evidence_inventory:
            print("\n未找到证据清单，请先返回阶段4收集证据信息。")
            print("输入 'back' 返回阶段4，输入 'quit' 退出系统。")
            
            while True:
                user_input = input("\n请选择操作: ").strip().lower()
                if user_input == 'back':
                    return self.stage4_evidence_inventory()
                elif user_input == 'quit':
                    print("感谢使用AI劳动法律师举证分析系统！")
                    return False
                else:
                    print("请输入 'back' 或 'quit'。")
        
        # 显示证据清单概览
        print(f"\n您的证据清单共有 {len(self.user_evidence_inventory)} 项证据：")
        self._print_separator()
        for i, evidence in enumerate(self.user_evidence_inventory, 1):
            print(f"{i}. {evidence['name']} ({evidence['type']})")
            if evidence.get('description'):
                print(f"   描述: {evidence['description']}")
        self._print_separator()
        
        try:
            current_index = 0
            total_evidence = len(self.user_evidence_inventory)
            
            while current_index < total_evidence:
                current_evidence = self.user_evidence_inventory[current_index]
                
                print(f"\n正在处理第 {current_index + 1}/{total_evidence} 个证据：")
                print(f"证据名称: {current_evidence['name']}")
                print(f"证据类型: {current_evidence['type']}")
                if current_evidence.get('description'):
                    print(f"证据描述: {current_evidence['description']}")
                
                print(f"\n请将 '{current_evidence['name']}' 文件放入 'uploads' 目录中。")
                print("操作选项:")
                print("- 输入文件名：上传并分析该证据")
                print("- 'skip'：跳过当前证据")
                print("- 'list'：查看uploads目录中的文件")
                print("- 'progress'：查看分析进度")
                print("- 'quit'：退出系统")
                
                self._print_separator()
                user_input = input("\n请输入操作: ").strip()
                
                if user_input.lower() == 'skip':
                    print(f"已跳过证据: {current_evidence['name']}")
                    current_index += 1
                    continue
                elif user_input.lower() == 'quit':
                    print("感谢使用AI劳动法律师举证分析系统！")
                    return False
                elif user_input.lower() == 'list':
                    # 列出uploads目录中的文件
                    uploads_dir = 'uploads'
                    if os.path.exists(uploads_dir):
                        files = os.listdir(uploads_dir)
                        if files:
                            print("\nuploads目录中的文件:")
                            for i, file in enumerate(files, 1):
                                print(f"{i}. {file}")
                        else:
                            print("uploads目录为空，请先上传证据文件。")
                    else:
                        print("uploads目录不存在。")
                    continue
                elif user_input.lower() == 'progress':
                    # 显示分析进度
                    print(f"\n分析进度: {len(self.analysis_results)}/{total_evidence}")
                    if self.analysis_results:
                        print("已完成分析的证据:")
                        for result in self.analysis_results:
                            print(f"- {result['file_name']} ({result['evidence_type']})")
                    
                    remaining = total_evidence - current_index
                    if remaining > 0:
                        print(f"\n剩余待处理证据 {remaining} 项:")
                        for i in range(current_index, total_evidence):
                            evidence = self.user_evidence_inventory[i]
                            print(f"- {evidence['name']} ({evidence['type']})")
                    continue
                elif not user_input:
                    print("请输入有效的操作。")
                    continue
                
                # 分析指定的文件
                file_path = os.path.join('uploads', user_input)
                if not os.path.exists(file_path):
                    print(f"文件不存在: {file_path}")
                    print("请确保文件已放入uploads目录中，并检查文件名是否正确。")
                    continue
                
                # 直接使用证据清单中的类型（已经是英文代码）
                evidence_type = current_evidence['type']
                
                # 验证类型是否支持
                supported_types = ['contract', 'payslip', 'attendance', 'injury', 'recording', 'chat']
                if evidence_type not in supported_types:
                    if evidence_type == 'other':
                        print(f"\n警告：'{current_evidence['name']}' 的类型为'其他'，分析器可能无法准确分析。")
                        print("建议手动指定更具体的证据类型。")
                        print("是否跳过该证据？(y/n): ", end="")
                        skip_choice = input().strip().lower()
                        if skip_choice in ['y', 'yes', '是']:
                            current_index += 1
                            continue
                    else:
                        print(f"\n错误：不支持的证据类型 '{evidence_type}'")
                        print(f"支持的类型: {supported_types}")
                        print("请跳过该证据或联系管理员更新类型支持。")
                        current_index += 1
                        continue
                
                print(f"\n正在分析文件: {user_input} (类型: {evidence_type})...")
                
                # 调用证据分析模块
                analysis_result = self.evidence_analyzer.analyze_evidence(
                    file_path, evidence_type
                )
                
                if analysis_result:
                    print("\n分析结果:")
                    self._print_separator()
                    
                    # 显示分析结果
                    for key, value in analysis_result.items():
                        if key != 'recommendations':
                            print(f"{key}: {value}")
                    
                    # 显示建议
                    recommendations = analysis_result.get('recommendations', [])
                    if recommendations:
                        print("\n改进建议:")
                        for i, rec in enumerate(recommendations, 1):
                            print(f"{i}. {rec}")
                    
                    # 保存分析结果
                    result_record = {
                        'file_name': user_input,
                        'evidence_type': evidence_type,
                        'analysis_time': datetime.now().isoformat(),
                        'analysis_result': analysis_result,
                        'original_evidence_info': current_evidence  # 保存原始证据信息
                    }
                    self.analysis_results.append(result_record)
                    
                    print("\n分析结果已保存。")
                    current_index += 1
                    
                    # 显示进度
                    remaining = total_evidence - current_index
                    if remaining > 0:
                        print(f"\n还有 {remaining} 个证据待处理。")
                    else:
                        print("\n所有证据分析完成！")
                        
                else:
                    print("分析失败，请检查文件格式或网络连接。")
                    print("您可以重试或选择跳过该证据。")
            
            # 所有证据处理完成
            print("\n证据分析阶段完成！")
            print(f"共分析了 {len(self.analysis_results)} 个证据文件。")
            print("\n进入证据分析对话阶段...")
            return True
            
        except KeyboardInterrupt:
            print("\n用户中断操作")
            return False
        except Exception as e:
            print(f"证据分析失败: {e}")
            return False
    
    def stage6_evidence_analysis_chat(self) -> bool:
        """阶段六：证据分析对话"""
        self._print_stage_header(6, "证据分析对话")
        
        print("欢迎进入证据分析对话阶段！")
        print("您可以根据已分析的证据询问您疑惑的地方，我将为您进行解答，如果没有问题，请回答'没有'，我们将跳转到交互收尾阶段。")
        
        # 显示已分析的证据摘要
        if self.analysis_results:
            print("\n已分析的证据：")
            self._print_separator()
            for i, result in enumerate(self.analysis_results, 1):
                analysis = result.get('analysis_result', {})
                raw_result = analysis.get('raw_result', {})
                
                # 获取文件类型，优先从raw_result获取
                file_type = raw_result.get('文件类型') or analysis.get('file_type', '未知')
                
                # 获取有效性，优先从raw_result获取，处理布尔值转换
                validity = raw_result.get('是否可以作为核心证据') or analysis.get('is_valid_evidence')
                if validity is True:
                    validity = '是'
                elif validity is False:
                    validity = '否'
                elif validity is None:
                    validity = '未知'
                
                print(f"{i}. {result.get('file_name', '未知文件')} ({result.get('evidence_type', '未知类型')})")
                print(f"   文件类型: {file_type}")
                print(f"   有效性: {validity}")
                print()
        else:
            print("\n暂无已分析的证据。建议先返回阶段5进行证据分析。")
        

        print("输入 'quit' 退出系统。")
        
        try:
            while True:
                self._print_separator()
                user_input = input("\n请输入您的问题: ").strip()
                
                if user_input.lower() in ['没有', '无', 'no']:
                    # 直接结束流程并生成报告
                    print("\n正在生成完整的证据分析报告...")
                    
                    report_data = {
                        'case_info': self.case_info,
                        'evidence_list': self.evidence_list,
                        'chat_history': self.chat_history,
                        'analysis_results': self.analysis_results
                    }
                    
                    report_path = self.report_generator.generate_report(
                        self.case_id, report_data
                    )
                    
                    if report_path:
                        print(f"\n分析报告已生成: {report_path}")
                    else:
                        print("报告生成失败")
                    
                    print("\n证据分析流程已完成！")
                    print("感谢使用AI劳动法律师举证分析系统！")
                    print("祝您维权顺利！")
                    return True
                elif user_input.lower() == 'next':
                    # 直接结束流程并生成报告
                    print("\n正在生成完整的证据分析报告...")
                    
                    report_data = {
                        'case_info': self.case_info,
                        'evidence_list': self.evidence_list,
                        'chat_history': self.chat_history,
                        'analysis_results': self.analysis_results
                    }
                    
                    report_path = self.report_generator.generate_report(
                        self.case_id, report_data
                    )
                    
                    if report_path:
                        print(f"\n分析报告已生成: {report_path}")
                    else:
                        print("报告生成失败")
                    
                    print("\n证据分析流程已完成！")
                    print("感谢使用AI劳动法律师举证分析系统！")
                    print("祝您维权顺利！")
                    return True
                elif user_input.lower() == 'back':
                    print("返回证据分析评估阶段...")
                    return self.stage5_evidence_analysis()
                elif user_input.lower() == 'quit':
                    print("感谢使用AI劳动法律师举证分析系统！")
                    return False
                elif not user_input:
                    print("请输入有效的问题。")
                    continue
                
                # 构建包含证据分析结果的上下文
                evidence_context = self._build_evidence_context()
                
                # 调用对话处理模块，传入证据分析结果作为上下文
                response = self.chat_handler.handle_evidence_analysis_chat(
                    user_input, self.case_info, self.evidence_list, 
                    self.analysis_results, evidence_context, self.chat_history
                )
                
                if response:
                    ai_reply = response.get('reply', '抱歉，无法生成回复')
                    print(f"\nAI律师回复:\n{ai_reply}")
                    

                    
                    # 保存对话历史
                    self.chat_history.append({
                        'role': 'user',
                        'content': user_input,
                        'timestamp': datetime.now().isoformat(),
                        'stage': 'evidence_analysis_chat'
                    })
                    self.chat_history.append({
                        'role': 'assistant',
                        'content': ai_reply,
                        'timestamp': datetime.now().isoformat(),
                        'stage': 'evidence_analysis_chat'
                    })
                    
                    # 保存ShareGPT格式数据
                    self._save_sharegpt_data_entry(user_input, ai_reply, "证据分析对话")
                    
                else:
                    print("抱歉，无法处理您的问题，请重新输入。")
            
            return True
            
        except KeyboardInterrupt:
            print("\n用户中断操作")
            return False
        except Exception as e:
            print(f"证据分析对话失败: {e}")
            return False
    
    def _build_evidence_context(self) -> str:
        """构建证据分析结果的上下文信息"""
        if not self.analysis_results:
            return "暂无已分析的证据。"
        
        context_parts = ["已分析的证据信息："]
        
        for i, result in enumerate(self.analysis_results, 1):
            analysis = result.get('analysis_result', {})
            context_parts.append(f"\n{i}. 文件：{result.get('file_name', '未知文件')}")
            context_parts.append(f"   类型：{result.get('evidence_type', '未知类型')}")
            context_parts.append(f"   分析时间：{result.get('analysis_time', '未知时间')}")
            
            # 添加关键分析结果
            for key, value in analysis.items():
                if key not in ['recommendations'] and value:
                    context_parts.append(f"   {key}：{value}")
            
            # 添加改进建议
            recommendations = analysis.get('recommendations', [])
            if recommendations:
                context_parts.append("   改进建议：")
                for rec in recommendations:
                    context_parts.append(f"   - {rec}")
        
        return "\n".join(context_parts)
    

    
    def run(self):
        """运行完整的六阶段流程"""
        print("欢迎使用AI劳动法律师举证分析系统！")
        print("本系统将通过六个阶段帮助您完成证据分析：")
        print("1. 案件信息收集")
        print("2. 证据需求生成")
        print("3. 证据收集指导")
        print("4. 证据清单收集")
        print("5. 证据分析评估")
        print("6. 证据分析对话")
        
        try:
            # 阶段一：案件信息收集
            if not self.stage1_case_info_collection():
                print("案件信息收集失败，程序退出。")
                return
            
            # 阶段二：证据需求生成
            if not self.stage2_evidence_list_generation():
                print("证据需求生成失败，程序退出。")
                return
            
            # 阶段三：证据收集指导
            if not self.stage3_evidence_collection_guidance():
                print("程序已退出。")
                return
            
            # 阶段四：证据清单收集
            if not self.stage4_evidence_inventory():
                print("程序已退出。")
                return
            
            # 阶段五：证据分析评估
            if not self.stage5_evidence_analysis():
                print("程序已退出。")
                return
            
            # 阶段六：证据分析对话
            if not self.stage6_evidence_analysis_chat():
                print("程序已退出。")
                return
            
        except KeyboardInterrupt:
            print("\n\n用户中断程序执行")
        except Exception as e:
            print(f"\n程序执行出错: {e}")
        finally:
            # 保存最终的对话历史和分析结果
            if self.case_id:
                try:
                    # 保存对话历史
                    if self.chat_history:
                        chat_history_path = os.path.join('data', f'{self.case_id}_chat_history.json')
                        with open(chat_history_path, 'w', encoding='utf-8') as f:
                            json.dump({
                                'case_id': self.case_id,
                                'messages': self.chat_history
                            }, f, ensure_ascii=False, indent=2)
                    
                    # 保存分析结果
                    if self.analysis_results:
                        analysis_results_path = os.path.join('data', f'{self.case_id}_analysis_results.json')
                        with open(analysis_results_path, 'w', encoding='utf-8') as f:
                            json.dump({
                                'case_id': self.case_id,
                                'results': self.analysis_results
                            }, f, ensure_ascii=False, indent=2)
                    
                    # 保存证据清单
                    if self.user_evidence_inventory:
                        inventory_path = os.path.join('data', f'{self.case_id}_evidence_inventory.json')
                        with open(inventory_path, 'w', encoding='utf-8') as f:
                            json.dump({
                                'case_id': self.case_id,
                                'inventory': self.user_evidence_inventory,
                                'created_time': datetime.now().isoformat()
                            }, f, ensure_ascii=False, indent=2)
                    
                    # 保存ShareGPT格式对话数据
                    self._save_sharegpt_data_to_file()
                    
                    print(f"\n会话数据已保存 (案件ID: {self.case_id})")
                except Exception as e:
                    print(f"保存会话数据失败: {e}")


def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("错误：需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查环境变量
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("警告：未设置DASHSCOPE_API_KEY环境变量")
        print("请设置环境变量后重新运行程序")
        print("例如: set DASHSCOPE_API_KEY=your_api_key")
        # 不直接退出，允许用户在运行时设置
    
    # 创建并运行系统
    system = EvidenceAnalysisSystem()
    system.run()


if __name__ == '__main__':
    main()