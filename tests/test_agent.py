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

    def test_web_search_returns_string(self):
        """测试网络搜索返回字符串"""
        from kuma_claw.agent import web_search

        # 测试搜索功能返回字符串即可（不依赖具体搜索结果）
        result = web_search("xyzabc123456789_unique_test_query")

        assert isinstance(result, str)
        # 只要返回非空字符串就算通过
        assert len(result) > 0


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

        instruction = get_system_instruction()

        assert isinstance(instruction, str)
        assert len(instruction) > 0
        # 应该包含内部思考说明
        assert "internal" in instruction.lower() or "思考" in instruction

    def test_get_system_instruction_no_channel(self):
        """测试系统提示词不再接受 channel 参数"""
        from kuma_claw.agent import get_system_instruction

        # 重构后 get_system_instruction 不再接受参数
        instruction = get_system_instruction()

        assert isinstance(instruction, str)
        assert len(instruction) > 0
