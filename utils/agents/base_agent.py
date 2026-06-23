"""
Base Agent Class for Multi-Agent System
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.client = None
    
    def set_client(self, client):
        """Set Groq client for AI capabilities"""
        self.client = client
    
    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task and return results"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> list:
        """Return list of capabilities this agent has"""
        pass
    
    def _call_ai(self, prompt: str, system_prompt: str = None) -> str:
        """Helper method to call AI"""
        if not self.client:
            return "AI client not available"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"