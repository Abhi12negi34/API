from crewai_bootstrap import bootstrap_crewai_runtime

bootstrap_crewai_runtime()

from crewai import Agent
from llm import default_llm
from tools.runtime_config import CREWAI_VERBOSE

api_analyzer_agent = Agent(
    role="USER PASS Aggregation Analyst",
    goal="Analyze the execution results across Usability, Security, Efficiency, Reliability, Performance, Accessibility, Scalability, and Stability.",
    backstory="You are the ultimate software attribute analyst. You digest thousands of raw network logs and output actionable intelligence on where the API breaks.",
    verbose=CREWAI_VERBOSE,
    allow_delegation=False,
    llm=default_llm
)
