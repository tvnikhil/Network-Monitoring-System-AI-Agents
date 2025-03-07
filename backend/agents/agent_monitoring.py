from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from tools.attack_detection import detect_attack_func
from common_classes import AttackDetectionResult, AnalysisResult, MyDeps
from secretKeys import GEMINI_API_KEY
import logging

logger = logging.getLogger(__name__)

sys_prompt = (
    "You are a network monitoring agent. Use the detect_attack tool to analyze PCAP files "
    "from the path in deps and report findings. Consider an attack detected only if normal "
    "traffic is significantly lower than attack traffic in the output; otherwise, return false."
)

model = GeminiModel(model_name='gemini-2.0-flash', api_key=GEMINI_API_KEY)

monitoring_agent = Agent(
    model=model,
    system_prompt=sys_prompt,
    model_settings={'temperature': 0.5},
    result_retries=3,
    retries=3,
    result_type=AnalysisResult
)

@monitoring_agent.tool
def detect_attack(ctx: RunContext[MyDeps]) -> AttackDetectionResult:
    """Detect attacks in the specified PCAP file."""
    logger.info(f"Detecting attack in {ctx.deps.pathToFile}...")
    output = detect_attack_func(ctx.deps.pathToFile)
    return AttackDetectionResult(op=output or "Error: No output from detection function.")