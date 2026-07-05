from groq import Groq
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()
def data_input(principal, rate, time, income):
  loan_calc=compound_interest_calculation(principal, rate, time)
  emi_calc=emi_calculation(principal, rate, time, income)
  emi=emi_calc.get("EMI",0)
  check=financial_check(emi, income)
  metrics={"Loan_Amount":loan_calc.get("Amount",0),
          "Loan_Interest":loan_calc.get("Interest",0),
          "EMI":emi,
          "Net_take_income":emi_calc.get("Net_take_home",0),
          "EMI to Income Ratio":check.get("Ratio",0),
          "Zone":check.get("Zone",0)
          }
  advice=financial_advice(metrics)
  print("Working backend")
  return {"Loan_Amount":round(loan_calc.get("Amount",0),2),
          "Loan_Interest":round(loan_calc.get("Interest",0),2),
          "EMI":round(emi,2),
          "Net_take_income":round(emi_calc.get("Net_take_home",0),2),
          "Ratio":round(check.get("Ratio",0),2),
          "Zone":round(check.get("Zone",0),2),
          "Advice": advice
  }

def compound_interest_calculation(principal, rate, time):#rate per annum, time in years, amount in rupees
  amt=principal*((1+(rate/100))**time)
  interest=amt-principal
  return {"Amount":amt,"Interest":interest}

def emi_calculation(principal, rate, time, income):
  m_rate=rate/12
  m_time=time*12
  try:
    if m_rate==0:
      emi=principal/m_time
    else:
      emi= (principal* m_rate/100 *(1+m_rate/100)**m_time)/(((1+m_rate/100)**m_time)-1)
  except Exception as e:
    emi=0
  net=income-emi
  return {"EMI":emi,"Net_take_home":net}
  
def financial_check(emi, income):
  if income is None or income <= 0:
    raise ValueError("Income must be greater than 0")
  ratio=(emi/income)
  percentage=(emi/income)*100
  if percentage<30:
    zone=1
  elif percentage <45:
    zone=0
  else:
    zone=-1
  return {"Ratio":ratio,"Zone":zone}

client = Groq(api_key=os.getenv("GROQ_API_KEY", "YOUR_API_KEY"))


def financial_advice(message):
    try:
        user_prompt_string = json.dumps(message, indent=2)
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a loan advisor, based on the info provided, provide the answers to the following questions:Are there any risks associated with the loan? What should they improve to make the loan suitable for them? All the prices are in rupees.For zone, 1 is safe, 0 is moderate and -1 is risky. Be precise and accurate."},
                {"role": "user", "content": f"Here are the financial metrics:{user_prompt_string}"}
            ]
        )

        return res.choices[0].message.content

    except Exception as e:
        print("🔥 GROQ ERROR:", e)  
        return "AI service is currently unavailable."

  
  
  
