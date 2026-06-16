// Retirement Simulator - Complete Working Code

let growthChart = null;

// Format currency in Indian Rupees
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0,
        minimumFractionDigits: 0
    }).format(amount);
}

// Calculate Future Value of Monthly Investments
function calculateFutureValue(monthlyInvestment, annualReturn, years) {
    if (monthlyInvestment <= 0 || annualReturn <= 0 || years <= 0) return 0;
    
    const monthlyRate = annualReturn / 100 / 12;
    const months = years * 12;
    
    if (monthlyRate === 0) return monthlyInvestment * months;
    
    // FV = P * ((1+r)^n - 1) / r * (1+r)
    const fv = monthlyInvestment * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate) * (1 + monthlyRate);
    return fv;
}

// Calculate Future Value of Existing Savings
function calculateLumpsumFutureValue(currentSavings, annualReturn, years) {
    if (currentSavings <= 0 || annualReturn <= 0 || years <= 0) return currentSavings;
    
    const rate = annualReturn / 100;
    return currentSavings * Math.pow(1 + rate, years);
}

// Adjust for Inflation
function adjustForInflation(nominalValue, inflationRate, years) {
    if (inflationRate <= 0 || years <= 0) return nominalValue;
    
    const inflationRateDecimal = inflationRate / 100;
    return nominalValue / Math.pow(1 + inflationRateDecimal, years);
}

// Calculate Required Monthly SIP to Reach Goal
function calculateRequiredSIP(targetRealCorpus, annualReturn, inflationRate, years, currentSavings) {
    if (targetRealCorpus <= 0 || years <= 0) return 0;
    
    // First, calculate future value of current savings
    const lumpsumFV = calculateLumpsumFutureValue(currentSavings, annualReturn, years);
    
    // Adjust target to nominal terms (account for inflation)
    const inflationRateDecimal = inflationRate / 100;
    const targetNominal = targetRealCorpus * Math.pow(1 + inflationRateDecimal, years);
    
    // Remaining amount needed from SIP
    const remainingNeeded = Math.max(0, targetNominal - lumpsumFV);
    
    if (remainingNeeded <= 0) return 0;
    
    // Calculate required SIP
    const monthlyRate = annualReturn / 100 / 12;
    const months = years * 12;
    
    // P = FV * r / ((1+r)^n - 1) / (1+r)
    const sip = remainingNeeded * monthlyRate / (Math.pow(1 + monthlyRate, months) - 1) / (1 + monthlyRate);
    
    return sip;
}

// Generate Yearly Data for Chart
function generateYearlyData(currentAge, retirementAge, monthlyInvestment, currentSavings, returnRate, inflationRate) {
    const years = retirementAge - currentAge;
    const data = {
        years: [],
        nominalCorpus: [],
        realCorpus: []
    };
    
    let runningLumpsum = currentSavings;
    
    for (let year = 0; year <= years; year++) {
        const ageAtYear = currentAge + year;
        data.years.push(ageAtYear);
        
        // Calculate corpus at this year
        const fvFromSIP = calculateFutureValue(monthlyInvestment, returnRate, year);
        const fvFromLumpsum = calculateLumpsumFutureValue(currentSavings, returnRate, year);
        const totalNominal = fvFromSIP + fvFromLumpsum;
        
        data.nominalCorpus.push(totalNominal);
        
        // Adjust for inflation
        const totalReal = adjustForInflation(totalNominal, inflationRate, year);
        data.realCorpus.push(totalReal);
    }
    
    return data;
}

// Update Chart
function updateChart(yearlyData) {
    const ctx = document.getElementById('growthChart').getContext('2d');
    
    if (growthChart) {
        growthChart.destroy();
    }
    
    growthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: yearlyData.years,
            datasets: [
                {
                    label: 'Nominal Corpus (Without Inflation)',
                    data: yearlyData.nominalCorpus,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6
                },
                {
                    label: 'Real Corpus (Inflation-Adjusted)',
                    data: yearlyData.realCorpus,
                    borderColor: '#f5576c',
                    backgroundColor: 'rgba(245, 87, 108, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            let value = context.raw;
                            return `${label}: ${formatCurrency(value)}`;
                        }
                    }
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    },
                    title: {
                        display: true,
                        text: 'Corpus Value (₹)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Age (Years)'
                    }
                }
            }
        }
    });
}

// Update Insights
function updateInsights(currentAge, retirementAge, totalNominal, totalReal, monthlyInvestment, returnRate, inflationRate) {
    const years = retirementAge - currentAge;
    const purchasingPowerLoss = ((totalNominal - totalReal) / totalNominal * 100).toFixed(1);
    
    // Calculate required SIP for a realistic goal (e.g., 5x annual expenses estimate)
    // For demo, let's show a suggestion based on current data
    const requiredSIPForBetterCorpus = calculateRequiredSIP(totalReal * 1.5, returnRate, inflationRate, years, 0);
    
    let insightsHtml = `
        <div class="row">
            <div class="col-md-6 mb-3">
                <div class="alert alert-success">
                    <strong>✅ Key Finding:</strong><br>
                    Your retirement corpus in today's value will be <strong>${formatCurrency(totalReal)}</strong>.
                </div>
            </div>
            <div class="col-md-6 mb-3">
                <div class="alert alert-warning">
                    <strong>⚠️ Inflation Impact:</strong><br>
                    Inflation will reduce purchasing power by <strong>${purchasingPowerLoss}%</strong>.
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-12 mb-3">
                <div class="alert alert-info">
                    <strong>💡 What this means:</strong><br>
                    While your bank statement will show <strong>${formatCurrency(totalNominal)}</strong>, 
                    you'll only be able to buy what <strong>${formatCurrency(totalReal)}</strong> buys today.
                </div>
            </div>
        </div>
    `;
    
    // Add SIP recommendation if needed
    if (requiredSIPForBetterCorpus > 0 && requiredSIPForBetterCorpus < 100000) {
        insightsHtml += `
            <div class="alert alert-secondary">
                <strong>📈 Pro Tip:</strong><br>
                To build a corpus 50% larger than your current projection, invest 
                <strong>${formatCurrency(requiredSIPForBetterCorpus)}/month</strong> instead of ${formatCurrency(monthlyInvestment)}/month.
            </div>
        `;
    }
    
    document.getElementById('insights').innerHTML = insightsHtml;
}

// Main Calculate Function
function calculateRetirement() {
    // Get input values
    const currentAge = parseInt(document.getElementById('currentAge').value);
    const retirementAge = parseInt(document.getElementById('retirementAge').value);
    const currentSavings = parseFloat(document.getElementById('currentSavings').value);
    const monthlyInvestment = parseFloat(document.getElementById('monthlyInvestment').value);
    const returnRate = parseFloat(document.getElementById('returnRate').value);
    const inflationRate = parseFloat(document.getElementById('inflationRate').value);
    
    // Validation
    if (currentAge >= retirementAge) {
        document.getElementById('insights').innerHTML = `
            <div class="alert alert-danger">
                ❌ Retirement age must be greater than current age!
            </div>
        `;
        return;
    }
    
    const years = retirementAge - currentAge;
    
    // Calculate final corpus
    const fvFromSIP = calculateFutureValue(monthlyInvestment, returnRate, years);
    const fvFromLumpsum = calculateLumpsumFutureValue(currentSavings, returnRate, years);
    const totalNominal = fvFromSIP + fvFromLumpsum;
    const totalReal = adjustForInflation(totalNominal, inflationRate, years);
    
    // Update summary cards
    document.getElementById('nominalCorpus').innerHTML = formatCurrency(totalNominal);
    document.getElementById('realCorpus').innerHTML = formatCurrency(totalReal);
    
    // Generate yearly data for chart
    const yearlyData = generateYearlyData(currentAge, retirementAge, monthlyInvestment, currentSavings, returnRate, inflationRate);
    
    // Update chart
    updateChart(yearlyData);
    
    // Update insights
    updateInsights(currentAge, retirementAge, totalNominal, totalReal, monthlyInvestment, returnRate, inflationRate);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('retirementForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            calculateRetirement();
        });
    }
    
    // Auto-calculate on page load with default values
    calculateRetirement();
});