#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成模块

功能：
1. 汇总分析结果，生成完整报告
2. 提供多种报告格式（文本、HTML、JSON）
3. 生成专业的法律分析报告
4. 提供维权建议和后续行动指导
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        self.report_templates = {
            'text': self._generate_text_report,
            'html': self._generate_html_report,
            'json': self._generate_json_report
        }
    
    def generate_report(self, case_id: str, report_data: Dict[str, Any], 
                       format_type: str = 'text') -> Optional[str]:
        """生成分析报告
        
        Args:
            case_id: 案件ID
            report_data: 报告数据
            format_type: 报告格式 (text/html/json)
            
        Returns:
            报告文件路径，失败返回None
        """
        try:
            # 验证输入数据
            if not self._validate_report_data(report_data):
                print("错误：报告数据不完整")
                return None
            
            # 选择报告生成器
            generator = self.report_templates.get(format_type)
            if not generator:
                print(f"错误：不支持的报告格式 {format_type}")
                return None
            
            # 生成报告内容
            report_content = generator(case_id, report_data)
            
            # 保存报告文件
            report_path = self._save_report(case_id, report_content, format_type)
            
            if report_path:
                print(f"报告生成成功: {report_path}")
                return report_path
            else:
                print("报告保存失败")
                return None
            
        except Exception as e:
            print(f"生成报告失败: {e}")
            return None
    
    def _validate_report_data(self, report_data: Dict[str, Any]) -> bool:
        """验证报告数据完整性
        
        Args:
            report_data: 报告数据
            
        Returns:
            数据是否完整
        """
        required_fields = ['case_info', 'evidence_list']
        
        for field in required_fields:
            if field not in report_data:
                print(f"缺少必要字段: {field}")
                return False
        
        return True
    
    def _generate_text_report(self, case_id: str, report_data: Dict[str, Any]) -> str:
        """生成文本格式报告
        
        Args:
            case_id: 案件ID
            report_data: 报告数据
            
        Returns:
            文本报告内容
        """
        case_info = report_data.get('case_info', {})
        evidence_list = report_data.get('evidence_list', {})
        chat_history = report_data.get('chat_history', [])
        analysis_results = report_data.get('analysis_results', [])
        
        report_lines = []
        
        # 报告标题
        report_lines.append("="*80)
        report_lines.append("AI劳动法律师举证分析报告")
        report_lines.append("="*80)
        report_lines.append(f"案件ID: {case_id}")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        report_lines.append("")
        
        # 案件基本信息
        report_lines.append("一、案件基本信息")
        report_lines.append("-"*40)
        
        basic_info = case_info.get('basic_info', {})
        dispute_info = case_info.get('dispute_info', {})
        
        report_lines.append(f"当事人: {basic_info.get('employee_name', '当事人')}")
        report_lines.append(f"公司名称: {basic_info.get('company_name', '未知')}")
        report_lines.append(f"入职日期: {basic_info.get('hire_date', '未知')}")
        report_lines.append(f"解除日期: {basic_info.get('termination_date', '未知')}")
        report_lines.append(f"月薪: {basic_info.get('monthly_salary', '未知')}元")
        report_lines.append(f"争议类型: {dispute_info.get('type', '未知')}")
        report_lines.append(f"解除理由: {dispute_info.get('reason_given', '未知')}")
        report_lines.append("")
        
        # 争议焦点分析
        report_lines.append("二、争议焦点分析")
        report_lines.append("-"*40)
        
        focus_analysis = self._analyze_dispute_focus(case_info)
        report_lines.extend(focus_analysis)
        report_lines.append("")
        
        # 证据清单
        report_lines.append("三、证据需求清单")
        report_lines.append("-"*40)
        
        evidence_items = evidence_list.get('evidence_items', [])
        
        # 按重要性分类显示
        core_evidence = [item for item in evidence_items if item.get('importance') == '核心']
        important_evidence = [item for item in evidence_items if item.get('importance') == '重要']
        auxiliary_evidence = [item for item in evidence_items if item.get('importance') == '辅助']
        
        if core_evidence:
            report_lines.append("(一) 核心证据")
            for i, evidence in enumerate(core_evidence, 1):
                report_lines.append(f"{i}. {evidence.get('type', '未知')}")
                report_lines.append(f"   描述: {evidence.get('description', '无')}")
                report_lines.append(f"   收集方法: {evidence.get('collection_method', '无')}")
                report_lines.append(f"   法律依据: {evidence.get('legal_basis', '无')}")
                report_lines.append(f"   状态: {evidence.get('status', '未收集')}")
                report_lines.append("")
        
        if important_evidence:
            report_lines.append("(二) 重要证据")
            for i, evidence in enumerate(important_evidence, 1):
                report_lines.append(f"{i}. {evidence.get('type', '未知')}")
                report_lines.append(f"   描述: {evidence.get('description', '无')}")
                report_lines.append(f"   收集方法: {evidence.get('collection_method', '无')}")
                report_lines.append("")
        
        if auxiliary_evidence:
            report_lines.append("(三) 辅助证据")
            for i, evidence in enumerate(auxiliary_evidence, 1):
                report_lines.append(f"{i}. {evidence.get('type', '未知')}")
                report_lines.append(f"   描述: {evidence.get('description', '无')}")
                report_lines.append("")
        
        # 证据分析结果
        if analysis_results:
            report_lines.append("四、证据分析结果")
            report_lines.append("-"*40)
            
            for i, result in enumerate(analysis_results, 1):
                report_lines.append(f"({i}) {result.get('file_name', '未知文件')}")
                report_lines.append(f"证据类型: {result.get('evidence_type', '未知')}")
                
                analysis_result = result.get('analysis_result', {})
                if analysis_result:
                    report_lines.append("分析结果:")
                    for key, value in analysis_result.items():
                        if key not in ['recommendations']:
                            report_lines.append(f"  {key}: {value}")
                    
                    recommendations = analysis_result.get('recommendations', [])
                    if recommendations:
                        report_lines.append("改进建议:")
                        for j, rec in enumerate(recommendations, 1):
                            report_lines.append(f"  {j}. {rec}")
                
                report_lines.append("")
        
        # 法律分析
        report_lines.append("五、法律分析")
        report_lines.append("-"*40)
        
        legal_analysis = self._generate_legal_analysis(case_info, evidence_list, analysis_results)
        report_lines.extend(legal_analysis)
        report_lines.append("")
        
        # 维权建议
        report_lines.append("六、维权建议")
        report_lines.append("-"*40)
        
        recommendations = self._generate_recommendations(case_info, evidence_list, analysis_results)
        report_lines.extend(recommendations)
        report_lines.append("")
        
        # 后续行动计划
        report_lines.append("七、后续行动计划")
        report_lines.append("-"*40)
        
        action_plan = self._generate_action_plan(case_info, evidence_list, analysis_results)
        report_lines.extend(action_plan)
        report_lines.append("")
        
        # 咨询记录摘要
        if chat_history:
            report_lines.append("八、咨询记录摘要")
            report_lines.append("-"*40)
            
            user_questions = [msg for msg in chat_history if msg.get('role') == 'user']
            if user_questions:
                report_lines.append(f"咨询问题总数: {len(user_questions)}")
                report_lines.append("主要关注问题:")
                
                # 显示前5个问题
                for i, question in enumerate(user_questions[:5], 1):
                    content = question.get('content', '')[:100]  # 限制长度
                    report_lines.append(f"{i}. {content}{'...' if len(question.get('content', '')) > 100 else ''}")
            
            report_lines.append("")
        
        # 报告结尾
        report_lines.append("="*80)
        report_lines.append("报告结束")
        report_lines.append("")
        report_lines.append("注意事项:")
        report_lines.append("1. 本报告仅供参考，具体法律问题请咨询专业律师")
        report_lines.append("2. 证据收集应当合法合规，避免侵犯他人权益")
        report_lines.append("3. 仲裁申请应在法定时效内提出")
        report_lines.append("4. 保留所有原始证据材料")
        report_lines.append("="*80)
        
        return "\n".join(report_lines)
    
    def _generate_html_report(self, case_id: str, report_data: Dict[str, Any]) -> str:
        """生成HTML格式报告
        
        Args:
            case_id: 案件ID
            report_data: 报告数据
            
        Returns:
            HTML报告内容
        """
        # 获取文本报告内容
        text_content = self._generate_text_report(case_id, report_data)
        
        # 转换为HTML格式
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI劳动法律师举证分析报告 - {case_id}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 10px;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .info-table th, .info-table td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        .info-table th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .evidence-item {{
            background-color: #f8f9fa;
            border-left: 4px solid #28a745;
            padding: 10px;
            margin: 10px 0;
        }}
        .core-evidence {{
            border-left-color: #dc3545;
        }}
        .important-evidence {{
            border-left-color: #ffc107;
        }}
        .auxiliary-evidence {{
            border-left-color: #28a745;
        }}
        .recommendation {{
            background-color: #e7f3ff;
            border: 1px solid #b3d9ff;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        .warning {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <pre style="white-space: pre-wrap; font-family: inherit;">{text_content}</pre>
    </div>
</body>
</html>
"""
        
        return html_content
    
    def _generate_json_report(self, case_id: str, report_data: Dict[str, Any]) -> str:
        """生成JSON格式报告
        
        Args:
            case_id: 案件ID
            report_data: 报告数据
            
        Returns:
            JSON报告内容
        """
        case_info = report_data.get('case_info', {})
        evidence_list = report_data.get('evidence_list', {})
        analysis_results = report_data.get('analysis_results', [])
        
        json_report = {
            'report_info': {
                'case_id': case_id,
                'generated_at': datetime.now().isoformat(),
                'report_type': 'evidence_analysis',
                'version': '1.0.0'
            },
            'case_summary': {
                'basic_info': case_info.get('basic_info', {}),
                'dispute_info': case_info.get('dispute_info', {}),
                'evidence_status': case_info.get('evidence_status', {})
            },
            'evidence_analysis': {
                'evidence_list': evidence_list,
                'analysis_results': analysis_results,
                'statistics': self._calculate_evidence_statistics(evidence_list, analysis_results)
            },
            'legal_analysis': {
                'dispute_focus': self._analyze_dispute_focus(case_info),
                'legal_basis': self._get_legal_basis(case_info),
                'strength_assessment': self._assess_case_strength(case_info, evidence_list, analysis_results)
            },
            'recommendations': {
                'evidence_collection': self._get_evidence_recommendations(evidence_list),
                'legal_strategy': self._get_legal_strategy(case_info),
                'action_plan': self._generate_action_plan(case_info, evidence_list, analysis_results)
            }
        }
        
        return json.dumps(json_report, ensure_ascii=False, indent=2)
    
    def _save_report(self, case_id: str, content: str, format_type: str) -> Optional[str]:
        """保存报告文件
        
        Args:
            case_id: 案件ID
            content: 报告内容
            format_type: 格式类型
            
        Returns:
            文件路径
        """
        try:
            # 确保reports目录存在
            reports_dir = 'reports'
            os.makedirs(reports_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_extension = {
                'text': 'txt',
                'html': 'html',
                'json': 'json'
            }.get(format_type, 'txt')
            
            filename = f"{case_id}_report_{timestamp}.{file_extension}"
            file_path = os.path.join(reports_dir, filename)
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return file_path
            
        except Exception as e:
            print(f"保存报告文件失败: {e}")
            return None
    
    def _analyze_dispute_focus(self, case_info: Dict[str, Any]) -> List[str]:
        """分析争议焦点
        
        Args:
            case_info: 案件信息
            
        Returns:
            争议焦点分析
        """
        focus_points = []
        
        dispute_info = case_info.get('dispute_info', {})
        dispute_type = dispute_info.get('type', '')
        reason_given = dispute_info.get('reason_given', '')
        has_training = dispute_info.get('has_training', False)
        has_evidence = dispute_info.get('has_evidence', False)
        
        if '违法解除' in dispute_type:
            focus_points.append("1. 解除劳动合同是否符合法定情形")
            
            if '不能胜任' in reason_given:
                focus_points.append("2. 公司是否有充分证据证明员工不能胜任工作")
                
                if not has_training:
                    focus_points.append("3. 公司是否履行了培训或调整工作岗位的义务")
                
                if not has_evidence:
                    focus_points.append("4. 公司解除决定是否有事实和法律依据")
            
            focus_points.append("5. 解除程序是否符合法律规定")
            focus_points.append("6. 经济补偿金或赔偿金的计算标准")
        
        elif '工资' in dispute_type:
            focus_points.append("1. 实际工资标准的确定")
            focus_points.append("2. 工资支付是否及时足额")
            focus_points.append("3. 加班费的计算和支付")
        
        elif '工伤' in dispute_type:
            focus_points.append("1. 是否构成工伤")
            focus_points.append("2. 伤残等级的认定")
            focus_points.append("3. 工伤赔偿项目和标准")
        
        if not focus_points:
            focus_points.append("1. 劳动关系的确认")
            focus_points.append("2. 争议事实的认定")
            focus_points.append("3. 法律责任的承担")
        
        return focus_points
    
    def _generate_legal_analysis(self, case_info: Dict[str, Any], evidence_list: Dict[str, Any], 
                                analysis_results: List[Dict[str, Any]]) -> List[str]:
        """生成法律分析
        
        Args:
            case_info: 案件信息
            evidence_list: 证据清单
            analysis_results: 分析结果
            
        Returns:
            法律分析内容
        """
        analysis = []
        
        dispute_info = case_info.get('dispute_info', {})
        dispute_type = dispute_info.get('type', '')
        
        if '违法解除' in dispute_type:
            analysis.append("根据《劳动合同法》第39条、第40条、第41条的规定，用人单位解除劳动合同应当符合法定情形。")
            
            reason_given = dispute_info.get('reason_given', '')
            if '不能胜任' in reason_given:
                analysis.append("")
                analysis.append("针对'不能胜任工作'的解除理由：")
                analysis.append("1. 根据《劳动合同法》第40条第2项，劳动者不能胜任工作，经过培训或者调整工作岗位，仍不能胜任工作的，用人单位可以解除劳动合同。")
                analysis.append("2. 用人单位需要证明：(1)劳动者确实不能胜任工作；(2)已经进行培训或调岗；(3)培训或调岗后仍不能胜任。")
                
                if not dispute_info.get('has_training', False):
                    analysis.append("3. 本案中公司未提供培训，不符合法定解除条件，可能构成违法解除。")
                
                if not dispute_info.get('has_evidence', False):
                    analysis.append("4. 公司无法提供不胜任的证据，解除理由不充分。")
            
            analysis.append("")
            analysis.append("违法解除的法律后果：")
            analysis.append("根据《劳动合同法》第87条，用人单位违法解除劳动合同的，应当按照经济补偿标准的二倍向劳动者支付赔偿金。")
        
        # 证据分析
        if analysis_results:
            analysis.append("")
            analysis.append("证据效力分析：")
            
            valid_evidence = [r for r in analysis_results if r.get('analysis_result', {}).get('是否可以作为核心证据') == '是']
            if valid_evidence:
                analysis.append(f"已收集的有效核心证据 {len(valid_evidence)} 项，证明力较强。")
            else:
                analysis.append("核心证据仍需补充，建议加强证据收集工作。")
        
        return analysis
    
    def _generate_recommendations(self, case_info: Dict[str, Any], evidence_list: Dict[str, Any], 
                                 analysis_results: List[Dict[str, Any]]) -> List[str]:
        """生成维权建议
        
        Args:
            case_info: 案件信息
            evidence_list: 证据清单
            analysis_results: 分析结果
            
        Returns:
            维权建议
        """
        recommendations = []
        
        # 证据收集建议
        evidence_items = evidence_list.get('evidence_items', [])
        uncollected = [item for item in evidence_items if item.get('status') != '已收集']
        
        if uncollected:
            recommendations.append("1. 证据收集建议：")
            core_uncollected = [item for item in uncollected if item.get('importance') == '核心']
            if core_uncollected:
                recommendations.append("   优先收集以下核心证据：")
                for item in core_uncollected[:3]:  # 显示前3个
                    recommendations.append(f"   - {item.get('type', '未知')}")
        
        # 法律策略建议
        dispute_info = case_info.get('dispute_info', {})
        if '违法解除' in dispute_info.get('type', ''):
            recommendations.append("")
            recommendations.append("2. 法律策略建议：")
            recommendations.append("   - 重点证明公司解除程序违法")
            recommendations.append("   - 收集证明工作能力的证据")
            recommendations.append("   - 主张违法解除赔偿金（经济补偿的二倍）")
        
        # 时效提醒
        recommendations.append("")
        recommendations.append("3. 时效提醒：")
        recommendations.append("   - 劳动争议仲裁时效为1年，从知道或应当知道权利被侵害之日起计算")
        recommendations.append("   - 建议尽快申请仲裁，避免超过时效")
        
        # 专业建议
        recommendations.append("")
        recommendations.append("4. 专业建议：")
        recommendations.append("   - 建议咨询专业劳动法律师")
        recommendations.append("   - 可考虑先与公司协商解决")
        recommendations.append("   - 保留所有证据原件")
        
        return recommendations
    
    def _generate_action_plan(self, case_info: Dict[str, Any], evidence_list: Dict[str, Any], 
                             analysis_results: List[Dict[str, Any]]) -> List[str]:
        """生成行动计划
        
        Args:
            case_info: 案件信息
            evidence_list: 证据清单
            analysis_results: 分析结果
            
        Returns:
            行动计划
        """
        action_plan = []
        
        # 短期行动（1-2周）
        action_plan.append("短期行动（1-2周内）：")
        action_plan.append("1. 完善证据收集，重点收集核心证据")
        action_plan.append("2. 整理所有相关材料，制作证据清单")
        action_plan.append("3. 咨询专业律师，制定详细维权策略")
        action_plan.append("")
        
        # 中期行动（2-4周）
        action_plan.append("中期行动（2-4周内）：")
        action_plan.append("1. 尝试与公司协商解决")
        action_plan.append("2. 如协商不成，准备仲裁申请材料")
        action_plan.append("3. 到劳动仲裁委员会了解申请流程")
        action_plan.append("")
        
        # 长期行动（1-3个月）
        action_plan.append("长期行动（1-3个月内）：")
        action_plan.append("1. 正式提起劳动仲裁申请")
        action_plan.append("2. 积极参与仲裁程序")
        action_plan.append("3. 根据仲裁结果决定是否上诉")
        
        return action_plan
    
    def _calculate_evidence_statistics(self, evidence_list: Dict[str, Any], 
                                      analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算证据统计信息
        
        Args:
            evidence_list: 证据清单
            analysis_results: 分析结果
            
        Returns:
            统计信息
        """
        evidence_items = evidence_list.get('evidence_items', [])
        
        stats = {
            'total_evidence': len(evidence_items),
            'core_evidence': len([item for item in evidence_items if item.get('importance') == '核心']),
            'important_evidence': len([item for item in evidence_items if item.get('importance') == '重要']),
            'auxiliary_evidence': len([item for item in evidence_items if item.get('importance') == '辅助']),
            'collected_evidence': len([item for item in evidence_items if item.get('status') == '已收集']),
            'analyzed_evidence': len(analysis_results),
            'valid_evidence': len([r for r in analysis_results if r.get('analysis_result', {}).get('是否可以作为核心证据') == '是'])
        }
        
        # 计算完成率
        if stats['total_evidence'] > 0:
            stats['collection_rate'] = stats['collected_evidence'] / stats['total_evidence']
        else:
            stats['collection_rate'] = 0.0
        
        return stats
    
    def _get_legal_basis(self, case_info: Dict[str, Any]) -> List[str]:
        """获取法律依据
        
        Args:
            case_info: 案件信息
            
        Returns:
            法律依据列表
        """
        legal_basis = []
        
        dispute_type = case_info.get('dispute_info', {}).get('type', '')
        
        if '违法解除' in dispute_type:
            legal_basis.extend([
                "《劳动合同法》第39条 - 用人单位可以解除劳动合同的情形",
                "《劳动合同法》第40条 - 用人单位提前三十日通知解除的情形",
                "《劳动合同法》第87条 - 违法解除的法律责任",
                "《劳动合同法》第47条 - 经济补偿的计算"
            ])
        
        # 通用法律依据
        legal_basis.extend([
            "《劳动争议调解仲裁法》 - 争议处理程序",
            "《劳动法》 - 基本劳动权益保护"
        ])
        
        return legal_basis
    
    def _assess_case_strength(self, case_info: Dict[str, Any], evidence_list: Dict[str, Any], 
                             analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估案件强度
        
        Args:
            case_info: 案件信息
            evidence_list: 证据清单
            analysis_results: 分析结果
            
        Returns:
            案件强度评估
        """
        # 简单的评估逻辑
        strength_score = 0.5  # 基础分数
        
        # 根据争议类型调整
        dispute_info = case_info.get('dispute_info', {})
        if '违法解除' in dispute_info.get('type', ''):
            if not dispute_info.get('has_training', False):
                strength_score += 0.2
            if not dispute_info.get('has_evidence', False):
                strength_score += 0.2
        
        # 根据证据情况调整
        if analysis_results:
            valid_evidence_rate = len([r for r in analysis_results if r.get('analysis_result', {}).get('是否可以作为核心证据') == '是']) / len(analysis_results)
            strength_score += valid_evidence_rate * 0.3
        
        strength_score = min(1.0, max(0.0, strength_score))
        
        if strength_score >= 0.8:
            strength_level = "强"
        elif strength_score >= 0.6:
            strength_level = "中等"
        else:
            strength_level = "弱"
        
        return {
            'score': strength_score,
            'level': strength_level,
            'description': f"基于现有证据和案件情况，案件强度评估为{strength_level}（{strength_score:.1f}/1.0）"
        }
    
    def _get_evidence_recommendations(self, evidence_list: Dict[str, Any]) -> List[str]:
        """获取证据收集建议
        
        Args:
            evidence_list: 证据清单
            
        Returns:
            证据建议列表
        """
        recommendations = []
        
        evidence_items = evidence_list.get('evidence_items', [])
        uncollected_core = [item for item in evidence_items 
                           if item.get('importance') == '核心' and item.get('status') != '已收集']
        
        if uncollected_core:
            recommendations.append("优先收集以下核心证据：")
            for item in uncollected_core:
                recommendations.append(f"- {item.get('type', '未知')}: {item.get('collection_method', '无方法')}")
        
        return recommendations
    
    def _get_legal_strategy(self, case_info: Dict[str, Any]) -> List[str]:
        """获取法律策略
        
        Args:
            case_info: 案件信息
            
        Returns:
            法律策略列表
        """
        strategy = []
        
        dispute_type = case_info.get('dispute_info', {}).get('type', '')
        
        if '违法解除' in dispute_type:
            strategy.extend([
                "主张公司违法解除劳动合同",
                "要求支付违法解除赔偿金（经济补偿的二倍）",
                "证明公司解除程序不当",
                "收集证明工作能力的证据"
            ])
        
        return strategy
    
    def generate_summary_report(self, case_id: str, report_data: Dict[str, Any]) -> Optional[str]:
        """生成摘要报告
        
        Args:
            case_id: 案件ID
            report_data: 报告数据
            
        Returns:
            摘要报告路径
        """
        try:
            case_info = report_data.get('case_info', {})
            evidence_list = report_data.get('evidence_list', {})
            analysis_results = report_data.get('analysis_results', [])
            
            summary_lines = []
            
            # 标题
            summary_lines.append("AI劳动法律师举证分析摘要报告")
            summary_lines.append("="*50)
            summary_lines.append(f"案件ID: {case_id}")
            summary_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            summary_lines.append("")
            
            # 案件概况
            basic_info = case_info.get('basic_info', {})
            dispute_info = case_info.get('dispute_info', {})
            
            summary_lines.append("案件概况:")
            summary_lines.append(f"- 公司: {basic_info.get('company_name', '未知')}")
            summary_lines.append(f"- 争议类型: {dispute_info.get('type', '未知')}")
            summary_lines.append(f"- 月薪: {basic_info.get('monthly_salary', '未知')}元")
            summary_lines.append("")
            
            # 证据统计
            stats = self._calculate_evidence_statistics(evidence_list, analysis_results)
            summary_lines.append("证据统计:")
            summary_lines.append(f"- 总证据数: {stats['total_evidence']}")
            summary_lines.append(f"- 核心证据: {stats['core_evidence']}")
            summary_lines.append(f"- 已收集: {stats['collected_evidence']}")
            summary_lines.append(f"- 收集率: {stats['collection_rate']:.1%}")
            summary_lines.append("")
            
            # 案件强度评估
            strength = self._assess_case_strength(case_info, evidence_list, analysis_results)
            summary_lines.append(f"案件强度: {strength['level']} ({strength['score']:.1f}/1.0)")
            summary_lines.append("")
            
            # 关键建议
            summary_lines.append("关键建议:")
            if stats['collection_rate'] < 0.8:
                summary_lines.append("- 加强证据收集工作")
            if stats['valid_evidence'] < stats['core_evidence']:
                summary_lines.append("- 重点收集核心证据")
            summary_lines.append("- 尽快咨询专业律师")
            summary_lines.append("- 注意仲裁时效")
            
            summary_content = "\n".join(summary_lines)
            
            # 保存摘要报告
            return self._save_report(case_id + "_summary", summary_content, 'text')
            
        except Exception as e:
            print(f"生成摘要报告失败: {e}")
            return None