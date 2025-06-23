import asyncio
from dotenv import load_dotenv
load_dotenv()
from browser_use import Agent, BrowserSession,BrowserProfile
from langchain_openai import ChatOpenAI
import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.browser_utils import initialize_browser, initialize_browser_with_profile

# Load OpenRouter DeepSeek API key from environment
OPENROUTER_DEEPSEEK_API_KEY = os.environ.get('OPENROUTER_DEEPSEEK_API_KEY')  # Set this in .env file


async def main():
    # _, context, page = await initialize_browser(
    #     cookie_file="../linkedin_cookies_ben.json",
    #     headless=False
    # )

    browser_session, page = await initialize_browser_with_profile(profile_name="yahoo_email_account",headless= False)


    await page.goto("https://www.linkedin.com/jobs/view/4221386170/")
    
    llm = ChatOpenAI(
    openai_api_base="https://openrouter.ai/api/v1",
    model='deepseek/deepseek-r1-0528:free', 
    openai_api_key=OPENROUTER_DEEPSEEK_API_KEY
    )


    agent = Agent(
        task = """"
        go to this job and get the rough job company name for this job
        """,
        llm=llm,
        # browser_context = context,
        browser_session=browser_session,
        page = page,
        use_vision=False
    )
    await agent.run()

asyncio.run(main())