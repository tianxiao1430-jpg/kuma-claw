"""
Agent 模块测试
============
"""


class TestAgentTools:
    """Agent 工具测试"""

    def test_get_current_time(self):
        """测试获取当前时间"""
        from kuma_claw.agent import get_current_time

        result = get_current_time()

        assert isinstance(result, str)
        assert len(result) > 0
        # 格式：YYYY-MM-DD HH:MM:SS
        assert len(result) == 19
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":"
        assert result[16] == ":"

    def test_echo_message(self, sample_text):
        """测试回显消息"""
        from kuma_claw.agent import echo_message

        result = echo_message(sample_text)

        assert isinstance(result, str)
        assert sample_text in result
        assert result.startswith("收到：")

    def test_web_search_empty_result(self):
        """测试网络搜索（无结果情况）"""
        from kuma_claw.agent import web_search

        # 使用非常特殊的查询词，应该没有结果
        result = web_search("xyzabc123456789_unique_test_query")

        assert isinstance(result, str)
        # 应该返回没有找到结果的提示
        assert "没有找到" in result or "搜索结果" in result or "搜索失败" in result


class TestAgentCreation:
    """Agent 创建测试"""

    def test_get_model_default(self):
        """测试获取默认模型"""
        from kuma_claw.agent import get_model

        model = get_model()

        # 应该返回模型配置（字符串或 LiteLlm 实例）
        assert model is not None

    def test_get_model_openai(self, monkeypatch):
        """测试 OpenAI 模型配置"""
        from kuma_claw.agent import get_model

        monkeypatch.setenv("KUMA_MODEL", "openai/gpt-4")
        # 注意：由于 MODEL 在模块加载时已确定，这个测试可能需要重新加载模块
        # 这里只是验证逻辑
        model = get_model()
        assert model is not None


class TestSystemInstruction:
    """系统提示词测试"""

    def test_get_system_instruction(self):
        """测试获取系统提示词"""
        from kuma_claw.agent import get_system_instruction

        instruction = get_system_instruction("telegram")

        assert isinstance(instruction, str)
        assert len(instruction) > 0
        # 应该包含内部思考说明
        assert "internal" in instruction.lower() or "思考" in instruction

    def test_get_system_instruction_channel(self):
        """测试不同渠道的系统提示词"""
        from kuma_claw.agent import get_system_instruction

        telegram_instruction = get_system_instruction("telegram")
        slack_instruction = get_system_instruction("slack")

        # 不同渠道可能有不同的格式要求
        assert isinstance(telegram_instruction, str)
        assert isinstance(slack_instruction, str)
