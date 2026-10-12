\# Deep Reasoning Supplier Research Agent



An LLM-powered procurement research agent that analyzes a quotation, researches potential suppliers, compares products against technical and commercial requirements, and produces an evidence-based supplier recommendation.



\## Architecture



1\. The user submits a quotation.

2\. The agent sends the requirements to an LLM through the OpenRouter API.

3\. The model uses tools exposed through Hound MCP to conduct web research.

4\. Tool results are returned to the model for analysis.

5\. The agent produces a supplier comparison, recommendation, supporting sources, and a list of unverified details.



\## Technologies



\- Python

\- OpenRouter API

\- OpenAI-compatible Python SDK

\- Model Context Protocol (MCP)

\- Hound MCP

\- python-dotenv



\## Requirements



\- Python 3.11 or newer, subject to dependency compatibility

\- An OpenRouter API key

\- Hound MCP and its required browser dependencies

\- A model available through OpenRouter that supports tool calling



\## Setup



1\. Clone this repository.

2\. Create and activate a Python virtual environment.

3\. Install the dependencies listed in `requirements.txt`.

4\. Copy `.env.example` to `.env`.

5\. Add your own OpenRouter API key to `.env`.

6\. Start Hound in HTTP mode using its installed executable.

7\. Configure the model identifier in `deep\_r.py` to a model available to your OpenRouter account.



By default, the agent connects to the Hound MCP endpoint:



`http://127.0.0.1:8765/mcp`



\## Run



Start Hound in one terminal, then run the agent in another:



`python deep\_r.py`



Paste a quotation when prompted.



\## Output



The agent aims to produce:



\- Extracted quotation requirements

\- A comparison of candidate suppliers

\- A recommended supplier

\- Supporting sources and URLs

\- Unverified information and procurement risks

\- A final recommendation with a confidence assessment



\## Security



Never commit `.env` or any file containing API keys. Each user should configure their own OpenRouter credentials.



\## Limitations



Supplier prices, stock, certifications, and delivery details can change. Recommendations should be validated against current supplier evidence and confirmed directly before placing an order.

