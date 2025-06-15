import asyncio
from dotenv import load_dotenv
load_dotenv()
from browser_use import Agent
from langchain_openai import ChatOpenAI

async def main():
    agent = Agent(
        task="print out the job qualification of this url: https://www.linkedin.com/jobs/view/4247086503/",

        llm=ChatOpenAI(model="gpt-4o"),
    )
    await agent.run()

asyncio.run(main())