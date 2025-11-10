#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证据清单生成模块

功能：
1. 调用Qwen-MAX模型分析案件
2. 生成标准化的证据需求清单
3. 按重要性和获取难度分类证据
4. 提供详细的收集指导
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from openai import OpenAI


class APICallError(Exception):
    """API调用错误"""
    pass


class EvidenceGenerator:
    """证据清单生成器"""
    
    def __init__(self):
        """初始化生成器"""
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
    
    def generate_evidence_list(self, case_summary: str, case_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生成证据清单
        
        Args:
            case_summary: 案件摘要
            case_info: 案件信息字典
            
        Returns:
            证据清单字典，失败返回None
        """
        if not self.client:
            print("错误：Qwen客户端未初始化")
            return None
        
        try:
            # 构建专业的法律分析prompt
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(case_summary, case_info)
            
            # 调用Qwen-MAX模型
            completion = self.client.chat.completions.create(
                model="qwen-max-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                extra_body={"enable_thinking": False},
            )
            
            # 解析模型响应
            response_content = completion.choices[0].message.content
            evidence_list = self._parse_model_response(response_content, case_info)
            
            return evidence_list
            
        except Exception as e:
            print(f"生成证据清单失败: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词
        
        Returns:
            系统提示词
        """
        return """
你是一位专业的劳动法律师，拥有丰富的劳动争议仲裁经验。你的任务是根据案件信息生成完整、专业的证据清单。

你需要：
1. 深入分析案件的争议焦点和法律关系
2. 根据《劳动法》、《劳动合同法》等相关法律法规，确定所需证据
3. 按照证据的重要性（核心、重要、辅助）进行分类
4. 为每项证据提供具体的收集方法和法律依据
5. 考虑证据的可获得性和证明力

证据分类标准：
- 核心证据：直接证明争议事实的关键证据，缺少将严重影响案件结果
- 重要证据：支持主要争议事实的重要证据，有助于加强案件说服力
- 辅助证据：补充说明相关情况的证据，起到佐证作用

请确保生成的证据清单：
- 完整覆盖案件争议焦点
- 符合法律证据要求
- 具有实际可操作性
- 提供明确的法律依据
"""
    
    def _build_user_prompt(self, case_summary: str, case_info: Dict[str, Any]) -> str:
        """构建用户提示词
        
        Args:
            case_summary: 案件摘要
            case_info: 案件信息
            
        Returns:
            用户提示词
        """
        dispute_type = case_info.get('dispute_info', {}).get('type', '劳动争议')
        
        prompt = f"""
请基于以下案件信息生成完整的仲裁证据清单：

【案件摘要】
{case_summary}

【争议类型】
{dispute_type}

【具体要求】
请生成JSON格式的证据清单，包含以下字段：
- evidence_items: 证据项目列表
  - id: 证据唯一标识
  - type: 证据类型（如：劳动合同、工资单、解除通知书等）
  - importance: 重要性（核心/重要/辅助）
  - description: 证据描述
  - collection_method: 收集方法
  - legal_basis: 法律依据
  - difficulty: 获取难度（容易/中等/困难）
  - notes: 特别注意事项

请确保证据清单针对{dispute_type}案件的特点，覆盖所有必要的证据类型。
"""
        
        return prompt
    
    def _parse_model_response(self, response_content: str, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """解析模型响应
        
        Args:
            response_content: 模型响应内容
            case_info: 案件信息
            
        Returns:
            解析后的证据清单
        """
        try:
            # 尝试从响应中提取JSON
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_content[json_start:json_end]
                evidence_data = json.loads(json_str)
            else:
                # 如果没有找到JSON，使用文本解析
                evidence_data = self._parse_text_response(response_content)
            
            # 标准化证据清单格式
            standardized_list = self._standardize_evidence_list(evidence_data, case_info)
            
            return standardized_list
            
        except json.JSONDecodeError:
            # JSON解析失败，尝试文本解析
            return self._parse_text_response(response_content, case_info)
        except Exception as e:
            print(f"解析模型响应失败: {e}")
            return self._create_default_evidence_list(case_info)
    
    def _parse_text_response(self, text: str, case_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """解析文本响应
        
        Args:
            text: 响应文本
            case_info: 案件信息
            
        Returns:
            解析后的证据清单
        """
        evidence_items = []
        
        # 基于争议类型生成默认证据清单
        if case_info:
            dispute_type = case_info.get('dispute_info', {}).get('type', '劳动争议')
            
            if '违法解除' in dispute_type:
                evidence_items = self._get_illegal_termination_evidence()
            elif '工资' in dispute_type:
                evidence_items = self._get_wage_dispute_evidence()
            elif '工伤' in dispute_type:
                evidence_items = self._get_injury_evidence()
            else:
                evidence_items = self._get_general_labor_evidence()
        
        return {
            'case_id': case_info.get('case_id') if case_info else None,
            'generated_at': datetime.now().isoformat(),
            'evidence_items': evidence_items
        }
    
    def _standardize_evidence_list(self, evidence_data: Dict[str, Any], case_info: Dict[str, Any]) -> Dict[str, Any]:
        """标准化证据清单格式
        
        Args:
            evidence_data: 原始证据数据
            case_info: 案件信息
            
        Returns:
            标准化的证据清单
        """
        standardized_items = []
        
        evidence_items = evidence_data.get('evidence_items', [])
        
        for i, item in enumerate(evidence_items):
            standardized_item = {
                'id': item.get('id', f'evidence_{str(uuid.uuid4())[:8]}'),
                'type': item.get('type', '未知证据'),
                'importance': item.get('importance', '重要'),
                'description': item.get('description', ''),
                'collection_method': item.get('collection_method', ''),
                'legal_basis': item.get('legal_basis', ''),
                'difficulty': item.get('difficulty', '中等'),
                'notes': item.get('notes', ''),
                'status': '未收集',
                'file_path': None,
                'analysis_result': None
            }
            standardized_items.append(standardized_item)
        
        return {
            'case_id': case_info.get('case_id'),
            'generated_at': datetime.now().isoformat(),
            'evidence_items': standardized_items
        }
    
    def _get_illegal_termination_evidence(self) -> List[Dict[str, Any]]:
        """获取违法解除劳动合同案件的证据清单
        
        Returns:
            证据项目列表
        """
        return [
            {
                'id': 'evidence_001',
                'type': '劳动合同',
                'importance': '核心',
                'description': '证明劳动关系存在的基础证据，包含工作岗位、薪资标准等关键信息',
                'collection_method': '从个人档案中获取合同副本，如无副本可要求公司提供或申请仲裁调取',
                'legal_basis': '《劳动合同法》第10条、第16条',
                'difficulty': '容易',
                'notes': '确保合同完整，包含双方签字盖章'
            },
            {
                'id': 'evidence_002',
                'type': '解除劳动合同通知书',
                'importance': '核心',
                'description': '公司解除劳动合同的正式通知，包含解除理由和日期',
                'collection_method': '保留公司发出的书面通知，包括邮件、微信等电子形式',
                'legal_basis': '《劳动合同法》第43条',
                'difficulty': '容易',
                'notes': '注意保存通知的完整性和真实性'
            },
            {
                'id': 'evidence_003',
                'type': '工资单/银行流水',
                'importance': '核心',
                'description': '证明实际工资水平，用于计算经济补偿金和赔偿金',
                'collection_method': '收集近12个月的工资单或银行转账记录',
                'legal_basis': '《劳动合同法》第47条',
                'difficulty': '容易',
                'notes': '工资单应包含基本工资、奖金、津贴等各项收入'
            },
            {
                'id': 'evidence_004',
                'type': '绩效考核记录',
                'importance': '重要',
                'description': '证明工作表现，反驳"不能胜任工作"的理由',
                'collection_method': '收集考核表、评价邮件、奖励证书等材料',
                'legal_basis': '《劳动合同法》第40条',
                'difficulty': '中等',
                'notes': '重点收集近期的优秀评价记录'
            },
            {
                'id': 'evidence_005',
                'type': '培训记录',
                'importance': '重要',
                'description': '证明公司是否履行培训义务，是否给予改进机会',
                'collection_method': '收集培训通知、培训材料、培训证书等',
                'legal_basis': '《劳动合同法》第40条',
                'difficulty': '困难',
                'notes': '如无培训记录，可作为公司违法解除的证据'
            },
            {
                'id': 'evidence_006',
                'type': '调岗记录',
                'importance': '重要',
                'description': '证明公司是否提供其他合适岗位',
                'collection_method': '收集调岗通知、岗位变更文件等',
                'legal_basis': '《劳动合同法》第40条',
                'difficulty': '困难',
                'notes': '如无调岗安排，可作为程序违法的证据'
            },
            {
                'id': 'evidence_007',
                'type': '社保缴费记录',
                'importance': '辅助',
                'description': '证明劳动关系存续期间和工资基数',
                'collection_method': '到社保局打印缴费明细或通过网上查询打印',
                'legal_basis': '《社会保险法》第4条',
                'difficulty': '容易',
                'notes': '可作为劳动关系和工资水平的辅助证明'
            },
            {
                'id': 'evidence_008',
                'type': '工作成果/邮件记录',
                'importance': '辅助',
                'description': '证明实际工作表现和能力',
                'collection_method': '收集工作邮件、项目文档、客户好评等',
                'legal_basis': '《劳动争议调解仲裁法》第6条',
                'difficulty': '中等',
                'notes': '选择能体现工作能力的代表性材料'
            }
        ]
    
    def _get_wage_dispute_evidence(self) -> List[Dict[str, Any]]:
        """获取工资争议案件的证据清单
        
        Returns:
            证据项目列表
        """
        return [
            {
                'id': 'evidence_001',
                'type': '劳动合同',
                'importance': '核心',
                'description': '证明约定的工资标准和支付方式',
                'collection_method': '从个人档案中获取合同副本',
                'legal_basis': '《劳动合同法》第17条',
                'difficulty': '容易',
                'notes': '重点关注工资条款'
            },
            {
                'id': 'evidence_002',
                'type': '工资单',
                'importance': '核心',
                'description': '证明实际发放的工资数额',
                'collection_method': '收集所有期间的工资单',
                'legal_basis': '《工资支付暂行规定》第6条',
                'difficulty': '容易',
                'notes': '注意工资单的完整性'
            },
            {
                'id': 'evidence_003',
                'type': '银行流水',
                'importance': '核心',
                'description': '证明实际到账的工资金额',
                'collection_method': '到银行打印工资卡流水',
                'legal_basis': '《劳动争议调解仲裁法》第6条',
                'difficulty': '容易',
                'notes': '标注工资发放记录'
            },
            {
                'id': 'evidence_004',
                'type': '考勤记录',
                'importance': '重要',
                'description': '证明实际工作时间，计算加班费',
                'collection_method': '申请仲裁调取或要求公司提供',
                'legal_basis': '《劳动法》第44条',
                'difficulty': '困难',
                'notes': '重点关注超时工作记录'
            }
        ]
    
    def _get_injury_evidence(self) -> List[Dict[str, Any]]:
        """获取工伤案件的证据清单
        
        Returns:
            证据项目列表
        """
        return [
            {
                'id': 'evidence_001',
                'type': '工伤认定书',
                'importance': '核心',
                'description': '人社部门出具的工伤认定决定书',
                'collection_method': '向人社部门申请工伤认定',
                'legal_basis': '《工伤保险条例》第17条',
                'difficulty': '中等',
                'notes': '工伤赔偿的前提条件'
            },
            {
                'id': 'evidence_002',
                'type': '劳动能力鉴定书',
                'importance': '核心',
                'description': '确定伤残等级的鉴定结论',
                'collection_method': '向劳动能力鉴定委员会申请鉴定',
                'legal_basis': '《工伤保险条例》第21条',
                'difficulty': '中等',
                'notes': '影响赔偿金额的关键证据'
            },
            {
                'id': 'evidence_003',
                'type': '医疗费票据',
                'importance': '核心',
                'description': '治疗工伤产生的医疗费用凭证',
                'collection_method': '收集所有相关医疗费用发票',
                'legal_basis': '《工伤保险条例》第30条',
                'difficulty': '容易',
                'notes': '保留所有医疗相关费用凭证'
            }
        ]
    
    def _get_general_labor_evidence(self) -> List[Dict[str, Any]]:
        """获取一般劳动争议案件的证据清单
        
        Returns:
            证据项目列表
        """
        return [
            {
                'id': 'evidence_001',
                'type': '劳动合同',
                'importance': '核心',
                'description': '证明劳动关系的基础证据',
                'collection_method': '从个人档案中获取合同副本',
                'legal_basis': '《劳动合同法》第10条',
                'difficulty': '容易',
                'notes': '劳动争议的基础证据'
            },
            {
                'id': 'evidence_002',
                'type': '工资单',
                'importance': '重要',
                'description': '证明工资标准和发放情况',
                'collection_method': '收集工资单或银行流水',
                'legal_basis': '《工资支付暂行规定》第6条',
                'difficulty': '容易',
                'notes': '计算经济补偿的依据'
            },
            {
                'id': 'evidence_003',
                'type': '社保记录',
                'importance': '辅助',
                'description': '证明劳动关系存续期间',
                'collection_method': '到社保局查询打印',
                'legal_basis': '《社会保险法》第4条',
                'difficulty': '容易',
                'notes': '辅助证明劳动关系'
            }
        ]
    
    def _create_default_evidence_list(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """创建默认证据清单
        
        Args:
            case_info: 案件信息
            
        Returns:
            默认证据清单
        """
        dispute_type = case_info.get('dispute_info', {}).get('type', '劳动争议')
        
        if '违法解除' in dispute_type:
            evidence_items = self._get_illegal_termination_evidence()
        else:
            evidence_items = self._get_general_labor_evidence()
        
        return {
            'case_id': case_info.get('case_id'),
            'generated_at': datetime.now().isoformat(),
            'evidence_items': evidence_items
        }
    
    def get_evidence_by_importance(self, evidence_list: Dict[str, Any], importance: str) -> List[Dict[str, Any]]:
        """按重要性筛选证据
        
        Args:
            evidence_list: 证据清单
            importance: 重要性级别（核心/重要/辅助）
            
        Returns:
            筛选后的证据列表
        """
        evidence_items = evidence_list.get('evidence_items', [])
        return [item for item in evidence_items if item.get('importance') == importance]
    
    def get_evidence_by_difficulty(self, evidence_list: Dict[str, Any], difficulty: str) -> List[Dict[str, Any]]:
        """按获取难度筛选证据
        
        Args:
            evidence_list: 证据清单
            difficulty: 难度级别（容易/中等/困难）
            
        Returns:
            筛选后的证据列表
        """
        evidence_items = evidence_list.get('evidence_items', [])
        return [item for item in evidence_items if item.get('difficulty') == difficulty]
    
    def get_evidence_statistics(self, evidence_list: Dict[str, Any]) -> Dict[str, int]:
        """获取证据统计信息
        
        Args:
            evidence_list: 证据清单
            
        Returns:
            统计信息字典
        """
        evidence_items = evidence_list.get('evidence_items', [])
        
        stats = {
            'total': len(evidence_items),
            'core': 0,
            'important': 0,
            'auxiliary': 0,
            'easy': 0,
            'medium': 0,
            'difficult': 0
        }
        
        for item in evidence_items:
            importance = item.get('importance', '')
            difficulty = item.get('difficulty', '')
            
            if importance == '核心':
                stats['core'] += 1
            elif importance == '重要':
                stats['important'] += 1
            elif importance == '辅助':
                stats['auxiliary'] += 1
            
            if difficulty == '容易':
                stats['easy'] += 1
            elif difficulty == '中等':
                stats['medium'] += 1
            elif difficulty == '困难':
                stats['difficult'] += 1
        
        return stats