#!usr/bin/env python
"""
Senior Data Scientist/AI Engineering.: Dr. Eddy Giusepe Chirinos Isidro


Study Link ---> https://www.youtube.com/watch?v=z5ri1yBMIdA

RUM
---
uv run product_support_agent.py
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter
from langchain_openai import ChatOpenAI

load_dotenv()


async def main():
    model = ChatOpenAI(model="gpt-6-luna")

    async with MCPAdapter(Path(__file__).parent / "product_support_server.py") as adapter:
        tools = await adapter.list_tools()
        
        print("Minhas ferramentas disponíveis são: ")
        for tool in tools:
            print(f"  -  {tool.name}: {tool.description}")

        agent = create_agent(model, tools=tools)

        result = await agent.ainvoke({"messages": [
            {"role": "user",
             "content": "Os envios são de 5 a 10 dias?" # E como funciona a política para devolver o  produto?
            }]})

        # for message in result["messages"]:
        #    message.pretty_print()

        final_answer = result["messages"][-1].text
        print(final_answer)


if __name__ == "__main__":
    asyncio.run(main())
