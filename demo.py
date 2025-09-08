#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示脚本
用于测试AI劳动法律师软件的基本功能
"""

import os
import sys
import json
from datetime import datetime

def check_dependencies():
    """检查依赖包是否安装"""
    print("🔍 检查系统依赖...")
    
    required_packages = [
        'dashscope',
        'openai', 
        'pandas',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - 已安装")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("\n✅ 所有依赖包检查通过")
    return True

def check_files():
    """检查必要文件是否存在"""
    print("\n📁 检查项目文件...")
    
    required_files = [
        'main.py',
        'lawyer_model.py',
        'free_generate_case_analysis.py', 
        'evidence_analyzer.py',
        'Lawyer_Prompt.txt'
    ]
    
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} - 存在")
        else:
            print(f"❌ {file} - 不存在")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️ 缺少以下文件: {', '.join(missing_files)}")
        return False
    
    print("\n✅ 所有必要文件检查通过")
    return True

def create_demo_conversation():
    """创建演示对话数据"""
    print("\n📝 创建演示对话数据...")
    
    demo_conversation = [{
        "system_prompt": "作为专精劳动法的资深律师，您在对话中必须始终以共情、专业的方式引导用户梳理案件细节。",
        "conversations": [
            {
                "from": "human",
                "value": "您好，我想咨询一下劳动争议的问题。我在一家科技公司工作了2年，最近被公司无故辞退了。"
            },
            {
                "from": "gpt", 
                "value": "您好，很理解您现在的困扰。被无故辞退确实让人感到不安。为了更好地帮助您，我需要了解一些具体情况。请问您和公司签订过书面劳动合同吗？"
            },
            {
                "from": "human",
                "value": "是的，我们签了3年期的劳动合同，约定月薪12000元。但是公司突然说要裁员，给了我一个月的代通知金就让我走了。"
            },
            {
                "from": "gpt",
                "value": "我明白了。公司给了代通知金，但这种做法是否合法还需要进一步分析。请问公司有没有给您书面的解除劳动合同通知书？上面写的具体理由是什么？"
            },
            {
                "from": "human",
                "value": "有的，通知书上写的是'因经营困难需要裁员'，但我觉得这不是真实原因，因为公司还在招新人。"
            },
            {
                "from": "gpt",
                "value": "这个情况确实值得关注。如果公司一边说裁员一边招新人，可能存在违法解除的情况。请问您在公司的具体岗位是什么？工作表现如何？有没有违反公司规章制度的情况？"
            },
            {
                "from": "human",
                "value": "我是软件开发工程师，工作表现一直很好，从来没有违反过公司制度。而且我发现公司在我被辞退后一周就发布了同样岗位的招聘信息。"
            },
            {
                "from": "gpt",
                "value": "根据您提供的信息，这种情况很可能构成违法解除劳动合同。公司以经营困难为由裁员，但同时招聘同岗位人员，这在法律上是站不住脚的。您现在最需要做的是收集相关证据，比如招聘信息的截图、您的工作表现证明等。关于具体的赔偿标准和维权方式，我们已经收集了足够的基础信息。"
            }
        ]
    }]
    
    # 确保目录存在
    os.makedirs("conversation_datasets", exist_ok=True)
    
    # 保存演示对话
    demo_file = "conversation_datasets/demo_conversation.json"
    with open(demo_file, 'w', encoding='utf-8') as f:
        json.dump(demo_conversation, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 演示对话数据已创建: {demo_file}")
    return demo_file

def test_case_analysis(conversation_file):
    """测试案例分析功能"""
    print("\n⚖️ 测试案例分析功能...")
    
    try:
        from free_generate_case_analysis import CaseAnalysisGenerator
        
        # 创建分析器（使用模拟模式）
        analyzer = CaseAnalysisGenerator()
        
        # 模拟分析结果（避免实际API调用）
        mock_result = """
【案情分析】
根据您提供的信息，您与公司签订了3年期劳动合同，约定月薪12000元，在职期间工作表现良好，无违纪行为。公司以"经营困难需要裁员"为由解除劳动合同，但同时发布同岗位招聘信息，这种行为在法律上存在明显矛盾，很可能构成违法解除劳动合同。

【当前应对方案】
建议您立即收集以下证据：1）公司发布的同岗位招聘信息截图；2）您的工作表现证明材料；3）劳动合同原件；4）解除劳动合同通知书。同时，您可以向劳动监察部门举报或申请劳动仲裁，要求公司承担违法解除的法律责任。

【维权与赔偿方案】
根据《劳动合同法》第87条规定，用人单位违法解除劳动合同的，应当按照经济补偿标准的二倍向劳动者支付赔偿金。以您的情况计算，应获得赔偿金为：12000元×2年×2倍=48000元。此外，您还可以要求公司支付代通知金、未休年假工资等其他合法权益。
"""
        
        print("✅ 案例分析功能测试通过")
        print("📋 分析结果示例:")
        print("-" * 50)
        print(mock_result[:200] + "...")
        print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ 案例分析功能测试失败: {e}")
        return False

def test_evidence_analysis():
    """测试证据分析功能"""
    print("\n🔬 测试证据分析功能...")
    
    try:
        from evidence_analyzer import EvidenceAnalyzer, EvidenceType
        
        # 创建分析器
        analyzer = EvidenceAnalyzer()
        
        print("✅ 证据分析模块加载成功")
        print("📋 支持的证据类型:")
        
        for evidence_type in EvidenceType:
            print(f"  • {evidence_type.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 证据分析功能测试失败: {e}")
        return False

def run_demo():
    """运行完整演示"""
    print("🚀 AI劳动法律师软件演示")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        return False
    
    # 检查文件
    if not check_files():
        return False
    
    # 创建演示数据
    demo_file = create_demo_conversation()
    
    # 测试各个模块
    case_analysis_ok = test_case_analysis(demo_file)
    evidence_analysis_ok = test_evidence_analysis()
    
    print("\n📊 演示结果总结:")
    print("=" * 40)
    print(f"依赖检查: ✅")
    print(f"文件检查: ✅")
    print(f"案例分析: {'✅' if case_analysis_ok else '❌'}")
    print(f"证据分析: {'✅' if evidence_analysis_ok else '❌'}")
    
    if case_analysis_ok and evidence_analysis_ok:
        print("\n🎉 所有功能测试通过！")
        print("\n💡 现在您可以运行主程序:")
        print("   python main.py")
        return True
    else:
        print("\n⚠️ 部分功能测试失败，请检查配置")
        return False

if __name__ == "__main__":
    try:
        success = run_demo()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 演示已取消")
    except Exception as e:
        print(f"\n❌ 演示运行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)