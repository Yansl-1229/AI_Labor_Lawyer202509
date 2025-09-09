#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证据分析系统
用于分析法律案件证据并生成结构化报告
"""

import json
import os
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import requests
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
import time
import logging

class EvidenceType(Enum):
    """证据类型枚举"""
    CONTRACT = "contract"  # 合同类文件
    PAYMENT = "payment"   # 薪资记录
    ATTENDANCE = "attendance"  # 考勤数据
    MEDICAL = "medical"   # 工伤材料
    MEDIA = "media"       # 音视频
    CHAT = "chat"         # 聊天记录

@dataclass
class APIConfig:
    """API配置数据结构"""
    url: str
    method: str = "POST"
    file_param: str = "file"
    additional_params: Dict[str, str] = None
    
    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}

@dataclass
class EvidenceItem:
    """证据项数据结构"""
    evidence_type: EvidenceType
    description: str
    keywords: List[str]
    required: bool = True
    file_path: Optional[str] = None
    analysis_result: Optional[Dict] = None

class EvidenceAnalyzer:
    """证据分析器主类"""
    
    def __init__(self, openai_api_key: Optional[str] = None, api_config_file: str = "接口说明.txt"):
        """
        初始化证据分析器
        
        Args:
            openai_api_key: OpenAI API密钥
            api_config_file: API配置文件路径
        """
        self.openai_base_url = "https://ark.cn-beijing.volces.com/api/v3"
        self.openai_client = OpenAI(
            api_key=openai_api_key or "1b4bef68-37d5-4196-ba8b-17c9054ae9c5",
            base_url=self.openai_base_url
        )
        self.evidence_patterns = self._init_evidence_patterns()
        self.api_config_file = api_config_file
        
        # 设置日志（必须在_load_api_configs之前）
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.api_configs = self._load_api_configs()
        
    def _init_evidence_patterns(self) -> Dict[EvidenceType, Dict[str, List[str]]]:
        """初始化证据识别模式"""
        return {
            EvidenceType.CONTRACT: {
                "keywords": ["劳动合同", "辞退通知书", "竞业协议", "实习合同", "竞业协议", "通知书"],
                "descriptions": ["书面劳动合同", "辞退通知", "解除合同通知"]
            },
            EvidenceType.PAYMENT: {
                "keywords": ["银行流水", "工资单", "工资条"],
                "descriptions": ["工资银行流水", "薪资发放记录", "收入证明"]
            },
            EvidenceType.ATTENDANCE: {
                "keywords": ["考勤单", "打卡记录"],
                "descriptions": ["考勤打卡记录", "请假审批记录", "工作时间证明"]
            },
            EvidenceType.MEDICAL: {
                "keywords": ["工伤", "诊断书", "病历", "医疗"],
                "descriptions": ["工伤诊断证明", "医疗记录", "伤情鉴定"]
            },
            EvidenceType.MEDIA: {
                "keywords": ["录音", "录像", "通话记录"],
                "descriptions": ["录音证据", "视频资料", "通话记录"]
            },
            EvidenceType.CHAT: {
                "keywords": ["微信", "钉钉", "飞书", "聊天记录"],
                "descriptions": ["聊天记录截图", "工作群对话", "沟通记录"]
            }
        }
    
    def analyze_case_evidence(self, conversation_file_path: str, uploaded_files_info: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        分析案件证据的主函数
        
        Args:
            conversation_file_path: 对话历史文件路径
            uploaded_files_info: 前端上传的文件信息列表，格式为 [{'filename': str, 'filepath': str, 'evidence_type': str}]
            
        Returns:
            包含所有证据分析结果的综合报告
        """
        print("🔍 开始分析案件证据...")
        
        # 1. 解析对话历史
        conversation_data = self._load_conversation_history(conversation_file_path)
        if not conversation_data:
            return {"error": "无法加载对话历史文件"}
        
        # 2. 识别证据需求
        evidence_items = self._identify_evidence_from_conversation(conversation_data)
        print(f"📋 识别到 {len(evidence_items)} 类证据需求")
        print(evidence_items)
        
        # 3. 处理证据上传（Web版本或命令行版本）
        if uploaded_files_info:
            # Web版本：使用前端上传的文件信息
            uploaded_evidence = self._process_uploaded_files(evidence_items, uploaded_files_info)
        else:
            # 命令行版本：引导用户上传证据
            uploaded_evidence = self._guide_evidence_upload(evidence_items)
        
        # 4. 分析每个证据
        analysis_results = {}
        for evidence_type, evidence_list in uploaded_evidence.items():
            for evidence in evidence_list:
                if evidence.file_path:
                    print(f"🔬 正在分析 {evidence.description} ({evidence_type.value} 类证据)...")
                    analysis_result = self._analyze_single_evidence(evidence)
                    evidence.analysis_result = analysis_result
                    
                    # 为每个具体的证据创建唯一的分析键
                    analysis_key = f"{evidence_type.value}_{evidence.description}_analysis"
                    if analysis_key not in analysis_results:
                        analysis_results[analysis_key] = []
                    analysis_results[analysis_key].append(analysis_result)
                    print(f"✅ {evidence.description} 分析完成")
        
        # 5. 生成综合报告
        comprehensive_report = self._generate_comprehensive_report(
            evidence_items, analysis_results, conversation_data
        )
        
        # 6. 保存报告
        report_file = self._save_report(comprehensive_report)
        print(f"📄 分析报告已保存至: {report_file}")
        
        return comprehensive_report
    
    def _load_conversation_history(self, file_path: str) -> Optional[List[Dict]]:
        """加载对话历史文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get('conversations', [])
                return data
        except Exception as e:
            print(f"❌ 加载对话历史失败: {e}")
            return None
    
    def _identify_evidence_from_conversation(self, conversations: List[Dict]) -> Dict[EvidenceType, List[EvidenceItem]]:
        """从对话中识别证据需求"""
        evidence_items = {evidence_type: [] for evidence_type in EvidenceType}
        
        # 合并所有对话内容
        full_text = ""
        for conv in conversations:
            if conv.get('value'):
                full_text += conv['value'] + " "
        
        # 使用关键词匹配识别证据类型，为每个关键词创建独立的证据项
        for evidence_type, patterns in self.evidence_patterns.items():
            found_keywords = []
            for keyword in patterns['keywords']:
                if keyword in full_text:
                    found_keywords.append(keyword)
            
            # 为每个找到的关键词创建独立的证据项
            for keyword in found_keywords:
                evidence_item = EvidenceItem(
                    evidence_type=evidence_type,
                    description=f"{keyword}",  # 使用具体的关键词作为描述
                    keywords=[keyword],  # 每个证据项只包含一个关键词
                    required=True
                )
                evidence_items[evidence_type].append(evidence_item)
        
        return evidence_items
    
    def _process_uploaded_files(self, evidence_items: Dict[EvidenceType, List[EvidenceItem]], uploaded_files_info: List[Dict]) -> Dict[EvidenceType, List[EvidenceItem]]:
        """
        处理前端上传的文件信息
        
        Args:
            evidence_items: 识别到的证据需求
            uploaded_files_info: 前端上传的文件信息列表
            
        Returns:
            包含文件路径的证据项字典
        """
        print("\n📤 处理前端上传的证据文件...")
        uploaded_evidence = {}
        
        # 创建文件名到证据类型的映射
        evidence_type_mapping = {
            '合同': EvidenceType.CONTRACT,
            '劳动合同': EvidenceType.CONTRACT,
            '工资': EvidenceType.PAYMENT,
            '银行流水': EvidenceType.PAYMENT,
            '工资单': EvidenceType.PAYMENT,
            '考勤': EvidenceType.ATTENDANCE,
            '打卡记录': EvidenceType.ATTENDANCE,
            '录音': EvidenceType.MEDIA,
            '视频': EvidenceType.MEDIA,
            '聊天记录': EvidenceType.CHAT,
            '微信': EvidenceType.CHAT
        }
        
        for file_info in uploaded_files_info:
            filename = file_info.get('filename', '')
            filepath = file_info.get('filepath', '')
            
            if not filepath or not os.path.exists(filepath):
                print(f"❌ 文件不存在或路径无效: {filepath}")
                continue
                
            # 根据文件名推断证据类型
            detected_type = None
            for keyword, evidence_type in evidence_type_mapping.items():
                if keyword in filename:
                    detected_type = evidence_type
                    break
            
            if not detected_type:
                # 默认为合同类型
                detected_type = EvidenceType.CONTRACT
                print(f"⚠️ 无法识别文件类型，默认为合同类: {filename}")
            
            # 查找匹配的证据项
            if detected_type in evidence_items and evidence_items[detected_type]:
                # 使用第一个匹配的证据项
                evidence_item = evidence_items[detected_type][0]
                evidence_item.file_path = filepath
                
                if detected_type not in uploaded_evidence:
                    uploaded_evidence[detected_type] = []
                uploaded_evidence[detected_type].append(evidence_item)
                
                print(f"✅ 文件已关联: {filename} -> {self._get_evidence_type_name(detected_type)}")
            else:
                # 创建新的证据项
                evidence_item = EvidenceItem(
                    evidence_type=detected_type,
                    description=filename,
                    keywords=[filename],
                    required=True,
                    file_path=filepath
                )
                
                if detected_type not in uploaded_evidence:
                    uploaded_evidence[detected_type] = []
                uploaded_evidence[detected_type].append(evidence_item)
                
                print(f"✅ 新建证据项: {filename} -> {self._get_evidence_type_name(detected_type)}")
        
        print(f"📋 共处理 {len(uploaded_files_info)} 个上传文件")
        return uploaded_evidence
    
    def _guide_evidence_upload(self, evidence_items: Dict[EvidenceType, List[EvidenceItem]]) -> Dict[EvidenceType, List[EvidenceItem]]:
        """引导用户上传证据文件"""
        print("\n📤 请按照提示上传相关证据文件：")
        print("=" * 50)
        print("💡 提示：现在可以为每种具体的证据类型单独上传文件")
        print("   例如：劳动合同、辞退通知书可以分别上传不同的文件")
        print()
        
        uploaded_evidence = {}
        
        for evidence_type, items in evidence_items.items():
            if not items:
                continue
                
            uploaded_evidence[evidence_type] = []
            
            print(f"\n📁 {self._get_evidence_type_name(evidence_type)} 类证据:")
            
            for i, item in enumerate(items, 1):
                print(f"  {i}. 📄 {item.description}")
                print(f"     📝 说明: 请上传与'{item.description}'相关的文件")
                
                # 模拟用户上传（实际应用中这里应该是文件上传界面）
                file_path = input(f"     📂 请输入文件路径 (回车跳过): ").strip()
                
                if file_path and os.path.exists(file_path):
                    item.file_path = file_path
                    uploaded_evidence[evidence_type].append(item)
                    print(f"     ✅ 文件上传成功: {file_path}")
                    print(f"     📋 将分析: {item.description}")
                elif file_path:
                    print(f"     ❌ 文件不存在: {file_path}")
                    print(f"     💡 请检查文件路径是否正确")
                else:
                    print(f"     ⏭️ 跳过 {item.description}")
                print()  # 添加空行分隔
        
        return uploaded_evidence
    
    def _analyze_single_evidence(self, evidence: EvidenceItem) -> Dict[str, Any]:
        """分析单个证据文件"""
        self.logger.info(f"开始分析 {evidence.evidence_type.value} 类型的证据文件: {evidence.file_path}")
        
        # 获取模拟分析结果作为备用
        mock_analysis = self._get_mock_analysis_result(evidence)
        
        # 尝试调用对应的API
        if self.api_configs and evidence.evidence_type in self.api_configs:
            try:
                api_result = self._call_evidence_api(evidence)
                
                if api_result:
                    self.logger.info(f"✅ 使用API分析结果: {evidence.evidence_type.value}")
                    return api_result
                else:
                    self.logger.warning(f"⚠️ API调用失败，自动切换到模拟分析结果: {evidence.evidence_type.value}")
                    return mock_analysis
            except Exception as e:
                self.logger.error(f"❌ API调用过程中发生异常: {e}，使用模拟分析结果")
                return mock_analysis
        else:
            self.logger.info(f"📝 未配置API或API类型不匹配，使用模拟分析结果: {evidence.evidence_type.value}")
            return mock_analysis
    
    def _get_mock_analysis_result(self, evidence: EvidenceItem) -> Dict[str, Any]:
        """获取模拟的分析结果"""
        base_result = {
            "文件类型": self._get_evidence_type_name(evidence.evidence_type),
            "文件有效性说明": "文件格式正确，内容清晰可读。",
            "与案件关联性分析": "与本案件具有直接关联性。",
            "是否可以作为核心证据": "是"
        }
        
        # 根据证据类型添加特定字段
        if evidence.evidence_type == EvidenceType.CONTRACT:
            base_result.update({
                "主体公司名称": "XX科技有限公司",
                "合同起始日期": "2022年09月01日",
                "合同有效期": "3年",
                "约定薪资": "12000元/月",
                "关键信息摘要": "合同约定工作年限3年，月薪12000元，包含试用期条款。"
            })
        elif evidence.evidence_type == EvidenceType.PAYMENT:
            base_result.update({
                "工资发放方式": "银行转账",
                "发放周期": "每月15日",
                "平均月薪": "12000元",
                "关键信息摘要": "银行流水显示每月15日定期收到工资转账，金额稳定。"
            })
        elif evidence.evidence_type == EvidenceType.ATTENDANCE:
            base_result.update({
                "考勤方式": "打卡系统",
                "工作时间": "9:00-18:00",
                "关键信息摘要": "考勤记录显示正常上下班打卡，存在管理关系。"
            })
        elif evidence.evidence_type == EvidenceType.MEDIA:
            base_result.update({
                "关键内容摘要（文字稿）": "录音中包含关键对话内容，证明相关事实。",
                "是否可以作为核心证据": "否，建议作为辅助证据"
            })
        elif evidence.evidence_type == EvidenceType.CHAT:
            base_result.update({
                "聊天平台": "微信",
                "关键信息摘要": "聊天记录显示工作安排和沟通内容。"
            })
        
        return base_result
    
    def _generate_comprehensive_report(self, evidence_items: Dict, analysis_results: Dict, conversation_data: List) -> Dict[str, Any]:
        """生成综合分析报告"""
        print("\n📊 正在生成综合分析报告...")
        
        # 使用LLM生成总结
        summary = self._generate_llm_summary(analysis_results, conversation_data)
        
        # 分类证据
        core_evidence = []
        supporting_evidence = []
        
        for analysis_type, results in analysis_results.items():
            for result in results:
                if result.get("是否可以作为核心证据") == "是":
                    core_evidence.append({
                        "类型": result.get("文件类型", "未知"),
                        "摘要": result.get("关键信息摘要", "无摘要")
                    })
                else:
                    supporting_evidence.append({
                        "类型": result.get("文件类型", "未知"),
                        "摘要": result.get("关键信息摘要", "无摘要")
                    })
        
        comprehensive_report = {
            "报告生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "案件概述": self._extract_case_summary(conversation_data),
            "证据分析结果": analysis_results,
            "核心证据列表": core_evidence,
            "辅助证据列表": supporting_evidence,
            "LLM综合分析": summary,
            "证据完整性评估": self._assess_evidence_completeness(evidence_items, analysis_results),
            "建议和风险提示": self._generate_recommendations(analysis_results)
        }
        
        return comprehensive_report
    
    def _generate_llm_summary(self, analysis_results: Dict, conversation_data: List) -> str:
        """使用LLM生成分析总结"""
        try:
            # 构建提示词
            prompt = f"""
            请基于以下证据分析结果和案件对话，生成一份专业的法律证据分析总结：
            
            证据分析结果：
            {json.dumps(analysis_results, ensure_ascii=False, indent=2)}
            
            请从以下角度进行分析：
            1. 证据的完整性和有效性
            2. 各类证据之间的关联性
            3. 对案件胜诉的支持程度
            4. 可能存在的证据缺陷或风险
            5. 补强证据的建议
            
            请用专业但易懂的语言撰写，字数控制在500字以内。
            """
            
            response = self.openai_client.chat.completions.create(
                model="doubao-seed-1-6-250615",
                messages=[
                    {"role": "system", "content": "你是一位专业的劳动法律师，擅长证据分析和案件评估。"},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM分析失败: {e}")
            return "基于现有证据，案件具有一定的胜诉可能性。建议进一步完善证据链，特别是关键证据的补强。"
    
    def _extract_case_summary(self, conversation_data: List) -> str:
        """从对话中提取案件概述"""
        # 简单提取前几轮对话作为案件概述
        summary_parts = []
        for i, conv in enumerate(conversation_data[:6]):  # 取前6轮对话
            if conv.get('from') == 'human' and conv.get('value'):
                summary_parts.append(conv['value'][:100])  # 每条限制100字符
        
        return " ".join(summary_parts)[:300] + "..." if summary_parts else "无法提取案件概述"
    
    def _assess_evidence_completeness(self, evidence_items: Dict, analysis_results: Dict) -> Dict[str, Any]:
        """评估证据完整性"""
        total_types = len([t for t, items in evidence_items.items() if items])
        analyzed_types = len(analysis_results)
        
        completeness_score = (analyzed_types / total_types * 100) if total_types > 0 else 0
        
        return {
            "完整性得分": f"{completeness_score:.1f}%",
            "已收集证据类型": analyzed_types,
            "识别证据类型总数": total_types,
            "缺失证据类型": [t.value for t, items in evidence_items.items() if items and f"{t.value}_analysis" not in analysis_results]
        }
    
    def _generate_recommendations(self, analysis_results: Dict) -> List[str]:
        """生成建议和风险提示"""
        recommendations = []
        
        # 基于分析结果生成建议
        if "contract_analysis" in analysis_results:
            recommendations.append("✅ 劳动合同证据充分，有利于证明劳动关系。")
        else:
            recommendations.append("⚠️ 建议补充劳动合同相关证据。")
        
        if "payment_analysis" in analysis_results:
            recommendations.append("✅ 工资流水证据有助于确定经济补偿标准。")
        else:
            recommendations.append("⚠️ 建议提供工资发放记录以支持经济补偿请求。")
        
        if "media_analysis" in analysis_results:
            recommendations.append("⚠️ 音视频证据需注意取证合法性，建议作为辅助证据使用。")
        
        recommendations.append("💡 建议咨询专业律师进行详细的案件评估。")
        
        return recommendations
    
    def _get_evidence_type_name(self, evidence_type: EvidenceType) -> str:
        """获取证据类型中文名称"""
        type_names = {
            EvidenceType.CONTRACT: "合同类文件",
            EvidenceType.PAYMENT: "薪资记录",
            EvidenceType.ATTENDANCE: "考勤数据",
            EvidenceType.MEDICAL: "医疗材料",
            EvidenceType.MEDIA: "音视频证据",
            EvidenceType.CHAT: "聊天记录"
        }
        return type_names.get(evidence_type, "未知类型")
    
    def _load_api_configs(self) -> Dict[EvidenceType, APIConfig]:
        """从配置文件加载API配置信息"""
        api_configs = {}
        
        try:
            # 根据接口说明.txt的内容创建API配置映射
            api_configs = {
                EvidenceType.CONTRACT: APIConfig(
                    url="http://localhost:8001/analyze_contract",
                    file_param="file"
                ),
                EvidenceType.PAYMENT: APIConfig(
                    url="http://localhost:8002/analyze-payslip",
                    file_param="file"
                ),
                EvidenceType.ATTENDANCE: APIConfig(
                    url="http://localhost:8003/analyze_attendance",
                    file_param="attendance_file"
                ),
                EvidenceType.MEDICAL: APIConfig(
                    url="http://localhost:8004/analyze_injury_assessment",
                    file_param="attendance_file"  # 注意：接口文档中使用的是attendance_file参数名
                ),
                EvidenceType.MEDIA: APIConfig(
                    url="http://localhost:8005/analyze_recording",
                    file_param="Record_file"
                ),
                EvidenceType.CHAT: APIConfig(
                    url="http://localhost:8006/analyze_single",
                    file_param="file"
                )
            }
            
            self.logger.info(f"成功加载 {len(api_configs)} 个API配置")
            
        except Exception as e:
            self.logger.error(f"加载API配置失败: {e}")
            # 返回空配置，将使用模拟分析结果
            api_configs = {}
            
        return api_configs
    
    def _call_evidence_api(self, evidence: EvidenceItem, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """调用对应的证据分析API"""
        if evidence.evidence_type not in self.api_configs:
            self.logger.warning(f"未找到 {evidence.evidence_type.value} 类型的API配置")
            return None
            
        api_config = self.api_configs[evidence.evidence_type]
        
        # 检查文件是否存在和可读
        if not os.path.exists(evidence.file_path):
            self.logger.error(f"证据文件不存在: {evidence.file_path}")
            return None
            
        if not os.path.isfile(evidence.file_path):
            self.logger.error(f"证据路径不是文件: {evidence.file_path}")
            return None
            
        try:
            with open(evidence.file_path, 'rb') as test_file:
                test_file.read(1)  # 测试文件是否可读
        except Exception as e:
            self.logger.error(f"无法读取证据文件: {evidence.file_path}, 错误: {e}")
            return None
        
        # 检查API服务可用性
        if not self._check_api_availability(api_config.url):
            self.logger.warning(f"API服务不可用: {api_config.url}，将使用模拟分析结果")
            return None
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"正在调用API: {api_config.url} (尝试 {attempt + 1}/{max_retries})")
                self.logger.debug(f"文件路径: {evidence.file_path}")
                self.logger.debug(f"文件参数名: {api_config.file_param}")
                
                with open(evidence.file_path, 'rb') as f:
                    files = {api_config.file_param: f}
                    data = api_config.additional_params.copy()
                    
                    # 设置请求超时
                    response = requests.post(
                        api_config.url, 
                        files=files, 
                        data=data,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        self.logger.info(f"API调用成功: {api_config.url}")
                        return result
                    else:
                        # 记录详细的错误信息
                        self.logger.warning(f"API返回错误状态码: {response.status_code}")
                        self.logger.error(f"API响应内容: {response.text[:500]}...")  # 只记录前500字符
                        self.logger.error(f"请求URL: {api_config.url}")
                        self.logger.error(f"请求文件参数: {api_config.file_param}")
                        self.logger.error(f"请求数据参数: {data}")
                        
            except requests.exceptions.Timeout:
                self.logger.warning(f"API调用超时 (尝试 {attempt + 1}/{max_retries})")
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"API连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                self.logger.error(f"API调用异常: {e} (尝试 {attempt + 1}/{max_retries})")
                import traceback
                self.logger.debug(f"异常详情: {traceback.format_exc()}")
            
            # 重试前等待
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                self.logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        self.logger.error(f"API调用失败，已达到最大重试次数: {api_config.url}，将使用模拟分析结果")
        return None
    
    def _check_api_availability(self, api_url: str) -> bool:
        """检查API服务是否可用"""
        try:
            # 提取基础URL进行健康检查
            from urllib.parse import urlparse
            parsed_url = urlparse(api_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # 尝试连接到服务器
            response = requests.get(base_url, timeout=5)
            return True
        except requests.exceptions.ConnectionError:
            self.logger.debug(f"无法连接到API服务: {api_url}")
            return False
        except Exception as e:
            self.logger.debug(f"API可用性检查异常: {e}")
            return False
    
    def _save_report(self, report: Dict[str, Any]) -> str:
        """保存分析报告"""
        if not os.path.exists("evidence_reports"):
            os.makedirs("evidence_reports")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evidence_reports/evidence_analysis_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 同时生成可读性更好的文本报告
        text_filename = f"evidence_reports/evidence_analysis_report_{timestamp}.txt"
        self._save_text_report(report, text_filename)
        
        return filename
    
    def _save_text_report(self, report: Dict[str, Any], filename: str):
        """保存文本格式的报告"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("证据分析报告\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"报告生成时间: {report.get('报告生成时间', 'N/A')}\n\n")
            
            f.write("案件概述:\n")
            f.write("-" * 30 + "\n")
            f.write(f"{report.get('案件概述', 'N/A')}\n\n")
            
            f.write("核心证据列表:\n")
            f.write("-" * 30 + "\n")
            for i, evidence in enumerate(report.get('核心证据列表', []), 1):
                f.write(f"{i}. {evidence.get('类型', 'N/A')}: {evidence.get('摘要', 'N/A')}\n")
            f.write("\n")
            
            f.write("辅助证据列表:\n")
            f.write("-" * 30 + "\n")
            for i, evidence in enumerate(report.get('辅助证据列表', []), 1):
                f.write(f"{i}. {evidence.get('类型', 'N/A')}: {evidence.get('摘要', 'N/A')}\n")
            f.write("\n")
            
            f.write("LLM综合分析:\n")
            f.write("-" * 30 + "\n")
            f.write(f"{report.get('LLM综合分析', 'N/A')}\n\n")
            
            f.write("证据完整性评估:\n")
            f.write("-" * 30 + "\n")
            completeness = report.get('证据完整性评估', {})
            f.write(f"完整性得分: {completeness.get('完整性得分', 'N/A')}\n")
            f.write(f"已收集证据类型: {completeness.get('已收集证据类型', 'N/A')}\n")
            f.write(f"识别证据类型总数: {completeness.get('识别证据类型总数', 'N/A')}\n\n")
            
            f.write("建议和风险提示:\n")
            f.write("-" * 30 + "\n")
            for recommendation in report.get('建议和风险提示', []):
                f.write(f"• {recommendation}\n")


def main():
    """主函数 - 演示用法"""
    print("🏛️ 证据分析系统启动")
    print("=" * 50)
    
    # 初始化分析器
    analyzer = EvidenceAnalyzer()
    
    # 分析证据
    conversation_file = "d:/Code/HJY/AI lawyer full-featured demo/conversation_history_demo.json"
    
    if not os.path.exists(conversation_file):
        print(f"❌ 对话历史文件不存在: {conversation_file}")
        return
    
    try:
        result = analyzer.analyze_case_evidence(conversation_file)
        
        if "error" in result:
            print(f"❌ 分析失败: {result['error']}")
        else:
            print("\n✅ 证据分析完成！")
            print(f"📊 核心证据数量: {len(result.get('核心证据列表', []))}")
            print(f"📋 辅助证据数量: {len(result.get('辅助证据列表', []))}")
            print(f"📈 证据完整性: {result.get('证据完整性评估', {}).get('完整性得分', 'N/A')}")
            
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()