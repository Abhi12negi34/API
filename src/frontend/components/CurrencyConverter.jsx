import React, { useState, useEffect } from 'react';

const CurrencyConverter = () => {
  const [amount, setAmount] = useState(1);
  const [fromCurrency, setFromCurrency] = useState('USD');
  const [toCurrency, setToCurrency] = useState('EUR');
  const [convertedAmount, setConvertedAmount] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const supportedCurrencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD'];

  const handleAmountChange = (e) => {
    const value = parseFloat(e.target.value);
    setAmount(isNaN(value) ? 1 : value);
  };

  const handleFromCurrencyChange = (e) => {
    const value = e.target.value;
    setFromCurrency(value);
  };

  const handleToCurrencyChange = (e) => {
    const value = e.target.value;
    setToCurrency(value);
  };

  const convertCurrency = async () => {
    if (!supportedCurrencies.includes(fromCurrency) || !supportedCurrencies.includes(toCurrency)) {
      setError('Invalid currency codes. Supported currencies: USD, EUR, GBP, JPY, CAD, AUD');
      return;
    }

    if (isNaN(amount) || amount <= 0) {
      setError('Invalid amount. Please enter a positive number.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/currency/convert', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount: amount,
          to_currency: toCurrency,
          from_currency: fromCurrency,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 400) {
          setError(errorData.message || 'Invalid currency codes or amount');
        } else if (response.status === 500) {
          setError('External API failure. Please try again later.');
        } else {
          setError('An unexpected error occurred.');
        }
        return;
      }

      const data = await response.json();
      setConvertedAmount(data.converted_amount);
    } catch (err) {
      setError('An unexpected error occurred while fetching conversion rates.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    convertCurrency();
  }, [amount, fromCurrency, toCurrency]);

  return (
    <div>
      <h2>Currency Converter</h2>
      <div>
        <label htmlFor="amount">Amount:</label>
        <input
          type="number"
          id="amount"
          value={amount}
          onChange={handleAmountChange}
        />
      </div>
      <div>
        <label htmlFor="fromCurrency">From Currency:</label>
        <select id="fromCurrency" value={fromCurrency} onChange={handleFromCurrencyChange}>
          {supportedCurrencies.map((currency) => (
            <option key={currency} value={currency}>
              {currency}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="toCurrency">To Currency:</label>
        <select id="toCurrency" value={toCurrency} onChange={handleToCurrencyChange}>
          {supportedCurrencies.map((currency) => (
            <option key={currency} value={currency}>
              {currency}
            </option>
          ))}
        </select>
      </div>
      <div>
        {loading ? (
          <p>Loading...</p>
        ) : error ? (
          <p style={{ color: 'red' }}>{error}</p>
        ) : (
          <p>
            {amount} {fromCurrency} = {convertedAmount} {toCurrency}
          </p>
        )}
      </div>
    </div>
  );
};

export default CurrencyConverter;