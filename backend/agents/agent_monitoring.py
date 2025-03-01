from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel

from tools.data_collection import collect_data_func
from tools.attack_detection import detect_attack_func
from common_classes import *
from secretKeys import *

sys_intsr = (
    "You are a network monitoring agent. "
    "You have detect_attack tool to detect attacks from the pcap file path in deps and report your findings."
    "Consider attack to be detected only if the normal traffic is too low compared to the other attack traffics in the output"
    "Otherwise, return attack detected to be false."
)

model = GeminiModel(model_name='gemini-2.0-flash', api_key=GEMINI_API_KEY)

monitoring_agent = Agent(
    model=model,
    system_prompt=sys_intsr,
    model_settings={'temperature': 0.5},
    result_retries=3,
    retries=3,
    result_type=AnalysisResult
)

@monitoring_agent.tool
def detect_attack(ctx: RunContext[MyDeps]) -> AttackDetectionResult:
    print(f"Detecting attack in {ctx.deps.pathToFile}...")
    output = detect_attack_func(ctx.deps.pathToFile)
    if output is None:
        output = "Error: No output from detection function."
    return AttackDetectionResult(op=output)

# @monitoring_agent.tool
# def collect_data(ctx: RunContext[MyDeps]) -> str:
#     print(f"Collect_data called: Capturing data for {ctx.deps.duration} seconds...")
#     collect_data_func(ctx.deps.duration)
#     return f"Data capture complete. PCAP stored at '{ctx.deps.pathToFile}/capture.pcap'."