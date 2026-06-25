def data_input(principal, rate, time, income):
  loan_calc=compound_interest_calculation(principal, rate, time)
  emi_calc=emi_calculation(principal, rate, time)
  emi=emi_calc.get("EMI",0)
  check=financial_check(emi, income)
  return {"Loan_Amount":loan_calc.get("Amount",0),
          "Loan_Interest":loan_calc.get("Interest",0),
          "EMI":emi,
          "Net_take_home":emi_calc.get("Net_take_income",0),
          "Ratio":check.get("Ratio",0)
          "Zone":check.get("Zone",0)
  }

def compound_interest_calculation(principal, rate, time):#rate per annum, time in years, amount in rupees
  amt=principal*((1+(rate/100))**T)
  interest=amt-principal
  return {"Amount":amt,"Interest":interest}

def emi_calculation(principal, rate, time):
  m_rate=rate/12
  m_time=time*12
  emi= principal* m_rate *(((1+m_rate)**m_time)/((1+m_rate)**m_time)-1))
  net=income-emi
  return {"EMI":emi,"Net_take_home":net}
  
def financial_check(emi, income):
  ratio=(emi/income)*100
  if ratio<30:
    zone=1
  elif ratio <45:
    zone=0
  else:
    zone=-1
  return {"Ratio":ratio,"Zone":zone}

  
  
  
