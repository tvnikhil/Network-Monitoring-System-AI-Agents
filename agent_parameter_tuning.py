from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from common_classes import *

sys_intsr = (
    "You are a parameter tuning agent. Based on current conditions and previous analysis, "
    "decide on the optimal capture duration in seconds and cycle interval in seconds for network monitoring."
    "You will be given the average latency and average packet loss of the network currently. Decide based off that."
    "The capture duration should be between 5 and 100 seconds."
    "The cycle interval should be between 30 and 60 seconds."
)

model = GeminiModel(model_name='gemini-2.0-flash', api_key="AIzaSyAY2grODd5AkIynpMavWrjjHolufxKIj5M")

parameter_tuning_agent = Agent(
    model=model,
    system_prompt=sys_intsr,
    model_settings={'temperature': 0.5},
    result_retries=3,
    retries=3,
    result_type=ParameterResult
)