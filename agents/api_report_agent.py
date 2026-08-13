from crewai_bootstrap import bootstrap_crewai_runtime

bootstrap_crewai_runtime()

from crewai import Agent
from llm import default_llm
from tools.runtime_config import CREWAI_VERBOSE

api_report_agent = Agent(
    role="Certification Authority Writer",
    goal="Generate the final USER PASS Certification scorecard and professional vulnerability report.",
    backstory="You are the technical authority. You translate raw attributes into Executive summaries and detailed technical findings. You issue Bronze, Silver, Gold, or Platinum Certifications.",
    verbose=CREWAI_VERBOSE,
    allow_delegation=False,
    llm=default_llm
)
