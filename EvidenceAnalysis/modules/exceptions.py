#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常处理模块

定义项目中使用的所有自定义异常类和错误处理机制
提供统一的错误处理和用户友好的错误信息
"""

import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any


class EvidenceAnalysisError(Exception):
    """证据分析异常基类
    
    所有项目相关异常的基类，提供统一的错误处理接口
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        """初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            错误信息字典
        """
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }
    
    def __str__(self) -> str:
        """字符串表示
        
        Returns:
            错误信息字符串
        """
        return f"[{self.error_code}] {self.message}"


class FileFormatError(EvidenceAnalysisError):
    """文件格式错误
    
    当文件格式不支持或文件损坏时抛出
    """
    
    def __init__(self, file_path: str, expected_formats: Optional[list] = None, 
                 actual_format: Optional[str] = None):
        """初始化文件格式错误
        
        Args:
            file_path: 文件路径
            expected_formats: 期望的文件格式列表
            actual_format: 实际文件格式
        """
        message = f"不支持的文件格式: {file_path}"
        if expected_formats:
            message += f"，支持的格式: {', '.join(expected_formats)}"
        if actual_format:
            message += f"，实际格式: {actual_format}"
        
        details = {
            'file_path': file_path,
            'expected_formats': expected_formats,
            'actual_format': actual_format
        }
        
        super().__init__(message, 'FILE_FORMAT_ERROR', details)


class APICallError(EvidenceAnalysisError):
    """API调用错误
    
    当调用外部API失败时抛出
    """
    
    def __init__(self, api_name: str, status_code: Optional[int] = None, 
                 response_text: Optional[str] = None, url: Optional[str] = None):
        """初始化API调用错误
        
        Args:
            api_name: API名称
            status_code: HTTP状态码
            response_text: 响应文本
            url: 请求URL
        """
        message = f"API调用失败: {api_name}"
        if status_code:
            message += f"，状态码: {status_code}"
        
        details = {
            'api_name': api_name,
            'status_code': status_code,
            'response_text': response_text[:200] if response_text else None,  # 限制长度
            'url': url
        }
        
        super().__init__(message, 'API_CALL_ERROR', details)


class DataParseError(EvidenceAnalysisError):
    """数据解析错误
    
    当解析JSON、文本或其他数据格式失败时抛出
    """
    
    def __init__(self, data_type: str, parse_error: Optional[str] = None, 
                 data_source: Optional[str] = None):
        """初始化数据解析错误
        
        Args:
            data_type: 数据类型
            parse_error: 解析错误信息
            data_source: 数据源
        """
        message = f"数据解析失败: {data_type}"
        if parse_error:
            message += f"，错误: {parse_error}"
        
        details = {
            'data_type': data_type,
            'parse_error': parse_error,
            'data_source': data_source
        }
        
        super().__init__(message, 'DATA_PARSE_ERROR', details)


class ConfigurationError(EvidenceAnalysisError):
    """配置错误
    
    当系统配置不正确时抛出
    """
    
    def __init__(self, config_item: str, expected_value: Optional[str] = None, 
                 actual_value: Optional[str] = None):
        """初始化配置错误
        
        Args:
            config_item: 配置项名称
            expected_value: 期望值
            actual_value: 实际值
        """
        message = f"配置错误: {config_item}"
        if expected_value:
            message += f"，期望: {expected_value}"
        if actual_value:
            message += f"，实际: {actual_value}"
        
        details = {
            'config_item': config_item,
            'expected_value': expected_value,
            'actual_value': actual_value
        }
        
        super().__init__(message, 'CONFIGURATION_ERROR', details)


class ValidationError(EvidenceAnalysisError):
    """数据验证错误
    
    当数据验证失败时抛出
    """
    
    def __init__(self, field_name: str, validation_rule: str, 
                 field_value: Optional[Any] = None):
        """初始化验证错误
        
        Args:
            field_name: 字段名称
            validation_rule: 验证规则
            field_value: 字段值
        """
        message = f"数据验证失败: {field_name}，规则: {validation_rule}"
        
        details = {
            'field_name': field_name,
            'validation_rule': validation_rule,
            'field_value': str(field_value) if field_value is not None else None
        }
        
        super().__init__(message, 'VALIDATION_ERROR', details)


class ServiceUnavailableError(EvidenceAnalysisError):
    """服务不可用错误
    
    当依赖的服务不可用时抛出
    """
    
    def __init__(self, service_name: str, reason: Optional[str] = None):
        """初始化服务不可用错误
        
        Args:
            service_name: 服务名称
            reason: 不可用原因
        """
        message = f"服务不可用: {service_name}"
        if reason:
            message += f"，原因: {reason}"
        
        details = {
            'service_name': service_name,
            'reason': reason
        }
        
        super().__init__(message, 'SERVICE_UNAVAILABLE_ERROR', details)


class EvidenceProcessingError(EvidenceAnalysisError):
    """证据处理错误
    
    当证据处理过程中发生错误时抛出
    """
    
    def __init__(self, evidence_type: str, processing_stage: str, 
                 error_details: Optional[str] = None):
        """初始化证据处理错误
        
        Args:
            evidence_type: 证据类型
            processing_stage: 处理阶段
            error_details: 错误详情
        """
        message = f"证据处理失败: {evidence_type}，阶段: {processing_stage}"
        if error_details:
            message += f"，详情: {error_details}"
        
        details = {
            'evidence_type': evidence_type,
            'processing_stage': processing_stage,
            'error_details': error_details
        }
        
        super().__init__(message, 'EVIDENCE_PROCESSING_ERROR', details)


class ReportGenerationError(EvidenceAnalysisError):
    """报告生成错误
    
    当生成报告失败时抛出
    """
    
    def __init__(self, report_type: str, generation_stage: str, 
                 error_details: Optional[str] = None):
        """初始化报告生成错误
        
        Args:
            report_type: 报告类型
            generation_stage: 生成阶段
            error_details: 错误详情
        """
        message = f"报告生成失败: {report_type}，阶段: {generation_stage}"
        if error_details:
            message += f"，详情: {error_details}"
        
        details = {
            'report_type': report_type,
            'generation_stage': generation_stage,
            'error_details': error_details
        }
        
        super().__init__(message, 'REPORT_GENERATION_ERROR', details)


class ErrorHandler:
    """错误处理器
    
    提供统一的错误处理和日志记录功能
    """
    
    def __init__(self, log_errors: bool = True, show_traceback: bool = False):
        """初始化错误处理器
        
        Args:
            log_errors: 是否记录错误日志
            show_traceback: 是否显示堆栈跟踪
        """
        self.log_errors = log_errors
        self.show_traceback = show_traceback
        self.error_log = []
    
    def handle_error(self, error: Exception, context: Optional[str] = None) -> Dict[str, Any]:
        """处理错误
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            错误信息字典
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'error_type': type(error).__name__,
            'message': str(error)
        }
        
        # 如果是自定义异常，获取详细信息
        if isinstance(error, EvidenceAnalysisError):
            error_info.update(error.to_dict())
        
        # 添加堆栈跟踪信息
        if self.show_traceback:
            error_info['traceback'] = traceback.format_exc()
        
        # 记录错误日志
        if self.log_errors:
            self.error_log.append(error_info)
        
        return error_info
    
    def get_user_friendly_message(self, error: Exception) -> str:
        """获取用户友好的错误消息
        
        Args:
            error: 异常对象
            
        Returns:
            用户友好的错误消息
        """
        if isinstance(error, FileFormatError):
            return "文件格式不支持，请检查文件类型并重新上传。"
        
        elif isinstance(error, APICallError):
            return "网络连接或服务异常，请稍后重试。如问题持续，请检查网络连接。"
        
        elif isinstance(error, DataParseError):
            return "数据格式错误，请检查文件内容是否完整和正确。"
        
        elif isinstance(error, ConfigurationError):
            return "系统配置错误，请检查环境变量设置。"
        
        elif isinstance(error, ValidationError):
            return "输入数据不符合要求，请检查并重新输入。"
        
        elif isinstance(error, ServiceUnavailableError):
            return "相关服务暂时不可用，请稍后重试。"
        
        elif isinstance(error, EvidenceProcessingError):
            return "证据处理过程中发生错误，请检查文件完整性。"
        
        elif isinstance(error, ReportGenerationError):
            return "报告生成失败，请稍后重试。"
        
        else:
            return "系统发生未知错误，请联系技术支持。"
    
    def get_error_suggestions(self, error: Exception) -> list:
        """获取错误解决建议
        
        Args:
            error: 异常对象
            
        Returns:
            解决建议列表
        """
        suggestions = []
        
        if isinstance(error, FileFormatError):
            suggestions.extend([
                "检查文件格式是否正确",
                "尝试转换文件格式",
                "确保文件没有损坏"
            ])
        
        elif isinstance(error, APICallError):
            suggestions.extend([
                "检查网络连接",
                "确认API服务正在运行",
                "稍后重试",
                "检查API密钥配置"
            ])
        
        elif isinstance(error, DataParseError):
            suggestions.extend([
                "检查文件内容格式",
                "确保文件编码正确",
                "验证JSON格式是否有效"
            ])
        
        elif isinstance(error, ConfigurationError):
            suggestions.extend([
                "检查环境变量设置",
                "确认配置文件存在",
                "验证配置项的值"
            ])
        
        elif isinstance(error, ServiceUnavailableError):
            suggestions.extend([
                "检查服务状态",
                "稍后重试",
                "联系系统管理员"
            ])
        
        else:
            suggestions.extend([
                "重新启动程序",
                "检查系统资源",
                "联系技术支持"
            ])
        
        return suggestions
    
    def print_error(self, error: Exception, context: Optional[str] = None):
        """打印错误信息
        
        Args:
            error: 异常对象
            context: 错误上下文
        """
        print(f"\n❌ 错误: {self.get_user_friendly_message(error)}")
        
        if context:
            print(f"📍 上下文: {context}")
        
        if isinstance(error, EvidenceAnalysisError):
            print(f"🔍 详细信息: {error.message}")
        
        suggestions = self.get_error_suggestions(error)
        if suggestions:
            print("💡 建议解决方案:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   {i}. {suggestion}")
        
        if self.show_traceback:
            print(f"\n🔧 技术详情:\n{traceback.format_exc()}")
    
    def get_error_log(self) -> list:
        """获取错误日志
        
        Returns:
            错误日志列表
        """
        return self.error_log.copy()
    
    def clear_error_log(self):
        """清空错误日志"""
        self.error_log.clear()
    
    def save_error_log(self, file_path: str):
        """保存错误日志到文件
        
        Args:
            file_path: 文件路径
        """
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.error_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存错误日志失败: {e}")


def handle_exception(func):
    """异常处理装饰器
    
    用于自动处理函数中的异常
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EvidenceAnalysisError as e:
            error_handler = ErrorHandler()
            error_handler.print_error(e, f"函数: {func.__name__}")
            return None
        except Exception as e:
            # 将未知异常包装为自定义异常
            wrapped_error = EvidenceAnalysisError(
                f"函数 {func.__name__} 执行失败: {str(e)}",
                'UNKNOWN_ERROR',
                {'function': func.__name__, 'original_error': str(e)}
            )
            error_handler = ErrorHandler()
            error_handler.print_error(wrapped_error, f"函数: {func.__name__}")
            return None
    
    return wrapper


def validate_file_path(file_path: str, required_extensions: Optional[list] = None):
    """验证文件路径
    
    Args:
        file_path: 文件路径
        required_extensions: 要求的文件扩展名列表
        
    Raises:
        FileFormatError: 文件格式错误
        ValidationError: 验证错误
    """
    import os
    
    if not file_path:
        raise ValidationError('file_path', '不能为空')
    
    if not os.path.exists(file_path):
        raise ValidationError('file_path', '文件不存在', file_path)
    
    if not os.path.isfile(file_path):
        raise ValidationError('file_path', '不是有效文件', file_path)
    
    if required_extensions:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in required_extensions:
            raise FileFormatError(file_path, required_extensions, file_ext)


def validate_api_response(response, expected_fields: Optional[list] = None):
    """验证API响应
    
    Args:
        response: API响应对象
        expected_fields: 期望的字段列表
        
    Raises:
        APICallError: API调用错误
        ValidationError: 验证错误
    """
    if not response:
        raise APICallError('unknown', None, 'Empty response')
    
    if hasattr(response, 'status_code') and response.status_code != 200:
        raise APICallError('unknown', response.status_code, 
                          getattr(response, 'text', 'No response text'))
    
    if expected_fields and hasattr(response, 'json'):
        try:
            data = response.json()
            for field in expected_fields:
                if field not in data:
                    raise ValidationError(field, '响应中缺少必要字段')
        except ValueError as e:
            raise DataParseError('JSON', str(e))


# 全局错误处理器实例
default_error_handler = ErrorHandler(log_errors=True, show_traceback=False)


def set_global_error_handler(handler: ErrorHandler):
    """设置全局错误处理器
    
    Args:
        handler: 错误处理器实例
    """
    global default_error_handler
    default_error_handler = handler


def get_global_error_handler() -> ErrorHandler:
    """获取全局错误处理器
    
    Returns:
        错误处理器实例
    """
    return default_error_handler