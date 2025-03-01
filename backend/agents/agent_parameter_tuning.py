from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from common_classes import *
from secretKeys import *

sys_intsr = (
    "You are a parameter tuning agent. Based on current network conditions and previous analysis, "
    "decide on the optimal capture duration in seconds and cycle interval in seconds for network monitoring. "
    "You will be given the current average latency in ms, current packet loss in %, and whether an attack was detected in the previous cycle. "
    "Consider the following guidelines: "
    "- If an attack was detected or if latency > 75 ms or packet loss > 5%, increase the capture duration (up to 100 seconds) and decrease the cycle interval (down to 30 seconds) to monitor more aggressively. "
    "- If no attack was detected and latency <= 75 ms and packet loss <= 5%, decrease the capture duration (down to 5 seconds) and increase the cycle interval (up to 60 seconds) to conserve resources. "
    "The capture duration must be between 30 and 100 seconds. "
    "The cycle interval must be between 5 and 30 seconds."
)

model = GeminiModel(model_name='gemini-2.0-flash', api_key=GEMINI_API_KEY)

parameter_tuning_agent = Agent(
    model=model,
    system_prompt=sys_intsr,
    model_settings={'temperature': 0.5},
    result_retries=3,
    retries=3,
    result_type=ParameterResult
)
