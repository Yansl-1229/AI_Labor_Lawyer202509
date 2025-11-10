#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多轮对话交互模块

功能：
1. 实现与用户的智能对话交互
2. 维护对话上下文和历史记录
3. 提供专业的法律咨询和证据收集指导
4. 生成相关的后续问题建议
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from openai import OpenAI


class ChatHandler:
    """对话处理器"""
    
    def __init__(self):
        """初始化对话处理器"""
        self.client = None
        self._init_qwen_client()
    
    def _init_qwen_client(self):
        """初始化Qwen客户端"""
        try:
            api_key = os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                print("警告：未设置DASHSCOPE_API_KEY环境变量")
                return
            
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            
        except Exception as e:
            print(f"初始化Qwen客户端失败: {e}")
    
    def handle_chat(self, user_message: str, case_info: Dict[str, Any], 
                   evidence_list: Dict[str, Any], chat_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """处理用户对话
        
        Args:
            user_message: 用户消息
            case_info: 案件信息
            evidence_list: 证据清单
            chat_history: 对话历史
            
        Returns:
            对话响应字典，包含回复和建议
        """
        try:
            # 使用AI模型处理对话
            if self.client:
                # 构建系统提示词
                system_prompt = self._build_chat_system_prompt(case_info, evidence_list)
                
                # 构建对话历史
                messages = [{'role': 'system', 'content': system_prompt}]
                
                # 添加最近的对话历史（限制数量避免token过多）
                recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
                for msg in recent_history:
                    messages.append({
                        'role': msg.get('role', 'user'),
                        'content': msg.get('content', '')
                    })
                
                # 添加当前用户消息
                messages.append({'role': 'user', 'content': user_message})
                
                # 调用AI模型
                completion = self.client.chat.completions.create(
                    model="qwen-max-latest",
                    messages=messages,
                    extra_body={"enable_thinking": False},
                )
                
                ai_reply = completion.choices[0].message.content
                
                # 返回固定的建议问题
                suggestions = ['如何收集劳动合同证据？', '公司不配合提供证据怎么办？', '什么是违法解除劳动合同？']
                
                return {
                    'reply': ai_reply,
                    'suggestions': suggestions
                }
            else:
                # 如果AI不可用，返回简单回复
                return {
                    'reply': '抱歉，AI服务暂时不可用。请稍后再试或联系技术支持。',
                    'suggestions': ['如何收集劳动合同证据？', '公司不配合提供证据怎么办？', '什么是违法解除劳动合同？']
                }
            
        except Exception as e:
            print(f"处理对话失败: {e}")
            return {
                'reply': '抱歉，我暂时无法处理您的问题。请稍后再试或换个方式提问。',
                'suggestions': ['如何收集劳动合同证据？', '公司不配合提供证据怎么办？', '什么是违法解除劳动合同？']
            }
    
    def _build_chat_system_prompt(self, case_info: Dict[str, Any], evidence_list: Dict[str, Any]) -> str:
        """构建对话系统提示词
        
        Args:
            case_info: 案件信息
            evidence_list: 证据清单
            
        Returns:
            系统提示词
        """
        # 提取案件关键信息
        company_name = case_info.get('basic_info', {}).get('company_name', '某公司')
        dispute_type = case_info.get('dispute_info', {}).get('type', '劳动争议')
        monthly_salary = case_info.get('basic_info', {}).get('monthly_salary', '未知')
        
        # 提取证据清单摘要
        evidence_items = evidence_list.get('evidence_items', [])
        core_evidence = [item['type'] for item in evidence_items if item.get('importance') == '核心']
        
        prompt = f"""
你是一位专业的劳动法律师，正在为当事人提供法律咨询服务。

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

请基于以上信息回答用户的法律咨询问题。
"""
        
        return prompt
    
    def handle_evidence_analysis_chat(self, user_message: str, case_info: Dict[str, Any], 
                                    evidence_list: Dict[str, Any], analysis_results: List[Dict[str, Any]],
                                    evidence_context: str, chat_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """处理证据分析对话
        
        Args:
            user_message: 用户消息
            case_info: 案件信息
            evidence_list: 证据清单
            analysis_results: 证据分析结果
            evidence_context: 证据上下文信息
            chat_history: 对话历史
            
        Returns:
            对话响应字典，包含回复和建议
        """
        try:
            # 使用AI模型处理证据分析对话
            if self.client:
                # 构建专门的证据分析提示词
                system_prompt = self._build_evidence_analysis_system_prompt(case_info, evidence_list, analysis_results)
                
                # 构建用户消息，包含证据上下文
                user_prompt = f"证据分析上下文：\n{evidence_context}\n\n用户问题：{user_message}"
                
                # 构建对话历史（只取最近的几轮对话）
                recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
                
                messages = [
                    {'role': 'system', 'content': system_prompt}
                ]
                
                # 添加对话历史
                for msg in recent_history:
                    messages.append({
                        'role': msg.get('role', 'user'),
                        'content': msg.get('content', '')
                    })
                
                # 添加当前用户消息
                messages.append({'role': 'user', 'content': user_prompt})
                
                # 调用AI模型
                completion = self.client.chat.completions.create(
                    model="qwen-max-latest",
                    messages=messages,
                    extra_body={"enable_thinking": False},
                )
                
                ai_reply = completion.choices[0].message.content
                
                # 返回固定的证据分析建议问题
                suggestions = ['证据有效性如何？', '还需要补充什么证据？', '如何改进证据质量？']
                
                return {
                    'reply': ai_reply,
                    'suggestions': suggestions
                }
            else:
                # AI不可用时的简单回复
                return {
                    'reply': '抱歉，AI服务暂时不可用。基于您已分析的证据，建议您重点关注证据的完整性和有效性。',
                    'suggestions': ['证据有效性如何？', '还需要补充什么证据？', '如何改进证据质量？']
                }
            
        except Exception as e:
            print(f"处理证据分析对话失败: {e}")
            return {
                'reply': '抱歉，我暂时无法处理您的问题。请稍后再试或换个方式提问。',
                'suggestions': ['证据有效性如何？', '还需要补充什么证据？', '如何改进证据质量？']
            }
    
    def _build_evidence_analysis_system_prompt(self, case_info: Dict[str, Any], 
                                             evidence_list: Dict[str, Any], 
                                             analysis_results: List[Dict[str, Any]]) -> str:
        """构建证据分析系统提示词"""
        company_name = case_info.get('basic_info', {}).get('company_name', '某公司')
        dispute_type = case_info.get('dispute_info', {}).get('type', '劳动争议')
        
        # 统计分析结果
        total_evidence = len(analysis_results)
        valid_evidence = sum(1 for result in analysis_results 
                           if result.get('analysis_result', {}).get('是否可以作为核心证据', 
                                result.get('analysis_result', {}).get('是否可以作为证据', '否')) == '是')
        
        prompt = f"""
你是一位专业的劳动法律师，正在为当事人提供基于证据分析结果的专业咨询服务。

【案件背景】
- 争议对象：{company_name}
- 争议类型：{dispute_type}
- 已分析证据：{total_evidence}份
- 有效证据：{valid_evidence}份

【证据分析咨询原则】
1. 基于实际的证据分析结果提供建议
2. 重点分析证据的有效性和完整性
3. 指出证据链中的薄弱环节
4. 提供具体的证据改进建议
5. 评估证据在仲裁中的作用

【回复要求】
- 直接回答用户关于证据的具体问题
- 结合证据分析结果给出专业意见
- 提供可操作的改进建议
- 控制回复长度在250字以内

请基于证据分析结果回答用户的问题。
"""
        
        return prompt