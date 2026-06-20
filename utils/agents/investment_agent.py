"""
Investment Agent - Specialized in investments and wealth creation
"""

from utils.agents.base_agent import BaseAgent
from typing import Dict, Any


class InvestmentAgent(BaseAgent):
    """Agent specialized in investments"""
    
    def __init__(self):
        super().__init__(
            name="Investment Agent",
            description="Expert in investment strategies, SIPs, stocks, and mutual funds"
        )
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute investment-related task"""
        query = task.get('query', '')
        context = task.get('context', {})
        
        prompt = f"""
        You are an Investment Expert Agent. Analyze this investment query:
        "{query}"
        
        User Context:
        - Monthly income: ₹{context.get('income', 'Unknown')}
        - Existing investments: ₹{context.get('investments', 'Unknown')}
        - Risk profile: {context.get('risk_profile', 'Moderate')}
        
        Provide:
        1. Investment recommendations aligned with risk profile
        2. Asset allocation suggestions (stocks/bonds/gold)
        3. SIP or lumpsum strategy
        4. Expected returns and risks
        
        Consider Indian market context.
        """
        
        system_prompt = """You are an expert investment advisor.
        Provide diversified, risk-appropriate investment recommendations.
        Always mention that past performance doesn't guarantee future returns."""
        
        response = self._call_ai(prompt, system_prompt)
        
        return {
            'agent': self.name,
            'query': query,
            'response': response,
            'confidence': 'high' if 'specific' in response.lower() else 'medium'
        }
    
    def get_capabilities(self) -> list:
        return [
            "SIP and mutual fund analysis",
            "Stock investment advice",
            "Asset allocation",
            "Portfolio diversification",
            "Risk assessment"
        ]