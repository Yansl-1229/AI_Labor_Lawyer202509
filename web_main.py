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
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
import shutil

# 导入三个核心模块
try:
    from lawyer_model import set_model_provider, get_current_provider, get_available_providers, get_model_info, update_model_config, chat_with_lawyer, create_new_conversation, save_conversation_to_json
    from free_generate_case_analysis import CaseAnalysisGenerator
    from evidence_analyzer import EvidenceAnalyzer
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请确保以下文件存在：")
    print("- lawyer_model.py")
    print("- free_generate_case_analysis.py")
    print("- evidence_analyzer.py")
    sys.exit(1)

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
        self.evidence_analysis_result = None
        
        # 初始化各个模块
        self._init_modules()
        
        # 创建会话目录
        self.session_dir = f"sessions/{self.session_id}"
        os.makedirs(self.session_dir, exist_ok=True)
        
        # 创建证据文件目录
        self.evidence_dir = os.path.join(self.session_dir, "evidence_files")
        os.makedirs(self.evidence_dir, exist_ok=True)
        
        # 存储上传的文件信息
        self.uploaded_files = []
    
    def _generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    def _init_modules(self):
        """初始化各个功能模块"""
        try:
            # 初始化案例分析生成器
            self.case_analyzer = CaseAnalysisGenerator()
            
            # 初始化证据分析器
            self.evidence_analyzer = EvidenceAnalyzer()
            
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
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入，返回律师回复"""
        try:
            if not user_input.strip():
                return {
                    "success": False,
                    "error": "请输入您的问题或回答..."
                }
            
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
                import json
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
                result["next_phase"] = "service_selection"
                result["next_phase_name"] = "服务选择阶段"
                result["message"] = "✅ 信息收集阶段完成，请选择服务类型"
            
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
                    "next_phase": "case_analysis",
                    "next_phase_name": "案例分析阶段"
                }
            elif service_type.lower() == 'premium':
                self.user_type = UserType.PREMIUM
                return {
                    "success": True,
                    "message": "✅ 已选择付费服务\n💡 注意：这是演示版本，实际付费功能需要接入支付系统",
                    "service_type": "premium",
                    "next_phase": "case_analysis",
                    "next_phase_name": "案例分析阶段"
                }
            else:
                return {
                    "success": False,
                    "error": "请选择 'free' 或 'premium' 服务类型"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"服务选择错误: {str(e)}"
            }
    
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
                
                result = {
                    "success": True,
                    "analysis_result": self.case_analysis_result,
                    "message": "✅ 案例分析完成",
                    "analysis_file": analysis_file
                }
                
                # 根据用户类型决定下一步
                if self.user_type == UserType.PREMIUM:
                    result["next_phase"] = "evidence_analysis"
                    result["next_phase_name"] = "证据分析阶段"
                else:
                    result["next_phase"] = "final_report"
                    result["next_phase_name"] = "生成最终报告"
                
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
    
    def perform_evidence_analysis(self, perform_analysis: bool = True) -> Dict[str, Any]:
        """执行证据分析（仅付费用户）"""
        try:
            if self.user_type != UserType.PREMIUM:
                return {
                    "success": False,
                    "error": "证据分析仅对付费用户开放"
                }
            
            if not perform_analysis:
                return {
                    "success": True,
                    "message": "⏭️ 跳过证据分析",
                    "next_phase": "final_report",
                    "next_phase_name": "生成最终报告"
                }
            
            # 准备证据分析数据
            evidence_data = {
                "conversation_file": self.conversation_file_path,
                "uploaded_files": self.uploaded_files,
                "evidence_dir": self.evidence_dir
            }
            
            # 调用增强的证据分析模块
            self.evidence_analysis_result = self._analyze_evidence_with_files(evidence_data)
            
            if self.evidence_analysis_result and "error" not in self.evidence_analysis_result:
                # 保存证据分析结果
                evidence_file = os.path.join(self.session_dir, "evidence_analysis.json")
                with open(evidence_file, 'w', encoding='utf-8') as f:
                    json.dump(self.evidence_analysis_result, f, ensure_ascii=False, indent=2)
                
                # 生成摘要
                summary = self._generate_evidence_summary()
                
                # 生成格式化的完整报告内容
                formatted_report = self._format_evidence_report(self.evidence_analysis_result)
                
                return {
                    "success": True,
                    "analysis_result": self.evidence_analysis_result,
                    "summary": summary,
                    "formatted_report": formatted_report,
                    "message": "✅ 证据分析完成",
                    "evidence_file": evidence_file,
                    "next_phase": "final_report",
                    "next_phase_name": "生成最终报告"
                }
            else:
                return {
                    "success": False,
                    "error": "证据分析失败"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"证据分析过程中出错: {str(e)}"
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
            "has_case_analysis": bool(self.case_analysis_result),
            "has_evidence_analysis": bool(self.evidence_analysis_result)
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
    
    def _generate_evidence_summary(self) -> Dict[str, Any]:
        """生成证据分析摘要"""
        if not self.evidence_analysis_result:
            return {}
        
        # 核心证据
        core_evidence = self.evidence_analysis_result.get('核心证据列表', [])
        core_evidence_summary = []
        for i, evidence in enumerate(core_evidence, 1):
            core_evidence_summary.append({
                "index": i,
                "type": evidence.get('类型', 'N/A'),
                "summary": evidence.get('摘要', 'N/A')[:100] + "..." if len(evidence.get('摘要', '')) > 100 else evidence.get('摘要', 'N/A')
            })
        
        # 证据完整性
        completeness = self.evidence_analysis_result.get('证据完整性评估', {})
        
        # 建议
        recommendations = self.evidence_analysis_result.get('建议和风险提示', [])[:3]
        
        return {
            "core_evidence_count": len(core_evidence),
            "core_evidence": core_evidence_summary,
            "completeness_score": completeness.get('完整性得分', 'N/A'),
            "recommendations": recommendations
        }
    
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
        
        # 付费用户包含证据分析
        if self.user_type == UserType.PREMIUM and self.evidence_analysis_result:
            report["证据分析结果"] = self.evidence_analysis_result
            report["服务级别"] = "付费专业版"
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
            
            # 案例分析
            if report.get("案例分析结果"):
                f.write("⚖️ 案例分析:\n")
                f.write("-" * 40 + "\n")
                f.write(str(report["案例分析结果"]) + "\n\n")
            
            # 证据分析（付费用户）
            if report.get("证据分析结果"):
                f.write("🔬 证据分析:\n")
                f.write("-" * 40 + "\n")
                
                evidence_result = report["证据分析结果"]
                
                # LLM综合分析
                if evidence_result.get("LLM综合分析"):
                    f.write("专业分析:\n")
                    f.write(evidence_result["LLM综合分析"] + "\n\n")
                
                # 核心证据
                core_evidence = evidence_result.get("核心证据列表", [])
                if core_evidence:
                    f.write(f"核心证据 ({len(core_evidence)} 项):\n")
                    for i, evidence in enumerate(core_evidence, 1):
                        f.write(f"{i}. {evidence.get('类型', 'N/A')}: {evidence.get('摘要', 'N/A')}\n")
                    f.write("\n")
                
                # 建议
                recommendations = evidence_result.get("建议和风险提示", [])
                if recommendations:
                    f.write("专业建议:\n")
                    for rec in recommendations:
                        f.write(f"• {rec}\n")
                    f.write("\n")
            
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
            "has_case_analysis": bool(report.get("案例分析结果")),
            "has_evidence_analysis": bool(report.get("证据分析结果"))
        }
        
        if report.get("证据分析结果"):
            evidence_result = report["证据分析结果"]
            core_count = len(evidence_result.get("核心证据列表", []))
            supporting_count = len(evidence_result.get("辅助证据列表", []))
            summary["evidence_stats"] = {
                "core_evidence_count": core_count,
                "supporting_evidence_count": supporting_count
            }
        
        return summary
    
    def _format_evidence_report(self, evidence_result: Dict[str, Any]) -> str:
        """格式化证据分析报告为可读文本"""
        if not evidence_result:
            return "暂无证据分析结果"
        
        report_lines = []
        report_lines.append("🔬 证据分析报告")
        report_lines.append("=" * 50)
        report_lines.append("")
        
        # LLM综合分析
        if evidence_result.get("LLM综合分析"):
            report_lines.append("📋 专业分析：")
            report_lines.append("-" * 30)
            report_lines.append(evidence_result["LLM综合分析"])
            report_lines.append("")
        
        # 核心证据列表
        core_evidence = evidence_result.get('核心证据列表', [])
        if core_evidence:
            report_lines.append(f"🎯 核心证据 ({len(core_evidence)} 项)：")
            report_lines.append("-" * 30)
            for i, evidence in enumerate(core_evidence, 1):
                evidence_type = evidence.get('类型', 'N/A')
                evidence_summary = evidence.get('摘要', 'N/A')
                importance = evidence.get('重要性', 'N/A')
                report_lines.append(f"{i}. {evidence_type}")
                report_lines.append(f"   摘要: {evidence_summary}")
                report_lines.append(f"   重要性: {importance}")
                report_lines.append("")
        
        # 辅助证据列表
        supporting_evidence = evidence_result.get('辅助证据列表', [])
        if supporting_evidence:
            report_lines.append(f"📎 辅助证据 ({len(supporting_evidence)} 项)：")
            report_lines.append("-" * 30)
            for i, evidence in enumerate(supporting_evidence, 1):
                evidence_type = evidence.get('类型', 'N/A')
                evidence_summary = evidence.get('摘要', 'N/A')
                report_lines.append(f"{i}. {evidence_type}: {evidence_summary}")
            report_lines.append("")
        
        # 证据完整性评估
        completeness = evidence_result.get('证据完整性评估', {})
        if completeness:
            report_lines.append("📊 证据完整性评估：")
            report_lines.append("-" * 30)
            score = completeness.get('完整性得分', 'N/A')
            report_lines.append(f"完整性得分: {score}")
            
            missing_evidence = completeness.get('缺失证据', [])
            if missing_evidence:
                report_lines.append("缺失证据:")
                for evidence in missing_evidence:
                    report_lines.append(f"  • {evidence}")
            report_lines.append("")
        
        # 建议和风险提示
        recommendations = evidence_result.get('建议和风险提示', [])
        if recommendations:
            report_lines.append("💡 专业建议：")
            report_lines.append("-" * 30)
            for rec in recommendations:
                report_lines.append(f"• {rec}")
            report_lines.append("")
        
        # 文件分析（如果有）
        if evidence_result.get('文件证据列表'):
            file_evidence = evidence_result['文件证据列表']
            report_lines.append(f"📁 上传文件分析 ({len(file_evidence)} 个文件)：")
            report_lines.append("-" * 30)
            for file_info in file_evidence:
                file_name = file_info.get('文件名', 'N/A')
                file_type = file_info.get('类型', 'N/A')
                report_lines.append(f"• {file_name} ({file_type})")
            report_lines.append("")
        
        report_lines.append("=" * 50)
        report_lines.append("报告生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return "\n".join(report_lines)
    
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
        
        # 证据分析结果（付费用户）
        evidence_result = final_report.get("证据分析结果")
        if evidence_result:
            report_lines.append("🔬 证据分析：")
            report_lines.append("-" * 30)
            
            # LLM综合分析
            if evidence_result.get("LLM综合分析"):
                report_lines.append("专业分析:")
                report_lines.append(evidence_result["LLM综合分析"])
                report_lines.append("")
            
            # 核心证据
            core_evidence = evidence_result.get("核心证据列表", [])
            if core_evidence:
                report_lines.append(f"核心证据 ({len(core_evidence)} 项):")
                for i, evidence in enumerate(core_evidence, 1):
                    evidence_type = evidence.get('类型', 'N/A')
                    evidence_summary = evidence.get('摘要', 'N/A')
                    report_lines.append(f"{i}. {evidence_type}: {evidence_summary}")
                report_lines.append("")
            
            # 建议
            recommendations = evidence_result.get("建议和风险提示", [])
            if recommendations:
                report_lines.append("专业建议:")
                for rec in recommendations:
                    report_lines.append(f"• {rec}")
                report_lines.append("")
        
        report_lines.append("=" * 60)
        report_lines.append("报告结束")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def upload_evidence_file(self, file, evidence_type: str = None) -> Dict[str, Any]:
        """上传证据文件"""
        try:
            # 验证文件
            if not file or file.filename == '':
                return {
                    "success": False,
                    "error": "未选择文件"
                }
            
            # 根据证据类型定义允许的文件扩展名
            allowed_extensions_by_type = {
                'contract': {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'},
                'payment': {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'},
                'attendance': {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'},
                'medical': {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'},
                'media': {'mp3', 'mp4', 'wav', 'avi', 'mov', 'm4a'},
                'chat': {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}
            }
            
            # 默认允许的文件类型（向后兼容）
            default_allowed = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt', 'mp3', 'mp4', 'wav', 'avi', 'mov', 'm4a'}
            allowed_extensions = allowed_extensions_by_type.get(evidence_type, default_allowed)
            
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            
            if file_ext not in allowed_extensions:
                return {
                    "success": False,
                    "error": f"该证据类型不支持 {file_ext} 格式文件"
                }
            
            # 验证文件大小 (10MB)
            file.seek(0, 2)  # 移动到文件末尾
            file_size = file.tell()
            file.seek(0)  # 重置到文件开头
            
            if file_size > 10 * 1024 * 1024:  # 10MB
                return {
                    "success": False,
                    "error": "文件大小超过10MB限制"
                }
            
            # 生成安全的文件名，确保保留扩展名
            original_filename = file.filename
            # 分离文件名和扩展名
            if '.' in original_filename:
                name_part, ext_part = original_filename.rsplit('.', 1)
                safe_name = secure_filename(name_part)
                safe_ext = secure_filename(ext_part)
            else:
                safe_name = secure_filename(original_filename)
                safe_ext = file_ext  # 使用之前提取的扩展名
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{safe_name}.{safe_ext}"
            
            # 保存文件
            file_path = os.path.join(self.evidence_dir, safe_filename)
            file.save(file_path)
            
            # 记录文件信息
            file_info = {
                "original_name": file.filename,
                "safe_filename": safe_filename,
                "file_path": file_path,
                "file_size": file_size,
                "file_type": file_ext,
                "evidence_type": evidence_type,  # 添加证据类型信息
                "upload_time": datetime.now().isoformat()
            }
            
            self.uploaded_files.append(file_info)
            
            return {
                "success": True,
                "message": f"文件 {file.filename} 上传成功",
                "file_path": file_path,
                "file_info": file_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"文件上传失败: {str(e)}"
            }
    
    def get_uploaded_files(self) -> List[Dict[str, Any]]:
        """获取已上传的文件列表"""
        return self.uploaded_files
    
    def remove_uploaded_file(self, file_path: str) -> Dict[str, Any]:
        """删除已上传的文件"""
        try:
            # 从列表中移除
            self.uploaded_files = [f for f in self.uploaded_files if f['file_path'] != file_path]
            
            # 删除物理文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return {
                "success": True,
                "message": "文件删除成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"文件删除失败: {str(e)}"
            }
    
    def _get_evidence_type_display_name(self, evidence_type: str) -> str:
        """将前端传递的evidence_type转换为中文显示名称"""
        type_mapping = {
            'contract': '劳动合同',
            'payment': '工资证明', 
            'attendance': '考勤记录',
            'medical': '医疗材料',
            'media': '音视频证据',
            'chat': '聊天记录'
        }
        return type_mapping.get(evidence_type, '其他证据')
    
    def _analyze_evidence_with_files(self, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        """结合上传文件和对话记录进行证据分析"""
        try:
            # 准备上传文件信息
            uploaded_files = evidence_data.get("uploaded_files", [])
            uploaded_files_info = []
            
            if uploaded_files:
                for file_info in uploaded_files:
                    uploaded_files_info.append({
                        'filename': file_info.get('original_name', ''),
                        'filepath': file_info.get('file_path', ''),
                        'evidence_type': file_info.get('evidence_type', '')  # 直接传递前端的evidence_type
                    })
            
            # 调用证据分析器，传递上传文件信息
            base_analysis = self.evidence_analyzer.analyze_case_evidence(
                evidence_data["conversation_file"],
                uploaded_files_info if uploaded_files_info else None
            )
            
            if not base_analysis or "error" in base_analysis:
                return base_analysis
            
            # 如果有上传的文件，进行额外的文件分析和合并
            if uploaded_files:
                file_analysis = self._analyze_uploaded_files(uploaded_files)
                
                # 合并分析结果
                enhanced_analysis = self._merge_analysis_results(base_analysis, file_analysis)
                return enhanced_analysis
            else:
                # 没有上传文件时，返回基础分析结果
                return base_analysis
                
        except Exception as e:
            return {
                "error": f"证据分析失败: {str(e)}"
            }
    
    def _analyze_uploaded_files(self, uploaded_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析上传的文件"""
        file_evidence = []
        file_types_count = {}
        total_files = len(uploaded_files)
        
        for file_info in uploaded_files:
            file_type = file_info.get('file_type', 'unknown')
            file_name = file_info.get('original_name', 'unknown')
            file_size = file_info.get('file_size', 0)
            
            # 统计文件类型
            file_types_count[file_type] = file_types_count.get(file_type, 0) + 1
            
            # 直接使用前端传递的证据类型
            evidence_type = self._get_evidence_type_display_name(
                file_info.get('evidence_type', '')
            )
            
            file_evidence.append({
                "类型": evidence_type,
                "文件名": file_name,
                "文件类型": file_type,
                "文件大小": self._format_file_size(file_size),
                "摘要": f"上传的{evidence_type}文件：{file_name}",
                "重要性": "高" if file_type in ['pdf', 'doc', 'docx'] else "中",
                "来源": "用户上传"
            })
        
        return {
            "文件证据列表": file_evidence,
            "文件统计": {
                "总文件数": total_files,
                "文件类型分布": file_types_count
            },
            "文件分析建议": self._generate_file_analysis_suggestions(file_types_count)
        }
    
    def _generate_file_analysis_suggestions(self, file_types_count: Dict[str, int]) -> List[str]:
        """根据文件类型生成分析建议"""
        suggestions = []
        
        if file_types_count.get('pdf', 0) > 0:
            suggestions.append("📄 检测到PDF文件，建议仔细审查其中的关键条款和签名")
        
        if file_types_count.get('jpg', 0) + file_types_count.get('jpeg', 0) + file_types_count.get('png', 0) > 0:
            suggestions.append("🖼️ 检测到图片文件，建议确认图片清晰度和内容完整性")
        
        if file_types_count.get('doc', 0) + file_types_count.get('docx', 0) > 0:
            suggestions.append("📝 检测到Word文档，建议检查文档的修改历史和版本信息")
        
        if len(file_types_count) == 0:
            suggestions.append("⚠️ 未检测到上传文件，建议补充相关证据材料")
        
        return suggestions
    
    def _merge_analysis_results(self, base_analysis: Dict[str, Any], file_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """合并基础分析和文件分析结果"""
        merged_analysis = base_analysis.copy()
        
        # 合并核心证据列表
        base_core_evidence = merged_analysis.get('核心证据列表', [])
        file_evidence = file_analysis.get('文件证据列表', [])
        
        # 将文件证据添加到核心证据列表
        merged_analysis['核心证据列表'] = base_core_evidence + file_evidence
        
        # 更新证据完整性评估
        original_score = merged_analysis.get('证据完整性评估', {}).get('完整性得分', '0%')
        original_score_num = float(original_score.replace('%', '')) if original_score != 'N/A' else 0
        
        # 根据上传文件数量提升完整性得分
        file_count = len(file_evidence)
        bonus_score = min(file_count * 15, 40)  # 每个文件增加15分，最多40分
        new_score = min(original_score_num + bonus_score, 100)
        
        if '证据完整性评估' not in merged_analysis:
            merged_analysis['证据完整性评估'] = {}
        
        merged_analysis['证据完整性评估']['完整性得分'] = f"{new_score:.1f}%"
        
        # 合并建议和风险提示
        base_suggestions = merged_analysis.get('建议和风险提示', [])
        file_suggestions = file_analysis.get('文件分析建议', [])
        
        merged_analysis['建议和风险提示'] = base_suggestions + file_suggestions
        
        # 添加文件统计信息
        merged_analysis['文件统计信息'] = file_analysis.get('文件统计', {})
        
        # 更新LLM综合分析
        if '文件证据列表' in file_analysis and file_analysis['文件证据列表']:
            file_summary = f"\n\n📎 文件证据分析：\n用户上传了{len(file_evidence)}个证据文件，包括{', '.join(set([f['类型'] for f in file_evidence]))}等。这些文件证据大大增强了案件的可信度和完整性。"
            
            if 'LLM综合分析' in merged_analysis:
                merged_analysis['LLM综合分析'] += file_summary
            else:
                merged_analysis['LLM综合分析'] = "基于对话记录和上传文件的综合分析：" + file_summary
        
        return merged_analysis
    
    def _format_file_size(self, bytes_size: int) -> str:
        """格式化文件大小"""
        if bytes_size == 0:
            return "0 Bytes"
        k = 1024
        sizes = ['Bytes', 'KB', 'MB', 'GB']
        i = 0
        while bytes_size >= k and i < len(sizes) - 1:
            bytes_size /= k
            i += 1
        return f"{bytes_size:.1f} {sizes[i]}"

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

@app.route('/api/select_service', methods=['POST'])
def select_service():
    """选择服务类型"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        service_type = data.get('service_type', '').strip().lower()
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if service_type not in ['free', 'premium']:
            return jsonify({
                "success": False,
                "error": "无效的服务类型"
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

@app.route('/api/evidence_analysis', methods=['POST'])
def evidence_analysis():
    """执行证据分析"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        perform_analysis = data.get('perform_analysis', True)
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        lawyer_system = get_or_create_session(session_id)
        result = lawyer_system.perform_evidence_analysis(perform_analysis)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"证据分析失败: {str(e)}"
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

@app.route('/api/upload_evidence', methods=['POST'])
def upload_evidence():
    """上传证据文件"""
    try:
        session_id = request.form.get('session_id')
        evidence_type = request.form.get('evidence_type')  # 获取证据类型
        
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
        
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "未找到上传文件"
            }), 400
        
        file = request.files['file']
        lawyer_system = sessions[session_id]
        result = lawyer_system.upload_evidence_file(file, evidence_type)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"文件上传失败: {str(e)}"
        }), 500

@app.route('/api/uploaded_files', methods=['GET'])
def get_uploaded_files():
    """获取已上传的文件列表"""
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
        files = lawyer_system.get_uploaded_files()
        
        return jsonify({
            "success": True,
            "files": files
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取文件列表失败: {str(e)}"
        }), 500

@app.route('/api/remove_file', methods=['POST'])
def remove_file():
    """删除上传的文件"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        file_path = data.get('file_path')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "缺少会话ID"
            }), 400
        
        if not file_path:
            return jsonify({
                "success": False,
                "error": "缺少文件路径"
            }), 400
        
        if session_id not in sessions:
            return jsonify({
                "success": False,
                "error": "会话不存在"
            }), 404
        
        lawyer_system = sessions[session_id]
        result = lawyer_system.remove_uploaded_file(file_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"删除文件失败: {str(e)}"
        }), 500

def main():
    """主函数"""
    try:
        # 创建必要的目录
        os.makedirs("sessions", exist_ok=True)
        os.makedirs("conversation_datasets", exist_ok=True)
        os.makedirs("evidence_reports", exist_ok=True)
        os.makedirs("templates", exist_ok=True)
        os.makedirs("static", exist_ok=True)

        set_model_provider("doubao")
        
        print("🏛️ AI劳动法律师Web系统启动中...")
        print("🌐 访问地址: http://localhost:5000")
        print("=" * 60)
        
        # 启动Flask应用
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()