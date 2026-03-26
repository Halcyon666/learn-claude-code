# S01 Agent Loop - Silicon Flow API 配置说明

## 概述

本文档记录了如何将 S01 Agent Loop 程序配置为使用 Silicon Flow 提供的 OpenAI 兼容 API，以及相关的代码调整。

## 背景

原始程序使用 Anthropic SDK 与 Claude API 通信。为了使用 Silicon Flow 的模型服务，需要将底层 SDK 从 Anthropic 切换到 OpenAI。

## 调整内容

### 1. 依赖库更换

**文件：requirements.txt**

```diff
- anthropic>=0.25.0
+ openai>=1.0.0
```

**原因：** Silicon Flow 提供 OpenAI 兼容的 API 接口，而不是 Anthropic 兼容的。

### 2. 环境配置

**文件：.env**

```bash
# Silicon Flow API Configuration (OpenAI Compatible)
OPENAI_BASE_URL=https://api.siliconflow.cn/
OPENAI_API_KEY=sk-your-api-key-here
MODEL_ID=Pro/zai-org/GLM-4.7
```

**关键点：**

- 使用 `OPENAI_` 前缀而非 `ANTHROPIC_`
- 基础 URL：`https://api.siliconflow.cn/`
- 模型 ID：`Pro/zai-org/GLM-4.7`（Silicon Flow 的 GLM 模型）

### 3. 代码改动

#### 3.1 导入变更

**s01_agent_loop.py**

```python
# 旧
from anthropic import Anthropic

# 新
from openai import OpenAI
import json
```

#### 3.2 客户端初始化

```python
# 旧
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))

# 新
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)
```

#### 3.3 工具定义格式

**旧格式（Anthropic）：**

```python
TOOLS = [{
    "name": "bash",
    "description": "Run a shell command.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]
```

**新格式（OpenAI）：**

```python
TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "The shell command to run"}},
            "required": ["command"],
        },
    }
}]
```

#### 3.4 Agent Loop 函数

**主要变更：**

1. **API 调用方式**

```python
# 旧：Anthropic API
response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)

# 新：OpenAI API
all_messages = [{"role": "system", "content": SYSTEM}] + messages
response = client.chat.completions.create(
    model=MODEL,
    messages=all_messages,
    tools=TOOLS,
    max_tokens=8000,
)
```

2. **系统提示处理**

- 旧：作为 `system` 参数传递
- 新：作为消息列表的第一条消息（`{"role": "system", ...}`）

3. **工具结果处理**

```python
# 旧：Anthropic 格式
results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
messages.append({"role": "user", "content": results})

# 新：OpenAI 格式
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": output
})
```

4. **工具调用解析**

```python
# 旧：Anthropic 块结构
for block in response.content:
    if block.type == "tool_use":
        command = block.input['command']

# 新：OpenAI 工具调用
for tool_call in assistant_msg.tool_calls:
    if tool_call.function.name == "bash":
        command = json.loads(tool_call.function.arguments).get("command", "")
```

## 验证

可以使用以下命令验证配置是否正确：

```bash
python test_api.py
```

成功输出应为：

```
Configuration:
  Base URL: https://api.siliconflow.cn/
  API Key: sk-...
  Model: Pro/zai-org/GLM-4.7

Testing API call...
✓ API call successful!
Response: OK
```

## 使用示例

运行 agent 程序：

```bash
python -m agents.s01_agent_loop
```

输入任务（例如）：

```
s01 >> Create a file called hello.py that prints 'Hello, World!'
```

Agent 会自动执行 bash 命令来完成任务。

## 注意事项

1. **API Key 安全**：不要将真实的 API Key 提交到版本控制系统，使用 `.env` 文件
2. **模型可用性**：确保 Silicon Flow 账户有 `Pro/zai-org/GLM-4.7` 模型的访问权限
3. **速率限制**：留意 Silicon Flow 的 API 速率限制和配额
4. **错误处理**：如遇 404 错误，检查 API Key 和基础 URL 是否正确

## 后续改进方向

- [ ] 添加更详细的错误处理和重试机制
- [ ] 支持多个模型切换
- [ ] 添加令牌计数和成本估算
- [ ] 实现流式响应支持
