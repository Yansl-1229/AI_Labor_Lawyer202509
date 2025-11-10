#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI劳动法律师软件Web版本
将命令行交互改造为网页交互形式
提供HTTP API接口支持前端调用
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from flask import Flask, request, jsonify, render_template, session, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import shutil

# 导入核心模块
try:
    from lawyer_model import set_model_provider, get_current_provider, get_available_providers, get_model_info, update_model_config, chat_with_lawyer, create_new_conversation, save_conversation_to_json, DoubaoAdapter
    from free_generate_case_analysis import CaseAnalysisGenerator
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请确保以下文件存在：")
    print("- lawyer_model.py")
    print("- free_generate_case_analysis.py")
    sys.exit(1)

# 导入举证分析模块
sys.path.append(os.path.join(os.path.dirname(__file__), 'EvidenceAnalysis', 'modules'))
try:
    from case_parser import CaseParser
    from evidence_generator import EvidenceGenerator
    from chat_handler import ChatHandler
    from evidence_analyzer import EvidenceAnalyzer
    from report_generator import ReportGenerator
except ImportError as e:
    print(f"❌ 举证分析模块导入失败: {e}")
    print("请确保EvidenceAnalysis/modules目录下的文件存在")
    # 不退出，允许基础功能继续运行
    CaseParser = None
    EvidenceGenerator = None
    ChatHandler = None
    EvidenceAnalyzer = None
    ReportGenerator = None

class UserType(Enum):
    """用户类型枚举"""
    FREE = "free"        # 免费用户
    PREMIUM = "premium"  # 付费用户

class SessionStatus(Enum):
    """会话状态枚举"""
    COLLECTING = "collecting"    # 信息收集中
    COMPLETED = "completed"      # 信息收集完成
    ANALYZING = "analyzing"      # 分析中
    FINISHED = "finished"        # 全部完成
    SERVICE_SELECTION = "service_selection"  # 服务选择阶段
    # 举证分析阶段
    EVIDENCE_CASE_INFO = "evidence_case_info"          # 阶段1：案件信息收集
    EVIDENCE_LIST_GEN = "evidence_list_generation"     # 阶段2：证据需求生成
    EVIDENCE_GUIDANCE = "evidence_guidance"            # 阶段3：证据收集指导
    EVIDENCE_INVENTORY = "evidence_inventory"          # 阶段4：证据清单收集
    EVIDENCE_ANALYSIS = "evidence_analysis"            # 阶段5：证据分析评估
    EVIDENCE_CHAT = "evidence_chat"                    # 阶段6：证据分析对话

class EvidenceStage(Enum):
    """举证分析阶段枚举"""
    STAGE1_CASE_INFO = 1        # 案件信息收集
    STAGE2_EVIDENCE_LIST = 2    # 证据需求生成
    STAGE3_GUIDANCE = 3         # 证据收集指导
    STAGE4_INVENTORY = 4        # 证据清单收集
    STAGE5_ANALYSIS = 5         # 证据分析评估
    STAGE6_CHAT = 6             # 证据分析对话

class WebAILawyerSystem:
    """
    AI劳动法律师系统Web版本
    支持HTTP API调用，保持原有业务逻辑
    """
    
    def __init__(self, session_id: str = None):
        """初始化系统"""
        self.session_id = session_id or self._generate_session_id()
        self.user_type = UserType.FREE  # 默认免费用户
        self.session_status = SessionStatus.COLLECTING
        self.conversation_history = None
        self.conversation_file_path = None
        self.case_analysis_result = None
        
        # 举证分析相关属性
        self.evidence_mode = False  # 是否启用举证分析模式
        self.current_evidence_stage = None  # 当前举证分析阶段
        self.case_id = None  # 案件ID
        self.case_info = None  # 案件信息
        self.evidence_list = None  # 证据清单
        self.evidence_chat_history = []  # 举证分析对话历史
        self.analysis_results = []  # 证据分析结果
        self.user_evidence_inventory = []  # 用户持有的证据清单
        self.sharegpt_data = {"conversations": []}  # ShareGPT格式对话数据
        self.system_prompt_added = False  # 系统提示词标记
        
        # 初始化各个模块
        self._init_modules()
        
        # 创建会话目录
        self.session_dir = f"sessions/{self.session_id}"
        os.makedirs(self.session_dir, exist_ok=True)
        
        # 创建举证分析相关目录
        self._ensure_evidence_directories()
    
    def _ensure_evidence_directories(self):
        """确保举证分析相关目录存在"""
        directories = [
            os.path.join(self.session_dir, 'evidence_files'),
            os.path.join(self.session_dir, 'uploads'),
            'EvidenceAnalysis/data',
            'EvidenceAnalysis/reports'
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def enable_evidence_analysis_mode(self) -> Dict[str, Any]:
        """启用举证分析模式"""
        if not all([self.case_parser, self.evidence_generator, self.chat_handler, 
                   self.evidence_analyzer, self.report_generator]):
            return {
                "success": False,
                "error": "举证分析模块不可用，请检查模块安装"
            }
        
        self.evidence_mode = True
        self.current_evidence_stage = EvidenceStage.STAGE1_CASE_INFO
        self.session_status = SessionStatus.EVIDENCE_CASE_INFO
        
        return {
            "success": True,
            "message": "✅ 已启用举证分析模式",
            "current_stage": 1,
            "stage_name": "案件信息收集阶段",
            "evidence_mode": True
        }
    
    def _get_evidence_system_prompt(self) -> str:
        """获取举证分析系统提示词"""
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
        """保存单条ShareGPT格式的对话数据"""
        try:
            # 如果是第一次保存对话且系统提示词还未添加，先添加系统提示词
            if not self.system_prompt_added and self.case_info and self.evidence_list:
                system_prompt = self._get_evidence_system_prompt()
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
    
    def evidence_stage1_case_info_collection(self) -> Dict[str, Any]:
        """阶段一：案件信息收集（从对话记录解析）"""
        try:
            if not self.evidence_mode:
                return {
                    "success": False,
                    "error": "请先启用举证分析模式"
                }
            
            if not self.case_parser:
                return {
                    "success": False,
                    "error": "案件解析模块不可用"
                }
            
            # 检查对话记录文件
            if not self.conversation_file_path or not os.path.exists(self.conversation_file_path):
                return {
                    "success": False,
                    "error": "未找到对话记录文件，请先完成信息收集阶段"
                }
            
            # 解析对话记录文件
            print(f"正在解析对话记录文件: {self.conversation_file_path}")
            self.case_info = self.case_parser.parse_conversation_file(self.conversation_file_path)
            
            if not self.case_info:
                print("案件信息解析失败")
                return {
                    "success": False,
                    "error": "无法解析案件信息"
                }
            
            print(f"案件信息解析成功: {self.case_info}")
            
            # 生成案件ID
            self.case_id = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            self.case_info['case_id'] = self.case_id
            
            # 保存案件信息
            case_info_path = os.path.join(self.session_dir, f'{self.case_id}_case_info.json')
            with open(case_info_path, 'w', encoding='utf-8') as f:
                json.dump(self.case_info, f, ensure_ascii=False, indent=2)
            
            # 更新状态
            self.current_evidence_stage = EvidenceStage.STAGE2_EVIDENCE_LIST
            self.session_status = SessionStatus.EVIDENCE_LIST_GEN
            
            # 提取关键信息用于返回
            basic_info = self.case_info.get('basic_info', {})
            dispute_info = self.case_info.get('dispute_info', {})
            
            return {
                "success": True,
                "message": "✅ 案件信息收集完成",
                "case_id": self.case_id,
                "case_info": {
                    "employee_name": basic_info.get('employee_name', '未知'),
                    "company_name": basic_info.get('company_name', '未知'),
                    "dispute_type": dispute_info.get('type', '未知'),
                    "monthly_salary": basic_info.get('monthly_salary', '未知'),
                    "hire_date": basic_info.get('hire_date', '未知'),
                    "termination_date": basic_info.get('termination_date', '未知')
                },
                "next_stage": 2,
                "next_stage_name": "证据需求生成阶段",
                "case_info_file": case_info_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"案件信息收集失败: {str(e)}"
            }
    
    def evidence_stage2_evidence_list_generation(self) -> Dict[str, Any]:
        """阶段二：证据需求生成"""
        try:
            if not self.evidence_mode or not self.case_info:
                return {
                    "success": False,
                    "error": "请先完成案件信息收集阶段"
                }
            
            if not self.evidence_generator:
                return {
                    "success": False,
                    "error": "证据生成模块不可用"
                }
            
            # 生成案件摘要
            case_summary = self.case_parser.generate_case_summary(self.case_info)
            
            # 调用证据生成器生成证据清单
            self.evidence_list = self.evidence_generator.generate_evidence_list(
                case_summary, self.case_info
            )
            
            if not self.evidence_list:
                return {
                    "success": False,
                    "error": "无法生成证据清单"
                }
            
            # 保存证据清单
            evidence_list_path = os.path.join(self.session_dir, f'{self.case_id}_evidence_list.json')
            with open(evidence_list_path, 'w', encoding='utf-8') as f:
                json.dump(self.evidence_list, f, ensure_ascii=False, indent=2)
            
            # 更新状态
            self.current_evidence_stage = EvidenceStage.STAGE3_GUIDANCE
            self.session_status = SessionStatus.EVIDENCE_GUIDANCE
            
            # 格式化证据清单用于前端显示
            evidence_items = []
            for evidence in self.evidence_list.get('evidence_items', []):
                evidence_items.append({
                    "type": evidence.get('type', '未知类型'),
                    "importance": evidence.get('importance', '未知重要性'),
                    "description": evidence.get('description', '无描述'),
                    "collection_method": evidence.get('collection_method', '无方法'),
                    "legal_basis": evidence.get('legal_basis', '无依据')
                })
            
            return {
                "success": True,
                "message": "✅ 证据清单生成完成",
                "case_summary": case_summary,
                "evidence_list": evidence_items,
                "total_evidence_count": len(evidence_items),
                "next_stage": 3,
                "next_stage_name": "证据收集指导阶段",
                "evidence_list_file": evidence_list_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"证据清单生成失败: {str(e)}"
            }
    
    def evidence_stage3_guidance_chat(self, user_input: str) -> Dict[str, Any]:
        """阶段三：证据收集指导对话"""
        try:
            if not self.evidence_mode or not self.evidence_list:
                return {
                    "success": False,
                    "error": "请先完成证据清单生成阶段"
                }
            
            if not self.chat_handler:
                return {
                    "success": False,
                    "error": "对话处理模块不可用"
                }
            
            if not user_input.strip():
                return {
                    "success": False,
                    "error": "请输入您的问题"
                }
            
            # 检查是否结束指导阶段
            if user_input.lower() in ['没有', '无', 'no', '结束']:
                # 更新状态到下一阶段
                self.current_evidence_stage = EvidenceStage.STAGE4_INVENTORY
                self.session_status = SessionStatus.EVIDENCE_INVENTORY
                
                return {
                    "success": True,
                    "message": "✅ 证据收集指导完成",
                    "response": "好的，现在我们进入证据清单收集阶段。请告诉我您目前手上持有哪些证据？",
                    "stage_completed": True,
                    "next_stage": 4,
                    "next_stage_name": "证据清单收集阶段"
                }
            
            # 调用对话处理模块
            chat_response = self.chat_handler.handle_chat(
                user_input, self.case_info, self.evidence_list, self.evidence_chat_history
            )
            
            if not chat_response:
                return {
                    "success": False,
                    "error": "无法生成回复"
                }
            
            ai_reply = chat_response.get('reply', '抱歉，无法生成回复')
            
            # 保存对话历史
            self.evidence_chat_history.append({
                'role': 'user',
                'content': user_input,
                'timestamp': datetime.now().isoformat(),
                'stage': 'evidence_guidance'
            })
            self.evidence_chat_history.append({
                'role': 'assistant',
                'content': ai_reply,
                'timestamp': datetime.now().isoformat(),
                'stage': 'evidence_guidance'
            })
            
            # 保存ShareGPT格式数据
            self._save_sharegpt_data_entry(user_input, ai_reply, "证据收集指导")
            
            return {
                "success": True,
                "response": ai_reply,
                "stage_completed": False,
                "current_stage": 3,
                "stage_name": "证据收集指导阶段",
                "hint": "如果没有其他问题，请回答'没有'进入下一阶段"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"证据收集指导失败: {str(e)}"
            }
    
    def evidence_stage4_inventory_collection(self, user_input: str) -> Dict[str, Any]:
        """阶段四：证据清单收集"""
        try:
            if not self.evidence_mode or self.current_evidence_stage != EvidenceStage.STAGE4_INVENTORY:
                return {
                    "success": False,
                    "error": "请先完成证据收集指导阶段"
                }
            
            if not user_input.strip():
                return {
                    "success": False,
                    "error": "请输入您持有的证据信息"
                }
            
            # 使用LLM解析用户的证据描述
            parsed_evidence = self._parse_evidence_with_llm(user_input)
            
            if not parsed_evidence:
                return {
                    "success": False,
                    "error": "抱歉，无法解析您的证据信息，请重新描述"
                }
            
            # 证据类型名称映射
            evidence_type_names = {
                'contract': '劳动合同', 'payslip': '工资单', 'attendance': '考勤记录',
                'injury': '工伤鉴定', 'recording': '录音', 'chat': '聊天记录', 'other': '其他'
            }
            
            # 格式化解析结果
            formatted_evidence = []
            for evidence in parsed_evidence:
                type_name = evidence_type_names.get(evidence['type'], evidence['type'])
                formatted_evidence.append({
                    "name": evidence['name'],
                    "type": evidence['type'],
                    "type_name": type_name,
                    "description": evidence.get('description', ''),
                    "added_time": evidence.get('added_time', datetime.now().isoformat())
                })
            
            return {
                "success": True,
                "message": "✅ 证据清单解析完成",
                "parsed_evidence": formatted_evidence,
                "total_count": len(formatted_evidence),
                "requires_confirmation": True,
                "hint": "请确认以上证据清单是否正确"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"证据清单收集失败: {str(e)}"
            }
    
    def evidence_stage4_confirm_inventory(self, confirmed: bool, evidence_list: List[Dict] = None) -> Dict[str, Any]:
        """阶段四：确认证据清单"""
        try:
            if not confirmed:
                return {
                    "success": True,
                    "message": "请重新描述您的证据",
                    "requires_reinput": True
                }
            
            if not evidence_list:
                return {
                    "success": False,
                    "error": "证据清单不能为空"
                }
            
            # 保存用户证据清单
            self.user_evidence_inventory = evidence_list
            
            # 保存到文件
            inventory_path = os.path.join(self.session_dir, f'{self.case_id}_evidence_inventory.json')
            with open(inventory_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'case_id': self.case_id,
                    'inventory': self.user_evidence_inventory,
                    'created_time': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            # 更新状态
            self.current_evidence_stage = EvidenceStage.STAGE5_ANALYSIS
            self.session_status = SessionStatus.EVIDENCE_ANALYSIS
            
            return {
                "success": True,
                "message": "✅ 证据清单确认完成",
                "inventory_saved": True,
                "next_stage": 5,
                "next_stage_name": "证据分析评估阶段",
                "inventory_file": inventory_path,
                "evidence_count": len(self.user_evidence_inventory)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"确认证据清单失败: {str(e)}"
            }
    
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
    
    def evidence_stage5_analysis_start(self) -> Dict[str, Any]:
        """阶段五：开始证据分析评估"""
        try:
            if not self.evidence_mode or not self.user_evidence_inventory:
                return {
                    "success": False,
                    "error": "请先完成证据清单收集阶段"
                }
            
            if not self.evidence_analyzer:
                return {
                    "success": False,
                    "error": "证据分析模块不可用"
                }
            
            # 显示证据清单概览
            evidence_overview = []
            for i, evidence in enumerate(self.user_evidence_inventory, 1):
                evidence_overview.append({
                    "index": i,
                    "name": evidence['name'],
                    "type": evidence['type'],
                    "type_name": evidence.get('type_name', evidence['type']),
                    "description": evidence.get('description', '')
                })
            
            return {
                "success": True,
                "message": "✅ 证据分析阶段开始",
                "evidence_overview": evidence_overview,
                "total_evidence": len(self.user_evidence_inventory),
                "current_stage": 5,
                "stage_name": "证据分析评估阶段",
                "instructions": "请逐一上传证据文件进行分析，或输入文件名进行分析"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"开始证据分析失败: {str(e)}"
            }
    
    def evidence_stage5_analyze_file(self, file_name: str, evidence_type: str) -> Dict[str, Any]:
        """阶段五：分析单个证据文件"""
        try:
            if not self.evidence_mode or not self.evidence_analyzer:
                return {
                    "success": False,
                    "error": "证据分析模块不可用"
                }
            
            # 检查文件是否存在
            file_path = os.path.join(self.session_dir, 'uploads', file_name)
            if not os.path.exists(file_path):
                # 尝试在EvidenceAnalysis/uploads目录查找
                alt_file_path = os.path.join('EvidenceAnalysis', 'uploads', file_name)
                if os.path.exists(alt_file_path):
                    file_path = alt_file_path
                else:
                    return {
                        "success": False,
                        "error": f"文件不存在: {file_name}，请确保文件已上传到uploads目录"
                    }
            
            # 验证证据类型
            supported_types = ['contract', 'payslip', 'attendance', 'injury', 'recording', 'chat']
            if evidence_type not in supported_types and evidence_type != 'other':
                return {
                    "success": False,
                    "error": f"不支持的证据类型: {evidence_type}"
                }
            
            if evidence_type == 'other':
                return {
                    "success": False,
                    "error": "'其他'类型的证据无法自动分析，建议手动指定具体类型",
                    "suggestion": "请将证据类型更改为具体的类型，如contract、payslip等"
                }
            
            # 调用证据分析模块
            analysis_result = self.evidence_analyzer.analyze_evidence(file_path, evidence_type)
            
            if not analysis_result:
                return {
                    "success": False,
                    "error": "证据分析失败，请检查文件格式或网络连接"
                }
            
            # 保存分析结果
            result_record = {
                'file_name': file_name,
                'evidence_type': evidence_type,
                'analysis_time': datetime.now().isoformat(),
                'analysis_result': analysis_result,
                'file_path': file_path
            }
            self.analysis_results.append(result_record)
            
            # 格式化分析结果用于前端显示
            formatted_result = {
                "file_name": file_name,
                "evidence_type": evidence_type,
                "analysis_time": result_record['analysis_time']
            }
            
            # 添加分析结果的关键信息
            for key, value in analysis_result.items():
                if key != 'recommendations' and value:
                    formatted_result[key] = value
            
            # 添加改进建议
            recommendations = analysis_result.get('recommendations', [])
            if recommendations:
                formatted_result['recommendations'] = recommendations
            
            return {
                "success": True,
                "message": f"✅ 文件 {file_name} 分析完成",
                "analysis_result": formatted_result,
                "total_analyzed": len(self.analysis_results),
                "remaining_count": len(self.user_evidence_inventory) - len(self.analysis_results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"证据分析失败: {str(e)}"
            }
    
    def evidence_stage5_get_progress(self) -> Dict[str, Any]:
        """阶段五：获取分析进度"""
        try:
            total_evidence = len(self.user_evidence_inventory)
            analyzed_count = len(self.analysis_results)
            
            # 已分析的证据
            analyzed_evidence = []
            for result in self.analysis_results:
                analysis = result.get('analysis_result', {})
                raw_result = analysis.get('raw_result', {})
                
                # 获取文件类型和有效性
                file_type = raw_result.get('文件类型') or analysis.get('file_type', '未知')
                validity = raw_result.get('是否可以作为核心证据') or analysis.get('is_valid_evidence')
                
                if validity is True:
                    validity = '是'
                elif validity is False:
                    validity = '否'
                elif validity is None:
                    validity = '未知'
                
                analyzed_evidence.append({
                    "file_name": result.get('file_name', '未知文件'),
                    "evidence_type": result.get('evidence_type', '未知类型'),
                    "file_type": file_type,
                    "validity": validity,
                    "analysis_time": result.get('analysis_time', '未知时间')
                })
            
            # 待分析的证据
            remaining_evidence = []
            analyzed_files = [result['file_name'] for result in self.analysis_results]
            for evidence in self.user_evidence_inventory:
                if evidence['name'] not in analyzed_files:
                    remaining_evidence.append({
                        "name": evidence['name'],
                        "type": evidence['type'],
                        "type_name": evidence.get('type_name', evidence['type'])
                    })
            
            # 检查是否可以进入下一阶段
            can_proceed = analyzed_count > 0  # 至少分析一个证据就可以进入对话阶段
            
            return {
                "success": True,
                "total_evidence": total_evidence,
                "analyzed_count": analyzed_count,
                "remaining_count": total_evidence - analyzed_count,
                "progress_percentage": round((analyzed_count / total_evidence) * 100, 1) if total_evidence > 0 else 0,
                "analyzed_evidence": analyzed_evidence,
                "remaining_evidence": remaining_evidence,
                "can_proceed": can_proceed,
                "next_stage": 6 if can_proceed else 5,
                "next_stage_name": "证据分析对话阶段" if can_proceed else "继续证据分析"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取分析进度失败: {str(e)}"
            }
    
    def evidence_stage5_complete(self) -> Dict[str, Any]:
        """阶段五：完成证据分析评估"""
        try:
            if not self.analysis_results:
                return {
                    "success": False,
                    "error": "请至少分析一个证据文件后再进入下一阶段"
                }
            
            # 更新状态
            self.current_evidence_stage = EvidenceStage.STAGE6_CHAT
            self.session_status = SessionStatus.EVIDENCE_CHAT
            
            # 保存分析结果到文件
            analysis_results_path = os.path.join(self.session_dir, f'{self.case_id}_analysis_results.json')
            with open(analysis_results_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'case_id': self.case_id,
                    'results': self.analysis_results
                }, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": "✅ 证据分析评估完成",
                "analyzed_count": len(self.analysis_results),
                "next_stage": 6,
                "next_stage_name": "证据分析对话阶段",
                "analysis_file": analysis_results_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"完成证据分析失败: {str(e)}"
            }
    
    def evidence_stage6_analysis_chat(self, user_input: str) -> Dict[str, Any]:
        """阶段六：证据分析对话"""
        try:
            if not self.evidence_mode or not self.analysis_results:
                return {
                    "success": False,
                    "error": "请先完成证据分析评估阶段"
                }
            
            if not self.chat_handler:
                return {
                    "success": False,
                    "error": "对话处理模块不可用"
                }
            
            if not user_input.strip():
                return {
                    "success": False,
                    "error": "请输入您的问题"
                }
            
            # 检查是否结束对话阶段
            if user_input.lower() in ['没有', '无', 'no', '结束', 'next']:
                # 生成最终报告
                return self._generate_evidence_final_report()
            
            # 构建证据分析结果的上下文
            evidence_context = self._build_evidence_context()
            
            # 调用对话处理模块，传入证据分析结果作为上下文
            chat_response = self.chat_handler.handle_evidence_analysis_chat(
                user_input, self.case_info, self.evidence_list, 
                self.analysis_results, evidence_context, self.evidence_chat_history
            )
            
            if not chat_response:
                return {
                    "success": False,
                    "error": "无法生成回复"
                }
            
            ai_reply = chat_response.get('reply', '抱歉，无法生成回复')
            
            # 保存对话历史
            self.evidence_chat_history.append({
                'role': 'user',
                'content': user_input,
                'timestamp': datetime.now().isoformat(),
                'stage': 'evidence_analysis_chat'
            })
            self.evidence_chat_history.append({
                'role': 'assistant',
                'content': ai_reply,
                'timestamp': datetime.now().isoformat(),
                'stage': 'evidence_analysis_chat'
            })
            
            # 保存ShareGPT格式数据
            self._save_sharegpt_data_entry(user_input, ai_reply, "证据分析对话")
            
            return {
                "success": True,
                "response": ai_reply,
                "stage_completed": False,
                "current_stage": 6,
                "stage_name": "证据分析对话阶段",
                "hint": "如果没有其他问题，请回答'没有'生成最终报告"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"证据分析对话失败: {str(e)}"
            }
    
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
    
    def _generate_evidence_final_report(self) -> Dict[str, Any]:
        """生成举证分析最终报告"""
        try:
            if not self.report_generator:
                return {
                    "success": False,
                    "error": "报告生成模块不可用"
                }
            
            # 准备报告数据
            report_data = {
                'case_info': self.case_info,
                'evidence_list': self.evidence_list,
                'chat_history': self.evidence_chat_history,
                'analysis_results': self.analysis_results,
                'user_evidence_inventory': self.user_evidence_inventory
            }
            
            # 生成报告
            report_path = self.report_generator.generate_report(
                self.case_id, report_data
            )
            
            if not report_path:
                return {
                    "success": False,
                    "error": "报告生成失败"
                }
            
            # 保存ShareGPT格式对话数据
            self._save_sharegpt_data_to_file()
            
            # 更新状态为完成
            self.session_status = SessionStatus.FINISHED
            
            # 生成报告摘要
            summary = {
                "case_id": self.case_id,
                "total_evidence_analyzed": len(self.analysis_results),
                "total_chat_messages": len(self.evidence_chat_history),
                "completion_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return {
                "success": True,
                "message": "🎉 举证分析流程已完成！",
                "report_path": report_path,
                "summary": summary,
                "stage_completed": True,
                "all_stages_completed": True,
                "final_message": "感谢使用AI劳动法律师举证分析系统！祝您维权顺利！",
                "show_comprehensive_report": True  # 添加跳转到综合报告的标志
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"生成最终报告失败: {str(e)}"
            }
    
    def _save_sharegpt_data_to_file(self):
        """将ShareGPT数据保存到文件"""
        if not self.case_id or not self.sharegpt_data["conversations"]:
            return
        
        try:
            sharegpt_file_path = os.path.join(self.session_dir, f'{self.case_id}_sharegpt_data.json')
            with open(sharegpt_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.sharegpt_data, f, ensure_ascii=False, indent=2)
            
            print(f"ShareGPT格式对话数据已保存到: {sharegpt_file_path}")
            
        except Exception as e:
            print(f"保存ShareGPT数据文件失败: {e}")
         
    def _generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    def _init_modules(self):
        """初始化各个功能模块"""
        try:
            # 初始化案例分析生成器
            self.case_analyzer = CaseAnalysisGenerator()
            
            # 初始化举证分析模块（如果可用）
            if all([CaseParser, EvidenceGenerator, ChatHandler, EvidenceAnalyzer, ReportGenerator]):
                self.case_parser = CaseParser()
                self.evidence_generator = EvidenceGenerator()
                self.chat_handler = ChatHandler()
                self.evidence_analyzer = EvidenceAnalyzer()
                self.report_generator = ReportGenerator()
                print("✅ 举证分析模块初始化成功")
            else:
                self.case_parser = None
                self.evidence_generator = None
                self.chat_handler = None
                self.evidence_analyzer = None
                self.report_generator = None
                print("⚠️ 举证分析模块不可用，仅基础功能可用")
            
        except Exception as e:
            print(f"❌ 模块初始化失败: {e}")
            raise
    
    def start_conversation(self) -> Dict[str, Any]:
        """开始对话，返回初始状态"""
        self.conversation_history = create_new_conversation()
        return {
            "success": True,
            "session_id": self.session_id,
            "status": self.session_status.value,
            "message": "🤝 欢迎使用AI劳动法律师咨询系统！我将通过专业的对话帮您梳理劳动争议相关问题。请放心，所有信息都会严格保密。",
            "phase": "information_collection",
            "phase_name": "信息收集阶段"
        }
    
    def process_user_input(self, user_input: str, stream: bool = False):
        """处理用户输入，返回律师回复或流式响应"""
        try:
            if not user_input.strip():
                return {
                    "success": False,
                    "error": "请输入您的问题或回答..."
                }
            
            if stream:
                # 准备会话与消息
                if self.conversation_history is None:
                    self.conversation_history = create_new_conversation()
                # 先将用户输入加入历史，保持一致性
                self.conversation_history.append({'role': 'user', 'content': user_input})

                adapter = DoubaoAdapter()
                # 使用历史消息进行流式生成
                stream_iter = adapter.call_api(self.conversation_history, model_name='doubao-seed-1-6-250615', stream=True)
                full_text = ""

                @stream_with_context
                def generate():
                    nonlocal full_text
                    print("[SSE] generator start")
                    chunk_idx = 0
                    for chunk in stream_iter:
                        chunk_idx += 1
                        try:
                            # 尝试多种结构提取文本
                            text = None
                            # 1) Ark标准：choices[0].delta.content 或 choices[0].message.content
                            if hasattr(chunk, 'choices') and chunk.choices:
                                choice = chunk.choices[0]
                                delta = getattr(choice, 'delta', None)
                                if delta is not None:
                                    text = getattr(delta, 'content', None)
                                if not text:
                                    message = getattr(choice, 'message', None)
                                    if message is not None:
                                        text = getattr(message, 'content', None)
                            # 2) 一些SDK会直接提供 output_text
                            if not text and hasattr(chunk, 'output_text'):
                                text = getattr(chunk, 'output_text', None)
                            # 3) 字典结构兜底
                            if not text and isinstance(chunk, dict):
                                try:
                                    chs = chunk.get('choices')
                                    if chs:
                                        delta = chs[0].get('delta') if isinstance(chs[0], dict) else None
                                        if delta and isinstance(delta, dict):
                                            text = delta.get('content')
                                        if not text:
                                            msg = chs[0].get('message') if isinstance(chs[0], dict) else None
                                            if msg and isinstance(msg, dict):
                                                text = msg.get('content')
                                    if not text:
                                        text = chunk.get('output_text')
                                except Exception:
                                    pass

                            if text:
                                full_text += text
                                print(f"[SSE] emit chunk #{chunk_idx} len={len(text)} text='{text[:100]}'")
                                try:
                                    payload = json.dumps({'content': text}, ensure_ascii=False)
                                except Exception as jex:
                                    print(f"[SSE] json dumps failed for chunk #{chunk_idx}: {jex}")
                                    payload = json.dumps({'content': str(text)}, ensure_ascii=False)
                                yield f"data: {payload}\n\n"
                            else:
                                # 打印有限制的调试信息，避免巨量日志
                                try:
                                    srepr = str(chunk)
                                except Exception:
                                    srepr = '<unrepr>'
                                print(f"[SSE] no text extracted from chunk #{chunk_idx}: {srepr[:200]}")
                        except Exception as ex:
                            print(f"[SSE] error processing chunk #{chunk_idx}: {ex}")
                            continue
                    # 流结束后，记录助手回复到历史
                    try:
                        print(f"[SSE] stream ended, total length={len(full_text)}")
                        self.conversation_history.append({'role': 'assistant', 'content': full_text})
                        conversation_ended = ('？' not in full_text) and ('?' not in full_text)
                        if conversation_ended:
                            self.session_status = SessionStatus.COMPLETED
                            self.conversation_file_path = self._save_conversation()
                        print("[SSE] generator end")
                    except Exception as ex:
                        print(f"[SSE] error after stream end: {ex}")

                return Response(
                    generate(),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'X-Accel-Buffering': 'no'
                    }
                )
            
            # 处理特殊命令
            if user_input.lower() == 'status':
                return self.get_status()
            
            # 调用律师对话模块
            response, self.conversation_history, conversation_ended = chat_with_lawyer(
                user_input, self.conversation_history
            )
            
            # 文本完整性检查
            if not response or not response.strip():
                return {
                    "success": False,
                    "error": "系统回复为空，请重试"
                }
            
            # 确保响应文本编码正确
            try:
                # 验证文本可以正确序列化为JSON
                json.dumps(response, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                print(f"警告: 响应文本JSON序列化失败: {e}")
                return {
                    "success": False,
                    "error": "响应文本格式错误"
                }
            
            result = {
                "success": True,
                "response": response,
                "conversation_ended": conversation_ended,
                "session_status": self.session_status.value
            }
            
            if conversation_ended:
                self.session_status = SessionStatus.COMPLETED
                # 保存对话记录
                self.conversation_file_path = self._save_conversation()
                result["phase_completed"] = True
                result["next_phase"] = "case_analysis"
                result["next_phase_name"] = "案例分析阶段"
                result["message"] = "✅ 信息收集阶段完成，开始案例分析"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"对话处理错误: {str(e)}"
            }
    
    def select_service_type(self, service_type: str) -> Dict[str, Any]:
        """选择服务类型"""
        try:
            if service_type.lower() == 'free':
                self.user_type = UserType.FREE
                return {
                    "success": True,
                    "message": "✅ 已选择免费服务",
                    "service_type": "free",
                    "next_phase": "final_report",
                    "next_phase_name": "生成最终报告"
                }
            elif service_type.lower() == 'premium':
                self.user_type = UserType.PREMIUM
                return {
                    "success": True,
                    "message": "✅ 已选择付费服务\n💡 您可以选择直接生成报告或进入6阶段举证分析",
                    "service_type": "premium",
                    "next_phase": "premium_choice",
                    "next_phase_name": "选择服务内容",
                    "show_premium_options": True
                }
            elif service_type.lower() == 'evidence':
                # 付费用户选择举证分析
                if self.user_type != UserType.PREMIUM:
                    return {
                        "success": False,
                        "error": "只有付费用户才能使用举证分析功能"
                    }
                return {
                    "success": True,
                    "message": "✅ 开始6阶段举证分析",
                    "service_type": "evidence",
                    "next_phase": "evidence_analysis",
                    "next_phase_name": "举证分析阶段"
                }
            else:
                return {
                    "success": False,
                    "error": "请选择有效的服务类型"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"服务选择错误: {str(e)}"
            }
    
    # 删除 perform_guidance 方法
    
    # 删除 process_guidance_input 方法
    
    # 删除 _generate_guidance_analysis_report 方法
     
    def perform_case_analysis(self) -> Dict[str, Any]:
        """执行案例分析"""
        try:
            if not self.conversation_file_path:
                return {
                    "success": False,
                    "error": "未找到对话记录文件"
                }
            
            self.session_status = SessionStatus.ANALYZING
            
            # 调用案例分析模块
            self.case_analysis_result = self.case_analyzer.analyze_conversation(
                self.conversation_file_path
            )
            
            if self.case_analysis_result and self.case_analysis_result != "分析失败":
                # 保存分析结果
                analysis_file = os.path.join(self.session_dir, "case_analysis.txt")
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    f.write(self.case_analysis_result)
                
                # 案例分析完成后，进入服务选择阶段
                self.session_status = SessionStatus.SERVICE_SELECTION
                
                result = {
                    "success": True,
                    "analysis_result": self.case_analysis_result,
                    "message": "✅ 案例分析完成，请选择服务模式",
                    "analysis_file": analysis_file,
                    "next_phase": "service_selection",
                    "next_phase_name": "服务选择",
                    "show_service_selection": True,
                    "phase_completed": True
                }
                
                return result
            else:
                return {
                    "success": False,
                    "error": "案例分析失败，请稍后重试"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"案例分析过程中出错: {str(e)}"
            }
    

    
    def generate_final_report(self) -> Dict[str, Any]:
        """生成最终综合报告"""
        try:
            # 生成综合报告
            final_report = self._create_comprehensive_report()
            
            # 保存最终报告
            report_file = os.path.join(self.session_dir, "final_report.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, ensure_ascii=False, indent=2)
            
            # 生成可读性更好的文本报告
            text_report_file = os.path.join(self.session_dir, "final_report.txt")
            self._save_text_report(final_report, text_report_file)
            
            self.session_status = SessionStatus.FINISHED
            
            # 生成报告摘要
            summary = self._generate_final_summary(final_report)
            
            # 生成格式化的完整报告内容
            formatted_final_report = self._format_final_report(final_report)
            
            return {
                "success": True,
                "final_report": final_report,
                "summary": summary,
                "formatted_final_report": formatted_final_report,
                "message": "🎉 咨询服务已完成，感谢您的使用！",
                "report_file": text_report_file,
                "session_completed": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"生成最终报告时出错: {str(e)}"
            }
    

    

    



    def get_status(self) -> Dict[str, Any]:
        """获取当前系统状态"""
        return {
            "success": True,
            "session_id": self.session_id,
            "user_type": self.user_type.value,
            "session_status": self.session_status.value,
            "session_dir": self.session_dir,
            "conversation_file": self.conversation_file_path,
            "has_case_analysis": bool(self.case_analysis_result)
        }
    
    def _save_conversation(self) -> str:
        """保存对话记录"""
        if not self.conversation_history:
            return None
        
        # 使用原有的保存逻辑，但指定保存位置
        original_file = save_conversation_to_json(self.conversation_history)
        
        # 复制到会话目录
        session_file = os.path.join(self.session_dir, "conversation.json")
        if os.path.exists(original_file):
            import shutil
            shutil.copy2(original_file, session_file)
            return session_file
        
        return original_file
    

    
    def _create_comprehensive_report(self) -> Dict[str, Any]:
        """创建综合报告"""
        report = {
            "会话信息": {
                "会话ID": self.session_id,
                "用户类型": self.user_type.value,
                "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "服务状态": "已完成"
            },
            "对话记录文件": self.conversation_file_path,
            "案例分析结果": self.case_analysis_result,
        }
        
        # 根据用户类型和是否使用举证分析设置服务级别
        if self.user_type == UserType.PREMIUM:
            if self.evidence_mode and self.analysis_results:
                report["服务级别"] = "付费专业版 - 举证分析"
                report["举证分析结果"] = self.analysis_results
                report["证据清单"] = self.user_evidence_inventory
            else:
                report["服务级别"] = "付费专业版 - 基础服务"
        else:
            report["服务级别"] = "免费基础版"
        
        return report
    
    def _save_text_report(self, report: Dict[str, Any], filename: str):
        """保存可读性更好的文本报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("AI劳动法律师咨询报告\n")
            f.write("=" * 80 + "\n\n")
            
            # 会话信息
            session_info = report.get("会话信息", {})
            f.write("📋 会话信息:\n")
            f.write("-" * 40 + "\n")
            for key, value in session_info.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # 删除举证指导相关内容
            
            # 案例分析
            if report.get("案例分析结果"):
                f.write("⚖️ 案例分析:\n")
                f.write("-" * 40 + "\n")
                f.write(str(report["案例分析结果"]) + "\n\n")
            

            
            f.write("=" * 80 + "\n")
            f.write("报告结束\n")
            f.write("=" * 80 + "\n")
    
    def _generate_final_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终报告摘要"""
        session_info = report.get("会话信息", {})
        summary = {
            "session_id": session_info.get("会话ID", "N/A"),
            "service_level": report.get("服务级别", "N/A"),
            "completion_time": session_info.get("生成时间", "N/A"),
            "has_case_analysis": bool(report.get("案例分析结果"))
        }
        
        return summary
    

    
    def _format_final_report(self, final_report: Dict[str, Any]) -> str:
        """格式化最终综合报告为可读文本"""
        if not final_report:
            return "暂无最终报告内容"
        
        report_lines = []
        report_lines.append("📊 AI劳动法律师咨询综合报告")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # 会话信息
        session_info = final_report.get("会话信息", {})
        if session_info:
            report_lines.append("📋 会话信息：")
            report_lines.append("-" * 30)
            for key, value in session_info.items():
                report_lines.append(f"{key}: {value}")
            report_lines.append("")
        
        # 案例分析结果
        case_analysis = final_report.get("案例分析结果")
        if case_analysis:
            report_lines.append("⚖️ 案例分析：")
            report_lines.append("-" * 30)
            report_lines.append(str(case_analysis))
            report_lines.append("")
        

        
        report_lines.append("=" * 60)
        report_lines.append("报告结束")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    

    

    

    

    


# Flask应用初始化
app = Flask(__name__)
app.secret_key = 'ai_lawyer_secret_key_2024'
CORS(app)  # 允许跨域请求

# 配置JSON响应确保中文字符正确显示
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# 全局会话存储
sessions = {}

def get_or_create_session(session_id: str = None) -> WebAILawyerSystem:
    """获取或创建会话"""
    if session_id and session_id in sessions:
        return sessions[session_id]
    
    # 创建新会话
    new_session = WebAILawyerSystem(session_id)
    sessions[new_session.session_id] = new_session
    return new_session

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/start_session', methods=['POST'])
def start_session():
    """开始新会话"""
    try:
        lawyer_system = get_or_create_session()
        result = lawyer_system.start_conversation()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"启动会话失败: {str(e)}"
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """处理对话"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_input = data.get('message', '').strip()
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not user_input:
            return jsonify({
                "success": False,
                "error": "消息不能为空"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.process_user_input(user_input)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"处理对话失败: {str(e)}"
        }), 500

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """处理对话（流式输出 SSE）"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_input = data.get('message', '').strip()

        print(f"[SSE] /api/chat/stream request received session_id={session_id} msg_preview='{user_input[:50]}'")

        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not user_input:
            return jsonify({
                "success": False,
                "error": "消息不能为空"
            }), 400

        lawyer_system = get_or_create_session(session_id)
        print("[SSE] dispatching to process_user_input(stream=True)")
        # 直接返回流式 Response
        return lawyer_system.process_user_input(user_input, stream=True)
    except Exception as e:
        # SSE 错误返回普通 JSON
        print(f"[SSE] chat_stream error: {e}")
        return jsonify({
            "success": False,
            "error": f"处理流式对话失败: {str(e)}"
        }), 500

@app.route('/api/select_service', methods=['POST'])
def select_service():
    """选择服务类型"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        service_type = data.get('service_type')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not service_type:
            return jsonify({
                "success": False,
                "error": "缺少服务类型参数"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.select_service_type(service_type)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"选择服务失败: {str(e)}"
        }), 500

@app.route('/api/case_analysis', methods=['POST'])
def case_analysis():
    """执行案例分析"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.perform_case_analysis()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"案例分析失败: {str(e)}"
        }), 500



@app.route('/api/final_report', methods=['POST'])
def final_report():
    """生成最终报告"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.generate_final_report()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"生成报告失败: {str(e)}"
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取会话状态"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if session_id not in sessions:
            return jsonify({
                "success": False,
                "error": "会话不存在"
            }), 404
        
        lawyer_system = sessions[session_id]
        result = lawyer_system.get_status()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取状态失败: {str(e)}"
        }), 500





# 举证分析相关API路由

@app.route('/api/evidence/enable', methods=['POST'])
def enable_evidence_mode():
    """启用举证分析模式"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.enable_evidence_analysis_mode()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"启用举证分析模式失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage1', methods=['POST'])
def evidence_stage1():
    """阶段1：案件信息收集"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage1_case_info_collection()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"案件信息收集失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage2', methods=['POST'])
def evidence_stage2():
    """阶段2：证据需求生成"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage2_evidence_list_generation()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"证据需求生成失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage3', methods=['POST'])
def evidence_stage3():
    """阶段3：证据收集指导对话"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_input = data.get('message', '').strip()
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not user_input:
            return jsonify({
                "success": False,
                "error": "消息不能为空"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage3_guidance_chat(user_input)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"证据收集指导失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage4/collect', methods=['POST'])
def evidence_stage4_collect():
    """阶段4：证据清单收集"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_input = data.get('evidence_description', '').strip()
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not user_input:
            return jsonify({
                "success": False,
                "error": "证据描述不能为空"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage4_inventory_collection(user_input)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"证据清单收集失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage4/confirm', methods=['POST'])
def evidence_stage4_confirm():
    """阶段4：确认证据清单"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        confirmed = data.get('confirmed', False)
        evidence_list = data.get('evidence_list', [])
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage4_confirm_inventory(confirmed, evidence_list)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"确认证据清单失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage5/start', methods=['POST'])
def evidence_stage5_start():
    """阶段5：开始证据分析"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage5_analysis_start()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"开始证据分析失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage5/analyze', methods=['POST'])
def evidence_stage5_analyze():
    """阶段5：分析证据文件"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        file_name = data.get('file_name', '').strip()
        evidence_type = data.get('evidence_type', '').strip()
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not file_name or not evidence_type:
            return jsonify({
                "success": False,
                "error": "文件名和证据类型不能为空"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage5_analyze_file(file_name, evidence_type)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"证据分析失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage5/progress', methods=['GET'])
def evidence_stage5_progress():
    """阶段5：获取分析进度"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage5_get_progress()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取分析进度失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage5/complete', methods=['POST'])
def evidence_stage5_complete():
    """阶段5：完成证据分析"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage5_complete()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"完成证据分析失败: {str(e)}"
        }), 500

@app.route('/api/evidence/stage6', methods=['POST'])
def evidence_stage6():
    """阶段6：证据分析对话"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_input = data.get('message', '').strip()
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not user_input:
            return jsonify({
                "success": False,
                "error": "消息不能为空"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.evidence_stage6_analysis_chat(user_input)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"证据分析对话失败: {str(e)}"
        }), 500

# 文件上传相关API

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传证据文件"""
    try:
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "没有选择文件"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "文件名不能为空"
            }), 400
        
        # 获取会话系统
        lawyer_system = get_or_create_session(session_id)
        
        # 安全的文件名
        filename = secure_filename(file.filename)
        
        # 保存到会话的uploads目录
        upload_dir = os.path.join(lawyer_system.session_dir, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 获取文件信息
        file_size = os.path.getsize(file_path)
        file_ext = os.path.splitext(filename)[1].lower()
        
        return jsonify({
            "success": True,
            "message": f"文件 {filename} 上传成功",
            "file_info": {
                "filename": filename,
                "file_path": file_path,
                "file_size": file_size,
                "file_extension": file_ext,
                "upload_time": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"文件上传失败: {str(e)}"
        }), 500

@app.route('/api/upload/list', methods=['GET'])
def list_uploaded_files():
    """列出已上传的文件"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        upload_dir = os.path.join(lawyer_system.session_dir, 'uploads')
        
        if not os.path.exists(upload_dir):
            return jsonify({
                "success": True,
                "files": [],
                "total_count": 0
            })
        
        files = []
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                file_ext = os.path.splitext(filename)[1].lower()
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                files.append({
                    "filename": filename,
                    "file_size": file_size,
                    "file_extension": file_ext,
                    "upload_time": file_mtime.isoformat()
                })
        
        # 按上传时间排序
        files.sort(key=lambda x: x['upload_time'], reverse=True)
        
        return jsonify({
            "success": True,
            "files": files,
            "total_count": len(files)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取文件列表失败: {str(e)}"
        }), 500

@app.route('/api/evidence/status', methods=['GET'])
def get_evidence_status():
    """获取举证分析状态"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if session_id not in sessions:
            return jsonify({
                "success": False,
                "error": "会话不存在"
            }), 404
        
        lawyer_system = sessions[session_id]
        
        return jsonify({
            "success": True,
            "evidence_mode": lawyer_system.evidence_mode,
            "current_stage": lawyer_system.current_evidence_stage.value if lawyer_system.current_evidence_stage else None,
            "session_status": lawyer_system.session_status.value,
            "case_id": lawyer_system.case_id,
            "has_case_info": bool(lawyer_system.case_info),
            "has_evidence_list": bool(lawyer_system.evidence_list),
            "evidence_inventory_count": len(lawyer_system.user_evidence_inventory),
            "analysis_results_count": len(lawyer_system.analysis_results),
            "chat_history_count": len(lawyer_system.evidence_chat_history)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取举证分析状态失败: {str(e)}"
        }), 500


def main():
    """主函数"""
    try:
        # 创建必要的目录
        os.makedirs("sessions", exist_ok=True)
        os.makedirs("conversation_datasets", exist_ok=True)
        os.makedirs("templates", exist_ok=True)
        os.makedirs("static", exist_ok=True)
        
        # 创建举证分析相关目录
        os.makedirs("EvidenceAnalysis/data", exist_ok=True)
        os.makedirs("EvidenceAnalysis/uploads", exist_ok=True)
        os.makedirs("EvidenceAnalysis/reports", exist_ok=True)

        set_model_provider("doubao")
        
        print("🏛️ AI劳动法律师Web系统启动中...")
        print("🌐 访问地址: http://localhost:6000")
        print("=" * 60)
        
        # 启动Flask应用
        app.run(host='0.0.0.0', port=6000, debug=True)
        
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()