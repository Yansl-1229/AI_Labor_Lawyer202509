#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI劳动法律师软件主程序
整合多轮对话收集、仲裁分析和证据分析三个核心模块
实现完整的法律咨询服务流程
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# 导入三个核心模块
try:
    from lawyer_model import chat_with_lawyer, create_new_conversation, save_conversation_to_json
    from free_generate_case_analysis import CaseAnalysisGenerator
    from evidence_analyzer import EvidenceAnalyzer
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("请确保以下文件存在：")
    print("- 1.lawyer_model.py (重命名为 lawyer_model.py)")
    print("- 2.free_generate_case_analysis.py (重命名为 free_generate_case_analysis.py)")
    print("- 3.evidence_analyzer.py (重命名为 evidence_analyzer.py)")
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

class AILawyerSystem:
    """
    AI劳动法律师系统主类
    负责协调各个模块的工作，管理用户会话和业务流程
    """
    
    def __init__(self):
        """初始化系统"""
        self.session_id = self._generate_session_id()
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
        
        print(f"🏛️ AI劳动法律师系统已启动")
        print(f"📋 会话ID: {self.session_id}")
        print("=" * 60)
    
    def _generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _init_modules(self):
        """初始化各个功能模块"""
        try:
            # 初始化案例分析生成器
            self.case_analyzer = CaseAnalysisGenerator()
            print("✅ 案例分析模块初始化成功")
            
            # 初始化证据分析器
            self.evidence_analyzer = EvidenceAnalyzer()
            print("✅ 证据分析模块初始化成功")
            
        except Exception as e:
            print(f"❌ 模块初始化失败: {e}")
            raise
    
    def start_consultation(self):
        """
        启动法律咨询流程
        这是系统的主入口点
        """
        print("\n🤝 欢迎使用AI劳动法律师咨询系统")
        print("我将通过专业的对话帮您梳理劳动争议相关问题")
        print("请放心，所有信息都会严格保密")
        print("\n输入 'exit' 可随时退出系统")
        print("输入 'status' 查看当前进度")
        print("-" * 60)
        
        try:
            # 第一阶段：信息收集
            self._phase_information_collection()
            
            # 第二阶段：付费判断
            self._phase_payment_decision()
            
            # 第三阶段：案例分析
            self._phase_case_analysis()
            
            # 第四阶段：证据分析（仅付费用户）
            if self.user_type == UserType.PREMIUM:
                self._phase_evidence_analysis()
            
            # 第五阶段：生成最终报告
            self._phase_generate_final_report()
            
            print("\n🎉 咨询服务已完成，感谢您的使用！")
            
        except KeyboardInterrupt:
            print("\n\n👋 用户主动退出，会话已保存")
            self._save_session_data()
        except Exception as e:
            print(f"\n❌ 系统错误: {e}")
            self._save_session_data()
            raise
    
    def _phase_information_collection(self):
        """
        第一阶段：多轮对话信息收集
        通过智能对话收集用户的劳动争议相关信息
        """
        print("\n📝 第一阶段：信息收集")
        print("=" * 30)
        
        self.conversation_history = create_new_conversation()
        conversation_ended = False
        
        while not conversation_ended:
            try:
                user_input = input("\n您: ").strip()
                
                # 处理特殊命令
                if user_input.lower() == 'exit':
                    print("👋 感谢使用，再见！")
                    sys.exit(0)
                elif user_input.lower() == 'status':
                    self._show_status()
                    continue
                elif not user_input:
                    print("请输入您的问题或回答...")
                    continue
                
                # 调用律师对话模块
                print(conversation_ended)
                response, self.conversation_history, conversation_ended = chat_with_lawyer(
                    user_input, self.conversation_history
                )
                print(conversation_ended)
                print(f"\n律师: {response}")
                
                if conversation_ended:
                    self.session_status = SessionStatus.COMPLETED
                    print("\n✅ 信息收集阶段完成")
                    
                    # 保存对话记录
                    self.conversation_file_path = self._save_conversation()
                    print(f"📄 对话记录已保存: {self.conversation_file_path}")
                    
            except Exception as e:
                print(f"❌ 对话处理错误: {e}")
                continue
    
    def _phase_payment_decision(self):
        """
        第二阶段：付费判断
        根据用户选择决定服务级别
        """
        print("\n💳 第二阶段：服务选择")
        print("=" * 30)
        
        print("\n基于您提供的信息，我们可以为您提供以下服务：")
        print("\n🆓 免费服务包含：")
        print("  • 基础案例分析")
        print("  • 争议焦点梳理")
        print("  • 基本法律建议")
        
        print("\n💎 付费服务额外包含：")
        print("  • 专业证据合规性分析")
        print("  • 精确的仲裁赔偿计算")
        print("  • 完整的法律依据说明")
        print("  • 证据收集指导")
        print("  • 详细的维权方案")
        
        while True:
            choice = input("\n请选择服务类型 (输入 'free' 选择免费服务，'premium' 选择付费服务): ").strip().lower()
            
            if choice == 'free':
                self.user_type = UserType.FREE
                print("\n✅ 已选择免费服务")
                break
            elif choice == 'premium':
                self.user_type = UserType.PREMIUM
                print("\n✅ 已选择付费服务")
                print("💡 注意：这是演示版本，实际付费功能需要接入支付系统")
                break
            elif choice == 'exit':
                sys.exit(0)
            else:
                print("❌ 请输入 'free' 或 'premium'")
    
    def _phase_case_analysis(self):
        """
        第三阶段：案例分析
        基于收集的信息生成法律分析报告
        """
        print("\n⚖️ 第三阶段：案例分析")
        print("=" * 30)
        
        if not self.conversation_file_path:
            print("❌ 未找到对话记录文件")
            return
        
        print("🔍 正在分析您的案例...")
        
        try:
            # 调用案例分析模块
            self.case_analysis_result = self.case_analyzer.analyze_conversation(
                self.conversation_file_path
            )
            
            if self.case_analysis_result and self.case_analysis_result != "分析失败":
                print("\n📋 案例分析报告：")
                print("-" * 50)
                print(self.case_analysis_result)
                print("-" * 50)
                
                # 保存分析结果
                analysis_file = os.path.join(self.session_dir, "case_analysis.txt")
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    f.write(self.case_analysis_result)
                print(f"\n📄 分析报告已保存: {analysis_file}")
                
            else:
                print("❌ 案例分析失败，请稍后重试")
                
        except Exception as e:
            print(f"❌ 案例分析过程中出错: {e}")
    
    def _phase_evidence_analysis(self):
        """
        第四阶段：证据分析（仅付费用户）
        分析用户提供的证据材料
        """
        print("\n🔬 第四阶段：证据分析")
        print("=" * 30)
        
        print("作为付费用户，您可以享受专业的证据分析服务")
        
        choice = input("\n是否需要进行证据分析？(y/n): ").strip().lower()
        
        if choice in ['y', 'yes', '是']:
            try:
                print("\n🔍 开始证据分析流程...")
                
                # 调用证据分析模块
                self.evidence_analysis_result = self.evidence_analyzer.analyze_case_evidence(
                    self.conversation_file_path
                )
                
                if self.evidence_analysis_result and "error" not in self.evidence_analysis_result:
                    print("\n✅ 证据分析完成")
                    
                    # 显示分析摘要
                    self._display_evidence_summary()
                    
                    # 保存证据分析结果
                    evidence_file = os.path.join(self.session_dir, "evidence_analysis.json")
                    with open(evidence_file, 'w', encoding='utf-8') as f:
                        json.dump(self.evidence_analysis_result, f, ensure_ascii=False, indent=2)
                    print(f"\n📄 证据分析报告已保存: {evidence_file}")
                    
                else:
                    print("❌ 证据分析失败")
                    
            except Exception as e:
                print(f"❌ 证据分析过程中出错: {e}")
        else:
            print("⏭️ 跳过证据分析")
    
    def _phase_generate_final_report(self):
        """
        第五阶段：生成最终综合报告
        整合所有分析结果，生成完整的咨询报告
        """
        print("\n📊 第五阶段：生成综合报告")
        print("=" * 30)
        
        print("🔄 正在整合分析结果...")
        
        # 生成综合报告
        final_report = self._create_comprehensive_report()
        
        # 保存最终报告
        report_file = os.path.join(self.session_dir, "final_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        
        # 生成可读性更好的文本报告
        text_report_file = os.path.join(self.session_dir, "final_report.txt")
        self._save_text_report(final_report, text_report_file)
        
        print(f"\n📄 综合报告已生成: {text_report_file}")
        print("\n📋 报告摘要：")
        self._display_final_summary(final_report)
    
    def _save_conversation(self) -> str:
        """
        保存对话记录
        返回保存的文件路径
        """
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
    
    def _display_evidence_summary(self):
        """
        显示证据分析摘要
        """
        if not self.evidence_analysis_result:
            return
        
        print("\n📋 证据分析摘要：")
        print("-" * 40)
        
        # 显示核心证据
        core_evidence = self.evidence_analysis_result.get('核心证据列表', [])
        if core_evidence:
            print(f"🎯 核心证据 ({len(core_evidence)} 项):")
            for i, evidence in enumerate(core_evidence, 1):
                print(f"  {i}. {evidence.get('类型', 'N/A')}: {evidence.get('摘要', 'N/A')[:50]}...")
        
        # 显示证据完整性
        completeness = self.evidence_analysis_result.get('证据完整性评估', {})
        if completeness:
            print(f"\n📊 证据完整性: {completeness.get('完整性得分', 'N/A')}")
        
        # 显示建议
        recommendations = self.evidence_analysis_result.get('建议和风险提示', [])
        if recommendations:
            print("\n💡 专业建议:")
            for rec in recommendations[:3]:  # 只显示前3条
                print(f"  • {rec}")
    
    def _create_comprehensive_report(self) -> Dict[str, Any]:
        """
        创建综合报告
        整合所有分析结果
        """
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
        """
        保存可读性更好的文本报告
        """
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
    
    def _display_final_summary(self, report: Dict[str, Any]):
        """
        显示最终报告摘要
        """
        print("-" * 50)
        
        session_info = report.get("会话信息", {})
        print(f"📋 会话ID: {session_info.get('会话ID', 'N/A')}")
        print(f"🎯 服务级别: {report.get('服务级别', 'N/A')}")
        print(f"⏰ 完成时间: {session_info.get('生成时间', 'N/A')}")
        
        if report.get("案例分析结果"):
            print("✅ 案例分析: 已完成")
        
        if report.get("证据分析结果"):
            evidence_result = report["证据分析结果"]
            core_count = len(evidence_result.get("核心证据列表", []))
            supporting_count = len(evidence_result.get("辅助证据列表", []))
            print(f"✅ 证据分析: 已完成 (核心证据 {core_count} 项, 辅助证据 {supporting_count} 项)")
        
        print("-" * 50)
    
    def _show_status(self):
        """
        显示当前系统状态
        """
        print("\n📊 当前状态:")
        print(f"  会话ID: {self.session_id}")
        print(f"  用户类型: {self.user_type.value}")
        print(f"  会话状态: {self.session_status.value}")
        print(f"  会话目录: {self.session_dir}")
    
    def _save_session_data(self):
        """
        保存会话数据（用于异常退出时的数据保护）
        """
        try:
            session_data = {
                "session_id": self.session_id,
                "user_type": self.user_type.value,
                "session_status": self.session_status.value,
                "conversation_file_path": self.conversation_file_path,
                "timestamp": datetime.now().isoformat()
            }
            
            session_file = os.path.join(self.session_dir, "session_data.json")
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 会话数据已保存: {session_file}")
            
        except Exception as e:
            print(f"❌ 保存会话数据失败: {e}")


def main():
    """
    主函数
    程序入口点
    """
    try:
        # 创建必要的目录
        os.makedirs("sessions", exist_ok=True)
        os.makedirs("conversation_datasets", exist_ok=True)
        os.makedirs("evidence_reports", exist_ok=True)
        
        # 启动AI律师系统
        system = AILawyerSystem()
        system.start_consultation()
        
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序运行错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()