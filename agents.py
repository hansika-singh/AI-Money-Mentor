from groq import Groq, GroqError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY", "YOUR_API_KEY"))

# -----------------------
# SIP AGENT
# -----------------------
def sip_agent(query):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",   # fast & free
            messages=[
                {"role": "system", "content": "You are a SIP investment advisor for India."},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content
    except GroqError as e:
        print(f"Groq API Error in sip_agent: {e}")
        return "Sorry, I'm unable to process your SIP query at the moment due to API issues. Please try again later."
    except Exception as e:
        print(f"Unexpected error in sip_agent: {e}")
        return "An unexpected error occurred. Please try again later."


# -----------------------
# TAX AGENT
# -----------------------
def tax_agent(query):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a tax advisor for India."},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content
    except GroqError as e:
        print(f"Groq API Error in tax_agent: {e}")
        return "Sorry, I'm unable to process your tax query at the moment due to API issues. Please try again later."
    except Exception as e:
        print(f"Unexpected error in tax_agent: {e}")
        return "An unexpected error occurred. Please try again later."


# -----------------------
# LLM ROUTER (MAIN BRAIN)
# -----------------------
def route_query(query):
    routing_prompt = f"""
    Classify the user's query into one of these categories:
    1. SIP
    2. TAX

    Only return ONE word: SIP or TAX

    Query: {query}
    """

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": routing_prompt}]
        )
        decision = response.choices[0].message.content.strip().upper()
        return decision
    except GroqError as e:
        print(f"Groq API Error in route_query: {e}")
        return "ERROR"
    except Exception as e:
        print(f"Unexpected error in route_query: {e}")
        return "ERROR"

# -----------------------
# MAIN AGENT SYSTEM
# -----------------------
def agent(query):
    try:
        decision = route_query(query)

        if decision == "ERROR":
            return "Sorry, I'm experiencing technical difficulties. Please try again later."

        if "SIP" in decision:
            return sip_agent(query)

        elif "TAX" in decision:
            return tax_agent(query)

        else:
            return "Sorry, I can help with SIP or Tax queries only."
    except Exception as e:
        print(f"Unexpected error in agent: {e}")
        return "An unexpected error occurred. Please try again later."

# -----------------------
# TEST
# -----------------------
if __name__ == "__main__":
    while True:
        q = input("Ask: ")
        print(agent(q))
