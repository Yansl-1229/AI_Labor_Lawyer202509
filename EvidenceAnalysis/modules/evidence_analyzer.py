#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证据分析评估模块

功能：
1. 调用6个证据分析接口进行专业评估
2. 统一处理不同类型证据的分析请求
3. 解析和标准化分析结果
4. 提供证据有效性评估和改进建议
"""

import os
import requests
import time
from typing import Dict, List, Optional, Any
from datetime import datetime


class APICallError(Exception):
    """API调用错误"""
    pass


class FileFormatError(Exception):
    """文件格式错误"""
    pass


class EvidenceAnalyzer:
    """证据分析评估器"""
    
    def __init__(self):
        """初始化分析器"""
        # 证据分析接口映射
        self.endpoints = {
            'contract': 'http://localhost:8001/analyze_contract',
            'payslip': 'http://localhost:8002/analyze-payslip',
            'attendance': 'http://localhost:8003/analyze_attendance',
            'injury': 'http://localhost:8004/analyze_injury_assessment',
            'recording': 'http://localhost:8005/analyze_recording',
            'chat': 'http://localhost:8006/analyze_single'
        }
        
        # 参数名映射
        self.param_map = {
            'contract': 'file',
            'payslip': 'file',
            'attendance': 'attendance_file',
            'injury': 'attendance_file',
            'recording': 'Record_file',
            'chat': 'file'
        }
        
        # 支持的文件格式
        self.supported_formats = {
            'contract': ['.pdf', '.docx', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.zip'],
            'payslip': ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
            'attendance': ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
            'injury': ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
            'recording': ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'],
            'chat': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        }
        
        # 请求超时设置
        self.timeout = 30
        self.max_retries = 3
    
    def analyze_evidence(self, file_path: str, evidence_type: str) -> Optional[Dict[str, Any]]:
        """分析证据文件
        
        Args:
            file_path: 证据文件路径
            evidence_type: 证据类型 (contract/payslip/attendance/injury/recording/chat)
            
        Returns:
            分析结果字典，失败返回None
        """
        try:
            # 验证输入参数
            if not self._validate_input(file_path, evidence_type):
                return None
            
            # 验证文件格式
            if not self._validate_file_format(file_path, evidence_type):
                return None
            
            # 调用相应的分析接口
            result = self._call_analysis_api(file_path, evidence_type)
            
            if result:
                # 标准化分析结果
                standardized_result = self._standardize_result(result, evidence_type)
                
                # 添加分析元数据
                standardized_result['analysis_metadata'] = {
                    'file_path': file_path,
                    'evidence_type': evidence_type,
                    'analysis_time': datetime.now().isoformat(),
                    'analyzer_version': '1.0.0'
                }
                
                return standardized_result
            
            return None
            
        except Exception as e:
            print(f"证据分析失败: {e}")
            return None
    
    def _validate_input(self, file_path: str, evidence_type: str) -> bool:
        """验证输入参数
        
        Args:
            file_path: 文件路径
            evidence_type: 证据类型
            
        Returns:
            验证是否通过
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"错误：文件不存在 {file_path}")
            return False
        
        # 检查证据类型是否支持
        if evidence_type not in self.endpoints:
            print(f"错误：不支持的证据类型 {evidence_type}")
            print(f"支持的类型: {list(self.endpoints.keys())}")
            return False
        
        # 检查文件大小（限制为50MB）
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            print(f"错误：文件过大 {file_size / 1024 / 1024:.1f}MB，最大支持50MB")
            return False
        
        return True
    
    def _validate_file_format(self, file_path: str, evidence_type: str) -> bool:
        """验证文件格式
        
        Args:
            file_path: 文件路径
            evidence_type: 证据类型
            
        Returns:
            格式是否支持
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        supported_formats = self.supported_formats.get(evidence_type, [])
        
        if file_ext not in supported_formats:
            print(f"错误：不支持的文件格式 {file_ext}")
            print(f"证据类型 {evidence_type} 支持的格式: {supported_formats}")
            return False
        
        return True
    
    def _call_analysis_api(self, file_path: str, evidence_type: str) -> Optional[Dict[str, Any]]:
        """调用分析API
        
        Args:
            file_path: 文件路径
            evidence_type: 证据类型
            
        Returns:
            API响应结果
        """
        url = self.endpoints.get(evidence_type)
        param_name = self.param_map.get(evidence_type)
        
        if not url or not param_name:
            print(f"错误：无法找到证据类型 {evidence_type} 的接口配置")
            return None
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                print(f"正在调用分析接口 (尝试 {attempt + 1}/{self.max_retries})...")
                
                with open(file_path, 'rb') as f:
                    files = {param_name: f}
                    
                    response = requests.post(
                        url,
                        files=files,
                        timeout=self.timeout
                    )
                
                # 检查HTTP状态码
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print("分析接口调用成功")
                        return result
                    except ValueError as e:
                        print(f"错误：响应不是有效的JSON格式 {e}")
                        return None
                else:
                    print(f"错误：HTTP状态码 {response.status_code}")
                    print(f"响应内容: {response.text[:200]}")
                    
                    # 如果是服务器错误，尝试重试
                    if response.status_code >= 500 and attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避
                        print(f"服务器错误，{wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue
                    
                    return None
            
            except requests.exceptions.Timeout:
                print(f"错误：请求超时 ({self.timeout}秒)")
                if attempt < self.max_retries - 1:
                    print("正在重试...")
                    time.sleep(2)
                    continue
                return None
            
            except requests.exceptions.ConnectionError:
                print(f"错误：无法连接到分析服务 {url}")
                print("请确保分析服务正在运行")
                if attempt < self.max_retries - 1:
                    print("正在重试...")
                    time.sleep(2)
                    continue
                return None
            
            except Exception as e:
                print(f"错误：API调用失败 {e}")
                if attempt < self.max_retries - 1:
                    print("正在重试...")
                    time.sleep(2)
                    continue
                return None
        
        print(f"所有重试尝试都失败了")
        return None
    
    def _standardize_result(self, result: Dict[str, Any], evidence_type: str) -> Dict[str, Any]:
        """标准化分析结果
        
        Args:
            result: 原始分析结果
            evidence_type: 证据类型
            
        Returns:
            标准化的结果
        """
        standardized = {
            'evidence_type': evidence_type,
            'file_type': result.get('文件类型', '未知'),
            'is_valid_evidence': self._parse_validity(result),
            'effectiveness_score': self._calculate_effectiveness_score(result),
            'key_information': self._extract_key_information(result, evidence_type),
            'validity_explanation': result.get('文件有效性说明', ''),
            'case_relevance': result.get('与案件关联性分析', ''),
            'recommendations': self._generate_recommendations(result, evidence_type),
            'raw_result': result
        }
        
        return standardized
    
    def _parse_validity(self, result: Dict[str, Any]) -> bool:
        """解析证据有效性
        
        Args:
            result: 分析结果
            
        Returns:
            是否为有效证据
        """
        # 检查不同的有效性字段
        validity_fields = [
            '是否可以作为核心证据',
            '是否可以作为证据',
            '是否可以作为有效证据'
        ]
        
        for field in validity_fields:
            if field in result:
                value = result[field]
                if isinstance(value, str):
                    return value.strip() == '是'
                elif isinstance(value, bool):
                    return value
        
        # 如果没有明确的有效性字段，根据其他信息判断
        validity_explanation = result.get('文件有效性说明', '')
        if '有效' in validity_explanation and '无效' not in validity_explanation:
            return True
        elif '无效' in validity_explanation:
            return False
        
        # 默认认为是有效的
        return True
    
    def _calculate_effectiveness_score(self, result: Dict[str, Any]) -> float:
        """计算证据有效性评分
        
        Args:
            result: 分析结果
            
        Returns:
            有效性评分 (0-1)
        """
        score = 0.5  # 基础分数
        
        # 根据是否为核心证据调整分数
        if result.get('是否可以作为核心证据') == '是':
            score += 0.3
        elif result.get('是否可以作为证据') == '是':
            score += 0.2
        
        # 根据文件完整性调整分数
        validity_explanation = result.get('文件有效性说明', '')
        if '完整' in validity_explanation:
            score += 0.1
        if '清晰' in validity_explanation:
            score += 0.1
        if '规范' in validity_explanation:
            score += 0.1
        
        # 根据关键信息是否齐全调整分数
        key_fields = ['主体公司名称', '合同起始日期', '约定薪资', '鉴定日期', '鉴定机构']
        complete_fields = sum(1 for field in key_fields if result.get(field) and result.get(field) != '')
        if complete_fields > 0:
            score += (complete_fields / len(key_fields)) * 0.2
        
        return min(1.0, max(0.0, score))
    
    def _extract_key_information(self, result: Dict[str, Any], evidence_type: str) -> Dict[str, Any]:
        """提取关键信息
        
        Args:
            result: 分析结果
            evidence_type: 证据类型
            
        Returns:
            关键信息字典
        """
        key_info = {}
        
        # 通用字段
        common_fields = ['主体公司名称', '文件内容']
        for field in common_fields:
            if field in result:
                key_info[field] = result[field]
        
        # 根据证据类型提取特定字段
        if evidence_type == 'contract':
            contract_fields = ['合同起始日期', '合同有效期', '约定薪资', '关键信息摘要']
            for field in contract_fields:
                if field in result:
                    key_info[field] = result[field]
        
        elif evidence_type == 'payslip':
            payslip_fields = ['起始日期', '结束日期', '平均薪资']
            for field in payslip_fields:
                if field in result:
                    key_info[field] = result[field]
        
        elif evidence_type == 'attendance':
            attendance_fields = ['起始日期', '结束日期']
            for field in attendance_fields:
                if field in result:
                    key_info[field] = result[field]
        
        elif evidence_type == 'injury':
            injury_fields = ['鉴定机构', '鉴定日期']
            for field in injury_fields:
                if field in result:
                    key_info[field] = result[field]
        
        elif evidence_type == 'recording':
            recording_fields = ['关键内容摘要']
            for field in recording_fields:
                if field in result:
                    key_info[field] = result[field]
        
        elif evidence_type == 'chat':
            # 聊天记录通常只有文件内容
            pass
        
        return key_info
    
    def _generate_recommendations(self, result: Dict[str, Any], evidence_type: str) -> List[str]:
        """生成改进建议
        
        Args:
            result: 分析结果
            evidence_type: 证据类型
            
        Returns:
            建议列表
        """
        recommendations = []
        
        # 基于有效性生成建议
        if not self._parse_validity(result):
            recommendations.append("该证据可能无法作为有效证据使用，建议寻找其他证据材料")
        
        # 基于完整性生成建议
        validity_explanation = result.get('文件有效性说明', '')
        if '不完整' in validity_explanation:
            recommendations.append("文件信息不完整，建议补充相关材料")
        
        if '不清晰' in validity_explanation:
            recommendations.append("文件不够清晰，建议提供更高质量的扫描件或照片")
        
        # 基于证据类型生成特定建议
        if evidence_type == 'contract':
            if not result.get('主体公司名称'):
                recommendations.append("合同中公司名称不清晰，建议核实公司全称")
            if not result.get('约定薪资'):
                recommendations.append("合同中薪资条款不明确，建议查找薪资补充协议")
        
        elif evidence_type == 'payslip':
            if not result.get('平均薪资'):
                recommendations.append("工资单中薪资信息不完整，建议收集更多期间的工资单")
        
        elif evidence_type == 'injury':
            if not result.get('鉴定机构'):
                recommendations.append("鉴定机构信息缺失，建议确认鉴定机构的权威性")
        
        # 通用建议
        if result.get('是否可以作为核心证据') != '是':
            recommendations.append("建议同时收集其他相关证据以加强证明力")
        
        # 如果没有生成任何建议，添加默认建议
        if not recommendations:
            if self._parse_validity(result):
                recommendations.append("证据材料符合要求，建议妥善保管原件")
            else:
                recommendations.append("建议咨询专业律师以获取更详细的证据指导")
        
        return recommendations
    
    def analyze_multiple_evidence(self, file_paths: List[str], evidence_types: List[str]) -> List[Dict[str, Any]]:
        """批量分析多个证据文件
        
        Args:
            file_paths: 文件路径列表
            evidence_types: 对应的证据类型列表
            
        Returns:
            分析结果列表
        """
        if len(file_paths) != len(evidence_types):
            print("错误：文件路径和证据类型数量不匹配")
            return []
        
        results = []
        
        for i, (file_path, evidence_type) in enumerate(zip(file_paths, evidence_types)):
            print(f"\n正在分析第 {i + 1}/{len(file_paths)} 个文件: {os.path.basename(file_path)}")
            
            result = self.analyze_evidence(file_path, evidence_type)
            if result:
                results.append(result)
            else:
                print(f"文件 {file_path} 分析失败")
        
        return results
    
    def get_analysis_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取分析结果摘要
        
        Args:
            results: 分析结果列表
            
        Returns:
            摘要信息
        """
        if not results:
            return {'total': 0, 'valid': 0, 'invalid': 0, 'average_score': 0.0}
        
        total = len(results)
        valid = sum(1 for r in results if r.get('is_valid_evidence', False))
        invalid = total - valid
        
        scores = [r.get('effectiveness_score', 0.0) for r in results]
        average_score = sum(scores) / len(scores) if scores else 0.0
        
        evidence_types = {}
        for result in results:
            evidence_type = result.get('evidence_type', '未知')
            evidence_types[evidence_type] = evidence_types.get(evidence_type, 0) + 1
        
        return {
            'total': total,
            'valid': valid,
            'invalid': invalid,
            'validity_rate': valid / total if total > 0 else 0.0,
            'average_score': average_score,
            'evidence_types': evidence_types
        }
    
    def check_service_status(self) -> Dict[str, bool]:
        """检查各个分析服务的状态
        
        Returns:
            服务状态字典
        """
        status = {}
        
        for evidence_type, url in self.endpoints.items():
            try:
                # 发送简单的GET请求检查服务状态
                response = requests.get(url.replace('/analyze', '/health'), timeout=5)
                status[evidence_type] = response.status_code == 200
            except:
                status[evidence_type] = False
        
        return status