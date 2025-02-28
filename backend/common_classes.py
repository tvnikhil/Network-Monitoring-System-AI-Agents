from pydantic import BaseModel, Field
from typing import Optional
from dataclasses import dataclass

class AttackDetectionResult(BaseModel):
    op: str = Field(description="Result of the attack detection operation")

class AnalysisResult(BaseModel):
    attack_detected: bool = Field(description="Whether an attack was detected")
    details: Optional[str] = Field(default=None, description="Additional details about the analysis")

class ParameterResult(BaseModel):
    duration: int = Field(description="The updated capture duration in seconds")
    interval: int = Field(description="The interval (in seconds) before the next monitoring cycle")

@dataclass
class MyDeps:
    pathToFile: str = Field(description="Path to the PCAP file")
    duration: int = Field(default=5, description="Duration of data collection in seconds")
    cycle_interval: int = Field(default=2, description="Interval between 2 cycles")
    avg_latency: float = Field(default=None, description="Average latency of the network")
    avg_loss: float = Field(default=None, description="Average packet loss of the network")
