# LinkedIn Job Automation Suite

An end-to-end automation system for job hunting on LinkedIn, powered by multiple AI agents working together to streamline the job search and application process.

## System Components

### 1. Job Scraper Agent
- Automatically searches and collects job listings from LinkedIn
- Filters jobs based on customizable criteria
- Saves job data for further processing

### 2. Resume Analysis Agent (Coming Soon)
- Analyzes job descriptions
- Identifies key requirements and skills
- Suggests resume modifications
- Optimizes resume for specific job postings

### 3. Application Agent (Coming Soon)
- Automates the job application process
- Fills out application forms
- Handles file uploads
- Manages application tracking

## Prerequisites

- Python 3.7 or higher
- pip3 (Python package installer)
- LinkedIn account
- OpenAI API key (for future AI-powered features)

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd linkedin-job-automation-suite
```

2. Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

3. Install the required packages:
```bash
pip3 install -r requirements.txt
```

## Usage

### Step 1: Save LinkedIn Cookies

Before scraping, you need to save your LinkedIn cookies for authentication:

1. Run the cookie saver script:
```bash
python3 save_linkedin_cookies.py
```

2. A browser window will open. Log in to your LinkedIn account.
3. After successful login, the script will save your cookies to `linkedin_cookies.json`.

### Step 2: Scrape Jobs

1. Run the scraper with your desired search parameters:
```bash
python3 scraper.py
```

By default, the scraper will:
- Search for "product manager" jobs
- Look in "United States"
- Scrape 100 jobs
- Save results in the `results` directory

### Customizing the Search

You can modify the search parameters in `scraper.py`:

```python
search_config = SearchConfig(
    title="your job title",      # e.g., "software engineer"
    location="your location",    # e.g., "San Francisco"
    num_jobs=100,               # number of jobs to scrape
    time_filter="Past 24 hours" # optional: time filter for jobs
)
```

## Output

The scraper will create a CSV file in the `results` directory with the following format:
- Filename: `linkedin_jobs_[title]_[location]_[timestamp].csv`
- Columns: `job_id`, `url`

## Future Features

### Resume Analysis Agent
- Job description analysis
- Skill matching
- Resume optimization suggestions
- ATS compatibility checking

### Application Agent
- Automated form filling
- Resume and cover letter upload
- Application tracking
- Follow-up automation

## Troubleshooting

1. If you get authentication errors:
   - Delete the existing `linkedin_cookies.json`
   - Run `save_linkedin_cookies.py` again to create fresh cookies

2. If the browser doesn't start:
   - Make sure you have the latest version of Playwright
   - Run `playwright install` to install browser dependencies

## Notes

- The scraper uses a visible browser by default for debugging
- To run in headless mode, set `headless=True` in the `LinkedInJobScraper` initialization
- Be mindful of LinkedIn's rate limits and terms of service
- Consider adding delays between requests to avoid being blocked

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License
