"""
Multi-Agent Financial Advisor System with Chief Planner
Specialized agents for different financial domains with intelligent orchestration
"""

from typing import Dict, List, Tuple, Any, Optional
from groq import Groq
import re
import json
import time


class FinancialAgent:
    """Base class for specialized financial agents"""
    
    def __init__(self, name: str, specialization: str, system_prompt: str, keywords: List[str]):
        self.name = name
        self.specialization = specialization
        self.system_prompt = system_prompt
        self.keywords = keywords
        self.queries_handled = 0
        self.total_response_time = 0
        self.capabilities = self._extract_capabilities()
    
    def _extract_capabilities(self) -> List[str]:
        """Extract capabilities from system prompt"""
        capabilities = []
        lines = self.system_prompt.split('\n')
        for line in lines:
            if '- ' in line:
                cap = line.replace('-', '').strip()
                if cap and len(cap) > 10:
                    capabilities.append(cap)
        return capabilities[:5]  # Return top 5
    
    def process_query(self, query: str, client: Groq, context: str = "", sub_task: str = "") -> Dict:
        """Process query and return response"""
        start = time.time()
        
        full_prompt = f"""{self.system_prompt}

{sub_task if sub_task else 'Please analyze and respond to the user query.'}

Previous context from other agents: {context if context else 'None'}

User Query: {query}

Provide expert, actionable advice based on your specialization. Be specific and practical.
If you need more information, ask clarifying questions.
Include specific numbers, percentages, or recommendations where possible."""

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            elapsed = time.time() - start
            self.queries_handled += 1
            self.total_response_time += elapsed
            
            return {
                "agent": self.name,
                "specialization": self.specialization,
                "response": response.choices[0].message.content,
                "confidence": 0.85,
                "response_time": round(elapsed, 2),
                "query": query,
                "capabilities": self.capabilities
            }
        except Exception as e:
            return {
                "agent": self.name,
                "specialization": self.specialization,
                "response": f"I apologize, but I encountered an error. Let me try to help differently.",
                "confidence": 0.3,
                "error": str(e),
                "query": query
            }
    
    def get_avg_response_time(self):
        if self.queries_handled == 0:
            return 0
        return round(self.total_response_time / self.queries_handled, 2)
    
    def to_dict(self):
        return {
            "name": self.name,
            "specialization": self.specialization,
            "capabilities": self.capabilities,
            "queries_handled": self.queries_handled,
            "avg_response_time": self.get_avg_response_time()
        }


# Agent Definitions
TAX_AGENT = FinancialAgent(
    name="Tax Advisor",
    specialization="Tax Planning & Optimization",
    system_prompt="""You are a specialized Tax Advisor for Indian taxation system.

Your expertise includes:
- Income Tax calculation (Old vs New Regime)
- Tax deductions under 80C, 80D, 80E
- HRA exemption calculation
- Capital gains tax
- GST for businesses
- TDS/TCS provisions
- Tax saving investments (ELSS, PPF, NPS, etc.)
- ITR filing guidance

Guidelines:
1. Always mention applicable sections when suggesting deductions
2. Compare Old vs New Regime when relevant
3. Suggest specific tax-saving investments with amounts
4. Be practical and consider user's income level
5. Mention deadlines for tax-saving investments (March 31st)

Remember: You are a tax expert - provide accurate, actionable tax advice.""",
    keywords=["tax", "itr", "income tax", "deduction", "80c", "80d", "hra", "capital gains", "gst", "tds", "tax saving", "elss", "ppf", "nps", "it refund", "tax filing"]
)

INVESTMENT_AGENT = FinancialAgent(
    name="Investment Advisor",
    specialization="Investment & Portfolio Management",
    system_prompt="""You are a specialized Investment Advisor.

Your expertise includes:
- Stock market investments (equity, derivatives)
- Mutual funds (large cap, mid cap, small cap, ELSS)
- Fixed income (FD, bonds, debentures)
- Portfolio allocation strategies
- Risk assessment and management
- Goal-based investing (retirement, child education, etc.)
- SIP planning and optimization
- Asset allocation based on age and risk profile

Guidelines:
1. Always mention risk levels when suggesting investments
2. Recommend specific mutual funds or stocks when possible
3. Consider investment horizon (short/medium/long term)
4. Suggest diversification strategies
5. Include expected returns range (not guaranteed)

Remember: You are an investment expert - provide balanced, risk-aware advice.""",
    keywords=["invest", "stock", "mutual fund", "sip", "portfolio", "equity", "bond", "fd", "fixed deposit", "share market", "nifty", "sensex", "returns", "dividend", "asset allocation", "risk profile"]
)

DEBT_AGENT = FinancialAgent(
    name="Debt Management Expert",
    specialization="Debt & Credit Management",
    system_prompt="""You are a specialized Debt Management Expert.

Your expertise includes:
- Loan management (home, car, personal, education)
- Credit score improvement (CIBIL)
- Debt consolidation strategies
- EMI calculation and restructuring
- Credit card management
- Loan prepayment strategies
- Bankruptcy alternatives
- Interest rate negotiation

Guidelines:
1. Prioritize high-interest debt repayment
2. Suggest specific debt reduction strategies (snowball/avalanche)
3. Provide EMI calculations when relevant
4. Explain credit score factors and improvement tips
5. Be empathetic but practical about debt situations

Remember: You are a debt expert - focus on reducing financial burden and improving credit health.""",
    keywords=["debt", "loan", "emi", "credit card", "cibil", "credit score", "borrow", "interest rate", "personal loan", "home loan", "car loan", "education loan", "debt consolidation", "bankruptcy", "overdue"]
)

RETIREMENT_AGENT = FinancialAgent(
    name="Retirement Planner",
    specialization="Retirement & Pension Planning",
    system_prompt="""You are a specialized Retirement Planner.

Your expertise includes:
- Retirement corpus calculation
- NPS (National Pension System)
- PPF (Public Provident Fund)
- Senior citizen savings schemes
- Pension planning strategies
- Withdrawal strategies post-retirement
- Inflation-adjusted retirement planning
- Reverse mortgage options

Guidelines:
1. Use 4% withdrawal rule as reference
2. Account for inflation (typically 6-7%)
3. Suggest specific retirement products with current rates
4. Calculate required corpus based on current expenses
5. Consider life expectancy (85+ years)

Remember: You are a retirement expert - help users plan for a comfortable post-retirement life.""",
    keywords=["retirement", "pension", "nps", "ppf", "senior citizen", "retire", "post retirement", "old age", "pension scheme", "retirement corpus", "annuity"]
)

INSURANCE_AGENT = FinancialAgent(
    name="Insurance Advisor",
    specialization="Insurance Planning",
    system_prompt="""You are a specialized Insurance Advisor.

Your expertise includes:
- Life insurance (term, whole life, ULIP)
- Health insurance (individual, family floater)
- Critical illness coverage
- Accident insurance
- Home and vehicle insurance
- Claim process guidance
- Coverage gap analysis
- Premium optimization

Guidelines:
1. Recommend term insurance with adequate coverage (10-15x annual income)
2. Suggest health insurance with sufficient sum insured (min ₹5-10 lakhs)
3. Explain waiting periods and exclusions clearly
4. Compare different plan types when relevant
5. Emphasize buying pure term insurance over investment-linked plans

Remember: You are an insurance expert - prioritize adequate coverage over returns.""",
    keywords=["insurance", "health insurance", "life insurance", "term plan", "medical insurance", "claim", "premium", "coverage", "critical illness", "family floater", "accident insurance"]
)

GENERAL_AGENT = FinancialAgent(
    name="General Financial Advisor",
    specialization="General Financial Guidance",
    system_prompt="""You are a General Financial Advisor - a fallback for topics not covered by specialized agents.

Your expertise includes:
- Basic financial literacy
- Budgeting and saving tips
- Emergency fund planning
- General money management
- Financial goal setting
- Expense tracking advice
- Basic financial calculations

Guidelines:
1. Keep advice practical and actionable
2. Explain financial concepts in simple terms
3. Suggest specific percentages (e.g., 50/30/20 rule)
4. When specialized knowledge is needed, acknowledge it
5. Encourage users to ask specialized questions

Remember: You're the generalist - help with basic finance but defer to specialists when needed.""",
    keywords=["money", "finance", "budget", "save", "emergency fund", "financial goal", "spending", "expense", "salary", "income", "monthly budget", "financial planning", "wealth", "saving money"]
)


PORTFOLIO_AGENT = FinancialAgent(
    name="Portfolio Manager",
    specialization="Portfolio Optimization & Asset Allocation",
    system_prompt="""You are a specialized Portfolio Manager.

Your expertise includes:
- Asset allocation strategies (Strategic & Tactical)
- Portfolio rebalancing (threshold and periodic)
- Risk-return optimization (Modern Portfolio Theory)
- Diversification across asset classes (Equity, Debt, Gold, Cash)
- Evaluating portfolio performance metrics

Guidelines:
1. Always analyze current vs target asset allocation
2. Suggest specific rebalancing steps
3. Explain risk-return tradeoffs
4. Maintain a long-term investment discipline

Remember: You are a portfolio management expert - provide professional, risk-aligned asset allocation advice.""",
    keywords=["portfolio", "allocation", "asset allocation", "rebalance", "diversification", "optimization", "risk-return"]
)


class ChiefPlanner:
    """
    Chief Planner - Orchestrates all agents with intelligent task breakdown
    """
    
    def __init__(self, client: Groq):
        self.client = client
        self.agents = {
            'tax': TAX_AGENT,
            'investment': INVESTMENT_AGENT,
            'debt': DEBT_AGENT,
            'retirement': RETIREMENT_AGENT,
            'insurance': INSURANCE_AGENT,
            'portfolio': PORTFOLIO_AGENT,
            'general': GENERAL_AGENT
        }
        self.agent_list = list(self.agents.values())
        self.conversation_history = []
        self.cross_agent_context = {}
        self.agent_priority = ['tax', 'investment', 'portfolio', 'retirement', 'insurance', 'debt', 'general']
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query and identify which agents to consult"""
        query_lower = query.lower()
        
        # Score each agent
        scores = {}
        for agent_name, agent in self.agents.items():
            score = 0
            for keyword in agent.keywords:
                if keyword in query_lower:
                    score += 1
            # Boost for exact matches
            for keyword in agent.keywords:
                if query_lower.startswith(keyword):
                    score += 2
            scores[agent_name] = score
        
        # Sort by priority and score
        ordered_agents = []
        for agent_name in self.agent_priority:
            if scores.get(agent_name, 0) > 0:
                ordered_agents.append({
                    'name': agent_name,
                    'score': scores[agent_name],
                    'agent': self.agents[agent_name]
                })
        
        # If no agents match, use general
        if not ordered_agents:
            ordered_agents.append({
                'name': 'general',
                'score': 0,
                'agent': GENERAL_AGENT
            })
        
        return {
            'query': query,
            'agents_to_consult': ordered_agents,
            'primary_agent': ordered_agents[0]['name'] if ordered_agents else 'general'
        }
    
    def break_down_query(self, query: str) -> List[Dict[str, str]]:
        """Break down complex query into subtasks"""
        subtasks = []
        query_lower = query.lower()
        
        # Check for multiple domains
        domains = []
        if any(k in query_lower for k in TAX_AGENT.keywords):
            domains.append('tax')
        if any(k in query_lower for k in INVESTMENT_AGENT.keywords):
            domains.append('investment')
        if any(k in query_lower for k in DEBT_AGENT.keywords):
            domains.append('debt')
        if any(k in query_lower for k in RETIREMENT_AGENT.keywords):
            domains.append('retirement')
        if any(k in query_lower for k in INSURANCE_AGENT.keywords):
            domains.append('insurance')
        if any(k in query_lower for k in PORTFOLIO_AGENT.keywords):
            domains.append('portfolio')
        
        if not domains:
            domains = ['general']
        
        for domain in domains:
            subtasks.append({
                'domain': domain,
                'query': query,
                'priority': self.agent_priority.index(domain) if domain in self.agent_priority else 999
            })
        
        return sorted(subtasks, key=lambda x: x['priority'])
    
    def synthesize_response(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        """Synthesize responses from multiple agents into a cohesive master plan"""
        if not results:
            return {
                'response': "I couldn't process your query. Please try again.",
                'summary': "No response generated",
                'confidence': 0
            }
        
        # Build synthesis prompt
        synthesis_prompt = f"""
You are the Chief Financial Planner. Synthesize the step-by-step collaborative analysis of your specialized agents into a cohesive, structured master plan.

User Query: {query}

Collaborative Steps:
"""
        for idx, step in enumerate(results):
            synthesis_prompt += f"""
Step {idx + 1}: {step.get('timeline_point', 'Analysis')}
Agent: {step.get('agent_name', 'Advisor')} ({step.get('specialization', '')})
Subtask: {step.get('sub_task', '')}
Response:
{step.get('response', 'No response')}
"""
        
        synthesis_prompt += """
Provide a cohesive, unified master plan. It must include:
1. Executive Summary (2-3 sentences presenting the overall strategy)
2. Cohesive Timeline / Step-by-Step execution flow
3. Consolidated financial recommendations (key numbers, targets, and milestones)
4. Critical next steps for the user to take action

Ensure the plan flows logically and integrates all the agents' advice. Use markdown for styling and bullet points for readability.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are the Chief Financial Planner synthesizing expert advice."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            synthesized = response.choices[0].message.content
            
            return {
                'response': synthesized,
                'summary': synthesized.split('\n')[0] if synthesized else '',
                'confidence': 0.9,
                'agents_consulted': [r.get('agent_name', '') for r in results],
                'full_response': synthesized
            }
        except Exception as e:
            return {
                'response': f"Error synthesizing: {str(e)}",
                'summary': "Synthesis error",
                'confidence': 0.3,
                'agents_consulted': []
            }
    
    def process_query(self, query: str, chat_history: List = None) -> Dict:
        """
        Main entry point: Process query through multi-agent system with sequential collaboration plan
        """
        try:
            # Step 1: Request collaborative plan sequence from LLM
            planning_prompt = f"""
Analyze the user's financial query: "{query}"

Design a collaborative, sequential multi-agent execution plan.
You have access to these specialized agents:
- 'investment': Investment Advisor (SIPs, stocks, mutual funds, savings goals, wealth creation)
- 'debt': Debt Management Expert (loans, mortgages, EMI calculation, debt reduction)
- 'tax': Tax Advisor (tax planning, deductions under 80C/80D, capital gains, tax benefits)
- 'retirement': Retirement Planner (corpus calculation, NPS, PPF, pensions)
- 'insurance': Insurance Advisor (life, health, term plans, coverage gap analysis)
- 'portfolio': Portfolio Manager (portfolio allocation, rebalancing, diversification)
- 'general': General Financial Advisor (budgeting, emergency funds, basic finance)

Create a logical sequence of agent consultations to address the query. Each step MUST build on the previous steps' outputs (e.g. Investment Agent calculates savings -> Debt Agent uses savings for mortgage affordability -> Tax Agent analyzes tax benefits of the mortgage).

Output ONLY a JSON array of steps. Do NOT wrap the JSON in ```json ... ``` blocks, do NOT add any markdown formatting, and do NOT include any commentary. Just return the raw JSON string.

Each step in the JSON array must have:
1. "agent_key": The string key of the agent (one of: 'investment', 'debt', 'tax', 'retirement', 'insurance', 'portfolio', 'general')
2. "sub_task": A specific, clear prompt/question telling this agent what to analyze/calculate as part of the overall plan, building on previous context.
3. "timeline_point": A short label (2-4 words, e.g., "Down Payment Y1-5" or "Loan & EMI Plan") representing the focus of this step.

Example Output format:
[
  {{"agent_key": "investment", "sub_task": "Devise a savings plan to reach down payment...", "timeline_point": "Save Down Payment"}},
  {{"agent_key": "debt", "sub_task": "Model a home loan based on target price...", "timeline_point": "Home Loan Planning"}},
  {{"agent_key": "tax", "sub_task": "Analyze tax benefits for home loan principal and interest...", "timeline_point": "Tax Implications"}}
]
"""
            plan_steps = []
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are the Chief Financial Planner planning multi-agent collaboration. Output raw JSON only."},
                        {"role": "user", "content": planning_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1000
                )
                raw_plan = response.choices[0].message.content.strip()
                
                # Try to extract JSON array using regex if there is surrounding text
                json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_plan, re.DOTALL)
                if json_match:
                    raw_plan = json_match.group(0)
                
                plan_steps = json.loads(raw_plan)
                
                # Validate structure
                if not isinstance(plan_steps, list) or not all(isinstance(s, dict) and 'agent_key' in s for s in plan_steps):
                    raise ValueError("Invalid plan structure")
            except Exception as e:
                print("Planning LLM failed or returned invalid JSON. Falling back to keyword-based steps. Error:", e)
                # Fallback to keyword-based breakdown
                subtasks = self.break_down_query(query)
                plan_steps = []
                for subtask in subtasks:
                    domain = subtask['domain']
                    plan_steps.append({
                        'agent_key': domain,
                        'sub_task': f"Analyze this query focusing on {self.agents[domain].specialization}.",
                        'timeline_point': self.agents[domain].name
                    })

            # Step 2: Execute subtasks sequentially
            results = []
            for idx, step in enumerate(plan_steps):
                agent_key = step['agent_key']
                agent = self.agents.get(agent_key, GENERAL_AGENT)
                
                # Format previous context
                context_str = ""
                if idx > 0:
                    context_str = "Below is the output from the previous collaborating agents in this chain. Use this context to build your response:\n\n"
                    for prev_res in results:
                        context_str += f"=== {prev_res['agent_name']} ({prev_res['specialization']}) ===\n{prev_res['response']}\n\n"
                
                # Execute agent query
                start_time = time.time()
                agent_res = agent.process_query(
                    query=query,
                    client=self.client,
                    context=context_str,
                    sub_task=step['sub_task']
                )
                elapsed = time.time() - start_time
                
                # Store results
                step_result = {
                    'agent_key': agent_key,
                    'agent_name': agent.name,
                    'specialization': agent.specialization,
                    'sub_task': step['sub_task'],
                    'timeline_point': step['timeline_point'],
                    'response': agent_res.get('response', 'No response'),
                    'confidence': agent_res.get('confidence', 0.8),
                    'response_time': round(elapsed, 2)
                }
                results.append(step_result)
                
                # Store context in ChiefPlanner dictionary (legacy compatibility)
                self.cross_agent_context[agent.name] = agent_res.get('response', '')[:200]
            
            # Step 3: Synthesize results
            synthesized = self.synthesize_response(query, results)
            
            # Step 4: Store in history
            self.conversation_history.append({
                'query': query,
                'agents_consulted': [r['agent_name'] for r in results],
                'response': synthesized.get('response', ''),
                'timestamp': time.time()
            })
            
            # Keep only last 10
            if len(self.conversation_history) > 10:
                self.conversation_history.pop(0)
            
            return {
                'success': True,
                'query': query,
                'response': synthesized.get('response', ''),
                'summary': synthesized.get('summary', ''),
                'confidence': synthesized.get('confidence', 0.7),
                'agents_consulted': synthesized.get('agents_consulted', []),
                'plan_steps': results,
                'disclaimer': self.get_disclaimer()
            }
            
        except Exception as e:
            return {
                'success': False,
                'query': query,
                'response': f"I apologize, but I encountered an error processing your request: {str(e)}",
                'summary': "Error processing query",
                'confidence': 0,
                'error': str(e)
            }
    
    def get_cross_agent_context(self, current_agent: FinancialAgent) -> str:
        """Get relevant context from other agents"""
        context_parts = []
        for agent_name, context in self.cross_agent_context.items():
            if agent_name != current_agent.name:
                context_parts.append(f"[{agent_name}]: {context[:100]}...")
        return " | ".join(context_parts) if context_parts else ""
    
    def get_disclaimer(self) -> str:
        """Standard financial disclaimer"""
        return """
        ⚠️ **Disclaimer:** This is AI-generated financial guidance from specialized agents. 
        While we strive for accuracy, this should not replace professional financial advice. 
        Please consult a certified financial advisor before making important financial decisions.
        """
    
    def get_agent_status(self) -> Dict:
        """Get status of all agents"""
        return {
            'agents': [agent.to_dict() for agent in self.agent_list],
            'conversation_count': len(self.conversation_history),
            'total_queries': sum(a.queries_handled for a in self.agent_list)
        }
    
    def reset_context(self):
        """Reset cross-agent context"""
        self.cross_agent_context = {}
        self.conversation_history = []
        for agent in self.agent_list:
            agent.queries_handled = 0
            agent.total_response_time = 0


class MultiAgentRouter:
    """Legacy router - kept for backward compatibility"""
    
    def __init__(self, client: Groq):
        self.client = client
        self.chief_planner = ChiefPlanner(client)
    
    def route_query(self, query: str) -> FinancialAgent:
        """Determine which agent should handle the query"""
        return self.chief_planner.agents.get('general', GENERAL_AGENT)
    
    def process_query(self, query: str, chat_history: List = None) -> Dict:
        """Process query using the Chief Planner"""
        return self.chief_planner.process_query(query, chat_history)
    
    def get_performance_stats(self) -> Dict:
        """Get performance metrics"""
        return self.chief_planner.get_agent_status()