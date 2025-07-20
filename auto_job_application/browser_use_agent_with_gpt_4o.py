import asyncio
import logging
import os
from pathlib import Path
from typing import Literal, List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from PyPDF2 import PdfReader
from pydantic import BaseModel
import random

from browser_use import ActionResult, Agent, Controller
from browser_use.browser import BrowserProfile, BrowserSession

# --- Configuration & Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment and File Paths
if not os.getenv('OPENAI_API_KEY'):
    raise ValueError('OPENAI_API_KEY is not set. Please add it to your environment variables.')
RESUME_PATH = Path.cwd() / 'resumes/Lingrui_Duan_Resume_Dec_2025.pdf'
if not RESUME_PATH.exists():
    raise FileNotFoundError(f'Resume file not found at {RESUME_PATH}')

# --- Pydantic Models for Output ---
class JobApplicationResult(BaseModel):
    status: Literal["SUBMITTED", "REQUIRES_ACCOUNT_REGISTRATION", "NEEDS_HUMAN_INTERVENTION", "FAILED"]
    notes: str

# --- Agent Controller with Custom Actions ---
controller = Controller()

@controller.action('Read my resume for context to fill forms')
def read_resume():
    """Extract text from resume PDF for context when filling forms"""
    pdf = PdfReader(RESUME_PATH)
    text = ''.join(page.extract_text() or '' for page in pdf.pages)
    logger.info(f'Read resume with {len(text)} characters')
    return ActionResult(extracted_content=text, include_in_memory=True)

@controller.action('Upload resume to file input element')
async def upload_resume(index: int, browser_session: BrowserSession):
    """Upload resume PDF to a file input element at the specified index"""
    file_upload_dom_el = await browser_session.find_file_upload_element_by_index(index)
    if not file_upload_dom_el:
        return ActionResult(error=f'No file upload element found at index {index}')
    
    file_upload_el = await browser_session.get_locate_element(file_upload_dom_el)
    if not file_upload_el:
        return ActionResult(error=f'No located file upload element at index {index}')
        
    try:
        await file_upload_el.set_input_files(str(RESUME_PATH.absolute()))
        msg = f'Successfully uploaded resume to file input at index {index}'
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)
    except Exception as e:
        logger.error(f'Error uploading resume: {e}')
        return ActionResult(error='Failed to upload resume file.')

@controller.action('Check if page requires account registration')
async def check_registration_required(browser_session: BrowserSession):
    """Check if the current page is asking for account registration"""
    try:
        page = await browser_session.get_current_page()
        page_content = await page.content()
          
        # Common registration indicators
        registration_keywords = [
            'create account', 'sign up', 'register', 'new account',
            'workday', 'indeed account', 'facebook jobs login',
            'create profile', 'join now'
        ]
          
        content_lower = page_content.lower()
        for keyword in registration_keywords:
            if keyword in content_lower:
                return ActionResult(
                    extracted_content=f'Registration required - detected: {keyword}',
                    include_in_memory=True
                )
          
        return ActionResult(extracted_content='No registration requirement detected')
          
    except Exception as e:
        return ActionResult(error=f'Failed to check registration requirement: {str(e)}')

@controller.action('Ask human for help when unsure about form fields or next steps')
def ask_human_for_help(question: str) -> ActionResult:
    """Ask human for input when the agent is unsure how to proceed"""
    print(f"\n🤖 AGENT NEEDS HELP: {question}")
    print("=" * 50)
    answer = input("👤 Your response: ")
    return ActionResult(
        extracted_content=f'Human provided guidance: {answer}',
        include_in_memory=True
    )

@controller.action('Ask human for specific form field value')
def ask_human_for_field_value(field_name: str, field_description: str = "") -> ActionResult:
    """Ask human to provide a specific value for a form field"""
    prompt = f"\n🤖 NEED FORM DATA: Please provide value for '{field_name}'"
    if field_description:
        prompt += f"\nField description: {field_description}"
    print(prompt)
    print("=" * 50)
    value = input("👤 Enter value: ")
    return ActionResult(
        extracted_content=f'Human provided value for {field_name}: {value}',
        include_in_memory=True
    )

@controller.action('Smart dropdown handler - detects dropdown and selects option with human help if needed')  
async def handle_dropdown_smart(index: int, browser_session: BrowserSession) -> ActionResult:  
    """  
    Intelligently handle dropdown selection:  
    1. Detect if element is a dropdown  
    2. Get available options  
    3. Try to select based on context, or ask human for help  
    """  
    try:  
        # First, get the element and verify it's a dropdown  
        selector_map = await browser_session.get_selector_map()  
        if index not in selector_map:  
            return ActionResult(error=f'Element with index {index} not found in selector map')  
          
        dom_element = selector_map[index]  
          
        # Check if it's actually a select element  
        if dom_element.tag_name.lower() != 'select':  
            return ActionResult(  
                extracted_content=f'Element at index {index} is not a dropdown (tag: {dom_element.tag_name})',  
                include_in_memory=True  
            )  
          
        # Get all available options using the existing built-in action  
        page = await browser_session.get_current_page()  
          
        # Extract dropdown options using similar logic to get_dropdown_options  
        all_options = []  
        for frame in page.frames:  
            try:  
                options = await frame.evaluate(  
                    """  
                    (xpath) => {  
                        const select = document.evaluate(xpath, document, null,  
                            XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;  
                        if (!select) return null;  
                          
                        return {  
                            options: Array.from(select.options).map(opt => ({  
                                text: opt.text,  
                                value: opt.value,  
                                index: opt.index  
                            })),  
                            id: select.id,  
                            name: select.name,  
                            currentValue: select.value  
                        };  
                    }  
                    """,  
                    dom_element.xpath,  
                )  
                  
                if options:  
                    all_options = options['options']  
                    dropdown_info = {  
                        'id': options['id'],  
                        'name': options['name'],  
                        'currentValue': options['currentValue']  
                    }  
                    break  
                      
            except Exception as frame_e:  
                logger.debug(f'Frame evaluation failed: {str(frame_e)}')  
                continue  
          
        if not all_options:  
            return ActionResult(error=f'Could not retrieve options for dropdown at index {index}')  
          
        # Format options for human display  
        options_text = "\n".join([f"{i}: {opt['text']}" for i, opt in enumerate(all_options)])  
          
        # Ask human to select which option  
        question = f"""  
Found dropdown with {len(all_options)} options:  
{options_text}  
  
Current selection: {dropdown_info.get('currentValue', 'None')}  
Dropdown ID: {dropdown_info.get('id', 'N/A')}  
Dropdown Name: {dropdown_info.get('name', 'N/A')}  
  
Which option should I select? Please provide either:  
- The option number (0, 1, 2, etc.)  
- The exact text of the option  
- 'skip' to leave unchanged  
"""  
          
        print(f"\n🤖 DROPDOWN SELECTION NEEDED:")  
        print("=" * 60)  
        print(question)  
        print("=" * 60)  
        human_choice = input("👤 Your choice: ").strip()  
          
        # Process human input  
        if human_choice.lower() == 'skip':  
            return ActionResult(  
                extracted_content=f'Skipped dropdown selection at index {index} as requested',  
                include_in_memory=True  
            )  
          
        # Try to parse as option index first  
        selected_option = None  
        try:  
            option_index = int(human_choice)  
            if 0 <= option_index < len(all_options):  
                selected_option = all_options[option_index]  
        except ValueError:  
            # Not a number, try to match by text  
            for opt in all_options:  
                if opt['text'].strip().lower() == human_choice.lower():  
                    selected_option = opt  
                    break  
          
        if not selected_option:  
            return ActionResult(  
                error=f'Could not find option matching "{human_choice}". Please try again.',  
                include_in_memory=True  
            )  
          
        # Now select the option using similar logic to select_dropdown_option  
        selected_text = selected_option['text']  
          
        for frame in page.frames:  
            try:  
                # Use Playwright's select_option method  
                selected_values = await frame.locator(f'//{dom_element.xpath}').nth(0).select_option(  
                    label=selected_text,   
                    timeout=2000  
                )  
                  
                msg = f'Successfully selected "{selected_text}" from dropdown at index {index}'  
                logger.info(msg)  
                return ActionResult(  
                    extracted_content=msg,  
                    include_in_memory=True  
                )  
                  
            except Exception as frame_e:  
                logger.debug(f'Frame selection failed: {str(frame_e)}')  
                continue  
          
        return ActionResult(  
            error=f'Failed to select option "{selected_text}" in dropdown at index {index}',  
            include_in_memory=True  
        )  
          
    except Exception as e:  
        logger.error(f'Error in smart dropdown handler: {str(e)}')  
        return ActionResult(  
            error=f'Smart dropdown handler failed: {str(e)}',  
            include_in_memory=True  
        )
    
@controller.action('Check if element is a dropdown and get basic info')  
async def check_if_dropdown(index: int, browser_session: BrowserSession) -> ActionResult:  
    """Check if an element is a dropdown and return basic information"""  
    try:  
        selector_map = await browser_session.get_selector_map()  
        if index not in selector_map:  
            return ActionResult(error=f'Element with index {index} not found')  
          
        dom_element = selector_map[index]  
          
        if dom_element.tag_name.lower() == 'select':  
            return ActionResult(  
                extracted_content=f'Element at index {index} IS a dropdown (select element)',  
                include_in_memory=True  
            )  
        else:  
            return ActionResult(  
                extracted_content=f'Element at index {index} is NOT a dropdown (tag: {dom_element.tag_name})',  
                include_in_memory=True  
            )  
              
    except Exception as e:  
        return ActionResult(error=f'Failed to check element: {str(e)}')

# --- Main Application Class ---
class JobApplicationAgent:
    def __init__(self, job_urls: List[str], profile_name: str = "default"):
        self.job_urls = job_urls
        self.profile_name = profile_name
        user_data_dir = os.path.expanduser(f"~/.config/browseruse/profiles/{self.profile_name}")
        self.browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                user_data_dir=user_data_dir,
                window_size={'width': 1920, 'height': 1080}, 
                headless=False,
            ),
            # viewport={'width': 1920, 'height': 1080},
        )
    
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
        
        task_prompt_path = Path(__file__).parent / 'job_application_prompt.txt'
        extended_system_prompt_path = Path(__file__).parent / 'extended_system_prompt.txt'
        if not task_prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found at {task_prompt_path}")
        self.base_prompt = task_prompt_path.read_text()
        self.extended_system_prompt = extended_system_prompt_path.read_text();

    async def run(self):
        """Starts the browser session and processes all job applications."""
        logger.info(f"Starting browser session with profile: {self.profile_name}")
       
        await self.browser_session.start()

        ##sometimes the very first window (the one Playwright or browser-use opens by default) 
        # does not always respect the window_size parameter, especially on macOS or with 
        # certain Playwright versions. This is a known quirk with Chromium/Playwright.
        # When you later create a new tab or page (e.g., with create_new_tab(job_url)), 
        # the new page is opened in the same browser window, which by then may have been 
        # resized, or the new page itself is created with the correct viewport.
        initial_page = await self.browser_session.get_current_page()
        await initial_page.close()
        
        for job_url in self.job_urls:
            await self.apply_to_job(job_url)
            await asyncio.sleep(random.randint(10, 25)) # Longer, randomized delay

        await self.browser_session.stop()
        logger.info("All job applications processed.")

    async def apply_to_job(self, job_url: str):
        """Applies to a single job URL using a new agent instance."""
        logger.info(f"--- Starting application for: {job_url} ---")

        task = f"Apply for the job, following the provided instructions.\n\n{self.base_prompt}"
        
        job_page = await self.browser_session.create_new_tab(job_url)

        agent = Agent(
            task=task,
            llm=self.llm,
            controller=controller,
            browser_session=self.browser_session,
            use_vision=True,
            max_failures=3,
            page = job_page,
            # max_actions_per_step=2
            max_actions_per_step=1,  # Reduce to 1 for more careful step-by-step execution  
            extend_system_message=self.extended_system_prompt
        )
        
        try:
            history = await agent.run(max_steps=50)  ## max run of the agent
            final_result = history.final_result() or "No final result specified by agent."
            logger.info(f"Application for {job_url} completed with result: {final_result}")
        except Exception as e:
            logger.error(f"An error occurred while applying to {job_url}: {e}")

# --- Entry Point ---
async def main():
    job_urls_to_apply = [
        "https://www.linkedin.com/jobs/view/4254612043/", 
        # "https://www.linkedin.com/jobs/view/ANOTHER_JOB_ID_HERE/",  # Replace with actual job URLs
    ]
    
    application_agent = JobApplicationAgent(job_urls=job_urls_to_apply, profile_name="yahoo_email_account")
    await application_agent.run()


if __name__ == '__main__':
    asyncio.run(main())