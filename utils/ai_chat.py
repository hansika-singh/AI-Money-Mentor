from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY", "YOUR_API_KEY"))

def get_ai_reply(message):
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a financial advisor for India. Based on the questions, provide the suggestions and also mention risks associated with them if any."},
                {"role": "user", "content": message}
            ]
        )

        return res.choices[0].message.content

    except Exception as e:
        print("🔥 GROQ ERROR:", e)   # IMPORTANT
        return "AI service is currently unavailable."
