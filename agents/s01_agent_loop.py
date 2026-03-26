#!/usr/bin/env python3
# Harness: the loop -- the model's first connection to the real world.
"""
s01_agent_loop.py - The Agent Loop

The entire secret of an AI coding agent in one pattern:

    while stop_reason == "tool_use":
        response = LLM(messages, tools)
        execute tools
        append results

    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> |  Tool   |
    |  prompt  |      |       |      | execute |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                          (loop continues)

This is the core loop: feed tool results back to the model
until the model decides to stop. Production agents layer
policy, hooks, and lifecycle controls on top.
"""

import os
import subprocess
import json

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# Initialize OpenAI client with Silicon Flow
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

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


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


# -- The core pattern: a while loop that calls tools until the model stops --
def agent_loop(messages: list):
    # Prepare messages with system prompt
    all_messages = [{"role": "system", "content": SYSTEM}] + messages
    
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=all_messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        
        # Get the assistant's message
        assistant_msg = response.choices[0].message
        
        # Append assistant turn to both lists
        assistant_content = {
            "role": "assistant",
            "content": assistant_msg.content or "",
        }
        if hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls:
            assistant_content["tool_calls"] = assistant_msg.tool_calls
        
        all_messages.append(assistant_content)
        messages.append(assistant_content)
        
        # If the model didn't call a tool, we're done
        if not (hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls):
            return
        
        # Execute each tool call, collect results
        for tool_call in assistant_msg.tool_calls:
            if tool_call.function.name == "bash":
                command = json.loads(tool_call.function.arguments).get("command", "")
                print(f"\033[33m$ {command}\033[0m")
                output = run_bash(command)
                print(output[:200])
                
                # Add tool result message
                tool_result_msg = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": output
                }
                all_messages.append(tool_result_msg)
                messages.append(tool_result_msg)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        # Print assistant response
        if history and history[-1]["role"] == "assistant":
            content = history[-1]["content"]
            if content:
                print(content)
        print()
