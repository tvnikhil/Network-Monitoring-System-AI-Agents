from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from common_classes import ParameterResult, MyDeps
from secretKeys import GEMINI_API_KEY

sys_prompt = (
    "You are a parameter tuning agent. Based on network conditions and previous analysis, "
    "set optimal capture duration (30-100 seconds) and cycle interval (5-30 seconds). "
    "Guidelines: Increase duration and decrease interval if attack detected, latency > 75 ms, "
    "or packet loss > 5%; otherwise, decrease duration and increase interval."
)

model = GeminiModel(model_name='gemini-2.0-flash', api_key=GEMINI_API_KEY)

parameter_tuning_agent = Agent(
    model=model,
    system_prompt=sys_prompt,
    model_settings={'temperature': 0.5},
    result_retries=3,
    retries=3,
    result_type=ParameterResult
)