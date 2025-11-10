#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件信息解析模块

功能：
1. 读取conversation.json文件
2. 提取关键案件信息
3. 生成案件摘要
4. 数据验证和格式化
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any


class DataParseError(Exception):
    """数据解析错误"""
    pass


class CaseParser:
    """案件信息解析器"""
    
    def __init__(self):
        """初始化解析器"""
        self.conversation_data = None
        self.extracted_info = {}
    
    def parse_conversation_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """解析对话记录文件
        
        Args:
            file_path: conversation.json文件路径
            
        Returns:
            解析后的案件信息字典，失败返回None
        """
        try:
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                self.conversation_data = json.load(f)
            
            # 提取对话内容
            conversations = self._extract_conversations()
            if not conversations:
                raise DataParseError("无法提取对话内容")
            
            # 解析关键信息
            case_info = self._parse_case_information(conversations)
            
            # 验证数据完整性
            self._validate_case_info(case_info)
            
            return case_info
            
        except FileNotFoundError:
            print(f"错误：文件不存在 {file_path}")
            return None
        except json.JSONDecodeError as e:
            print(f"错误：JSON格式错误 {e}")
            return None
        except DataParseError as e:
            print(f"错误：数据解析失败 {e}")
            return None
        except Exception as e:
            print(f"错误：解析过程中发生未知错误 {e}")
            return None
    
    def _extract_conversations(self) -> List[Dict[str, str]]:
        """提取对话内容
        
        Returns:
            对话列表，每个元素包含role和value字段
        """
        conversations = []
        
        try:
            # 处理不同的JSON结构
            if isinstance(self.conversation_data, list):
                # 如果是列表，取第一个元素
                if self.conversation_data and 'conversations' in self.conversation_data[0]:
                    conversations = self.conversation_data[0]['conversations']
                else:
                    conversations = self.conversation_data
            elif isinstance(self.conversation_data, dict):
                # 如果是字典，查找conversations字段
                if 'conversations' in self.conversation_data:
                    conversations = self.conversation_data['conversations']
                else:
                    # 可能直接是对话数组
                    conversations = [self.conversation_data]
            
            # 标准化对话格式
            standardized_conversations = []
            for conv in conversations:
                if isinstance(conv, dict):
                    # 处理不同的字段名
                    role = conv.get('from', conv.get('role', 'unknown'))
                    content = conv.get('value', conv.get('content', conv.get('message', '')))
                    
                    standardized_conversations.append({
                        'role': role,
                        'content': content
                    })
            
            return standardized_conversations
            
        except Exception as e:
            raise DataParseError(f"提取对话内容失败: {e}")
    
    def _parse_case_information(self, conversations: List[Dict[str, str]]) -> Dict[str, Any]:
        """解析案件关键信息
        
        Args:
            conversations: 对话列表
            
        Returns:
            案件信息字典
        """
        # 合并所有对话内容用于信息提取
        all_text = ' '.join([conv.get('content', '') for conv in conversations])
        
        # 基本信息提取
        basic_info = self._extract_basic_info(all_text)
        
        # 争议信息提取
        dispute_info = self._extract_dispute_info(all_text)
        
        # 证据状态提取
        evidence_status = self._extract_evidence_status(all_text)
        
        # 构建完整的案件信息
        case_info = {
            'basic_info': basic_info,
            'dispute_info': dispute_info,
            'evidence_status': evidence_status,
            'original_conversations': conversations,
            'created_at': datetime.now().isoformat()
        }
        
        return case_info
    
    def _extract_basic_info(self, text: str) -> Dict[str, Any]:
        """提取基本信息
        
        Args:
            text: 对话文本
            
        Returns:
            基本信息字典
        """
        basic_info = {
            'employee_name': None,
            'company_name': None,
            'hire_date': None,
            'termination_date': None,
            'monthly_salary': None,
            'position': None
        }
        
        # 提取公司名称
        company_patterns = [
            r'(科大讯飞科技股份有限公司)',
            r'([\u4e00-\u9fa5]+(?:科技|有限|股份|集团|公司)+[\u4e00-\u9fa5]*公司)',
            r'([A-Za-z\u4e00-\u9fa5]+(?:有限公司|股份有限公司|科技有限公司))',
            r'公司.*?全称.*?是.*?([\u4e00-\u9fa5A-Za-z]+(?:有限公司|股份有限公司|科技有限公司|集团公司))',
            r'工作.*?单位.*?([\u4e00-\u9fa5A-Za-z]+(?:有限公司|股份有限公司|科技有限公司|集团公司))',
            r'在.*?([\u4e00-\u9fa5A-Za-z]+(?:有限公司|股份有限公司|科技有限公司|集团公司)).*?工作',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                basic_info['company_name'] = match.group(1)
                break
        
        # 如果没有找到具体公司名称，但对话中提到了公司，设置一个通用标识
        if not basic_info['company_name'] and ('公司' in text):
            print("警告：对话中提到公司但未能提取具体公司名称，建议用户补充公司全称信息")
        
        # 提取入职日期
        hire_date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日入职',
            r'入职.*?(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{1,2})-(\d{1,2})入职',
            r'我是(\d{4})年(\d{1,2})月(\d{1,2})日入职的'
        ]
        
        for pattern in hire_date_patterns:
            match = re.search(pattern, text)
            if match:
                year, month, day = match.groups()
                basic_info['hire_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                break
        
        # 提取解除日期
        termination_patterns = [
            r'解除劳动合同日期是(\d{1,2})月(\d{1,2})号',
            r'(\d{4})年(\d{1,2})月(\d{1,2})日解除',
            r'解除.*?(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})月(\d{1,2})日.*?解除'
        ]
        
        for pattern in termination_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:  # 只有月日
                    month, day = groups
                    # 假设是当前年份或从入职日期推断
                    year = "2024"  # 默认年份
                    basic_info['termination_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                elif len(groups) == 3:  # 年月日
                    year, month, day = groups
                    basic_info['termination_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                break
        
        # 提取月薪
        salary_patterns = [
            r'月平均工资(\d+)元',
            r'月平均(\d+)元',  # 新增：匹配"月平均12000元"
            r'月薪(\d+)元',
            r'工资.*?(\d+)元',
            r'薪资.*?(\d+)元',
            r'(\d+)元/月',
            r'月工资.*?(\d+)元',
            r'月收入.*?(\d+)元'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                basic_info['monthly_salary'] = int(match.group(1))
                break
        
        # 尝试从对话中推断员工姓名
        name_patterns = [
            r'我叫([\u4e00-\u9fa5]{2,4})',
            r'我是([\u4e00-\u9fa5]{2,4})',
            r'姓名.*?([\u4e00-\u9fa5]{2,4})'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                basic_info['employee_name'] = match.group(1)
                break
        
        # 如果没有找到姓名，使用默认值
        if not basic_info['employee_name']:
            basic_info['employee_name'] = "当事人"
        
        return basic_info
    
    def _extract_dispute_info(self, text: str) -> Dict[str, Any]:
        """提取争议信息
        
        Args:
            text: 对话文本
            
        Returns:
            争议信息字典
        """
        dispute_info = {
            'type': None,
            'reason_given': None,
            'notice_date': None,
            'has_training': False,
            'has_transfer': False,
            'has_evidence': False,
            'performance_rating': None
        }
        
        # 提取争议类型
        if '违法辞退' in text or '违法解除' in text:
            dispute_info['type'] = '违法解除劳动合同'
        elif '工资' in text and ('拖欠' in text or '未支付' in text):
            dispute_info['type'] = '工资拖欠'
        elif '工伤' in text:
            dispute_info['type'] = '工伤赔偿'
        elif '加班费' in text:
            dispute_info['type'] = '加班费争议'
        else:
            dispute_info['type'] = '劳动争议'
        
        # 提取辞退理由
        reason_patterns = [
            r'理由是(.+?)(?:[。，\n]|$)',
            r'以(.+?)为由',
            r'说我(.+?)(?:[。，\n]|$)'
        ]
        
        for pattern in reason_patterns:
            match = re.search(pattern, text)
            if match:
                reason = match.group(1).strip()
                if '不能胜任' in reason:
                    dispute_info['reason_given'] = '不能胜任岗位'
                else:
                    dispute_info['reason_given'] = reason
                break
        
        # 提取通知日期
        notice_patterns = [
            r'(\d{1,2})月(\d{1,2})日收到',
            r'收到.*?(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{1,2})-(\d{1,2}).*?通知'
        ]
        
        for pattern in notice_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:  # 只有月日
                    month, day = groups
                    year = "2024"  # 默认年份
                    dispute_info['notice_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                elif len(groups) == 3:  # 年月日
                    year, month, day = groups
                    dispute_info['notice_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                break
        
        # 检查是否有培训
        if '没有.*?培训' in text or '未.*?培训' in text:
            dispute_info['has_training'] = False
        elif '培训' in text:
            dispute_info['has_training'] = True
        
        # 检查是否有调岗
        if '没有.*?调岗' in text or '未.*?调岗' in text:
            dispute_info['has_transfer'] = False
        elif '调岗' in text:
            dispute_info['has_transfer'] = True
        
        # 检查公司是否有证据
        if '没有.*?证据' in text or '拿不出.*?证据' in text:
            dispute_info['has_evidence'] = False
        elif '有证据' in text:
            dispute_info['has_evidence'] = True
        
        # 提取绩效评级
        if '优秀' in text:
            dispute_info['performance_rating'] = '优秀'
        elif '良好' in text:
            dispute_info['performance_rating'] = '良好'
        elif '合格' in text:
            dispute_info['performance_rating'] = '合格'
        elif '不合格' in text:
            dispute_info['performance_rating'] = '不合格'
        
        return dispute_info
    
    def _extract_evidence_status(self, text: str) -> Dict[str, str]:
        """提取证据状态
        
        Args:
            text: 对话文本
            
        Returns:
            证据状态字典
        """
        evidence_status = {
            'contract': '未收集',
            'payslip': '未收集',
            'termination_notice': '未收集',
            'performance_review': '未收集',
            'attendance_record': '未收集',
            'social_insurance': '未收集'
        }
        
        # 检查劳动合同
        if '签过.*?合同' in text or '有.*?合同' in text:
            evidence_status['contract'] = '已收集'
        
        # 检查解除通知书
        if '书面.*?通知' in text or '解除.*?通知书' in text:
            evidence_status['termination_notice'] = '已收集'
        
        # 检查绩效考核
        if '绩效.*?优秀' in text or '考核.*?优秀' in text:
            evidence_status['performance_review'] = '已收集'
        
        # 检查社保
        if '正常缴纳' in text and '社保' in text:
            evidence_status['social_insurance'] = '已收集'
        
        return evidence_status
    
    def _validate_case_info(self, case_info: Dict[str, Any]) -> None:
        """验证案件信息完整性
        
        Args:
            case_info: 案件信息字典
            
        Raises:
            DataParseError: 数据验证失败
        """
        required_fields = ['basic_info', 'dispute_info', 'evidence_status']
        
        for field in required_fields:
            if field not in case_info:
                raise DataParseError(f"缺少必要字段: {field}")
        
        # 检查基本信息
        basic_info = case_info['basic_info']
        if not basic_info.get('company_name'):
            print("警告：未能提取公司名称")
        
        if not basic_info.get('monthly_salary'):
            print("警告：未能提取月薪信息")
        
        # 检查争议信息
        dispute_info = case_info['dispute_info']
        if not dispute_info.get('type'):
            print("警告：未能确定争议类型")
    
    def generate_case_summary(self, case_info: Dict[str, Any]) -> str:
        """生成案件摘要
        
        Args:
            case_info: 案件信息字典
            
        Returns:
            案件摘要文本
        """
        try:
            basic_info = case_info.get('basic_info', {})
            dispute_info = case_info.get('dispute_info', {})
            evidence_status = case_info.get('evidence_status', {})
            
            # 构建摘要
            summary_parts = []
            
            # 基本信息
            company_name = basic_info.get('company_name', '某公司')
            employee_name = basic_info.get('employee_name', '当事人')
            monthly_salary = basic_info.get('monthly_salary', '未知')
            hire_date = basic_info.get('hire_date', '未知')
            termination_date = basic_info.get('termination_date', '未知')
            
            summary_parts.append(f"案件概况：{employee_name}与{company_name}劳动争议案")
            
            if hire_date != '未知':
                summary_parts.append(f"入职时间：{hire_date}")
            
            if termination_date != '未知':
                summary_parts.append(f"解除时间：{termination_date}")
            
            if monthly_salary != '未知':
                summary_parts.append(f"月薪：{monthly_salary}元")
            
            # 争议信息
            dispute_type = dispute_info.get('type', '劳动争议')
            reason_given = dispute_info.get('reason_given', '未知')
            notice_date = dispute_info.get('notice_date', '未知')
            
            summary_parts.append(f"争议类型：{dispute_type}")
            
            if reason_given != '未知':
                summary_parts.append(f"公司给出理由：{reason_given}")
            
            if notice_date != '未知':
                summary_parts.append(f"通知日期：{notice_date}")
            
            # 关键事实
            facts = []
            if not dispute_info.get('has_training', False):
                facts.append("公司未提供培训")
            
            if not dispute_info.get('has_transfer', False):
                facts.append("公司未安排调岗")
            
            if not dispute_info.get('has_evidence', False):
                facts.append("公司无法提供不胜任证据")
            
            performance_rating = dispute_info.get('performance_rating')
            if performance_rating:
                facts.append(f"员工绩效评级：{performance_rating}")
            
            if facts:
                summary_parts.append(f"关键事实：{'; '.join(facts)}")
            
            # 现有证据
            collected_evidence = []
            for evidence_type, status in evidence_status.items():
                if status == '已收集':
                    evidence_names = {
                        'contract': '劳动合同',
                        'payslip': '工资单',
                        'termination_notice': '解除通知书',
                        'performance_review': '绩效考核',
                        'attendance_record': '考勤记录',
                        'social_insurance': '社保记录'
                    }
                    collected_evidence.append(evidence_names.get(evidence_type, evidence_type))
            
            if collected_evidence:
                summary_parts.append(f"已有证据：{', '.join(collected_evidence)}")
            
            return '\n'.join(summary_parts)
            
        except Exception as e:
            return f"生成案件摘要失败: {e}"
    
    def get_case_timeline(self, case_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """获取案件时间线
        
        Args:
            case_info: 案件信息字典
            
        Returns:
            时间线事件列表
        """
        timeline = []
        
        basic_info = case_info.get('basic_info', {})
        dispute_info = case_info.get('dispute_info', {})
        
        # 入职时间
        hire_date = basic_info.get('hire_date')
        if hire_date:
            timeline.append({
                'date': hire_date,
                'event': '入职',
                'description': f"入职{basic_info.get('company_name', '公司')}"
            })
        
        # 通知时间
        notice_date = dispute_info.get('notice_date')
        if notice_date:
            timeline.append({
                'date': notice_date,
                'event': '收到解除通知',
                'description': f"收到解除劳动合同通知书，理由：{dispute_info.get('reason_given', '未知')}"
            })
        
        # 解除时间
        termination_date = basic_info.get('termination_date')
        if termination_date:
            timeline.append({
                'date': termination_date,
                'event': '劳动关系解除',
                'description': '劳动合同正式解除'
            })
        
        # 按日期排序
        timeline.sort(key=lambda x: x['date'])
        
        return timeline