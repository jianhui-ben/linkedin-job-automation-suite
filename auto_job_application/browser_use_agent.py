import asyncio
from dotenv import load_dotenv
load_dotenv()
from browser_use import Agent
from langchain_openai import ChatOpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from openai import OpenAI
import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.browser_utils import initialize_browser


async def main():
    _, context, page = await initialize_browser(
        cookie_file="linkedin_cookies.json",
        headless=False
    )

    await page.goto("https://www.linkedin.com/jobs/view/4221386170/")
    
    # await page.pause()

    llm = ChatOpenAI(
    openai_api_key="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",
    openai_api_base="https://openrouter.ai/api/v1",
    model_name="deepseek/deepseek-chat-v3-0324:free"
    )


    agent = Agent(
        task=""""
        scroll down the page and and then print out the job qualification of this url, 
        if you couldn't find the job application, try to click on show me more to expand some
        hidden url.
        """,
        llm=llm,
        # browser_context = context,
        page = page,
        use_vision=False ## deepseek v3 doesn't support vision
    )
    await agent.run()

asyncio.run(main())