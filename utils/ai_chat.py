from groq import Groq, GroqError
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

    except GroqError as e:
        print(f"🔥 GROQ API ERROR: {e}")
        return "AI service encountered an API error. Please check your GROQ_API_KEY configuration and try again."
    except Exception as e:
        print(f"🔥 UNEXPECTED ERROR: {e}")
        return "AI service is currently unavailable."
