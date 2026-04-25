# 🧠📈 Quantitative Cryptocurrency Trading Bot

A real-time algorithmic trading bot built in Python that analyzes cryptocurrency market data, generates trading signals, and executes trades using rule-based strategies with integrated risk management.

---

## 🚀 Overview

This project is a quantitative trading system designed to automate decision-making in cryptocurrency markets.

The bot operates on a **1-minute timeframe**, continuously analyzing market conditions using technical indicators and executing trades based on predefined logic.

The goal is to build a **data-driven, automated trading system** that can be improved and optimized over time.

---

## ⚙️ Features

- 📊 Real-time market data processing  
- 📈 Technical indicator-based strategies:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - EMA (Exponential Moving Averages)  
- 🤖 Automated Buy/Sell signal generation  
- 🛡️ Risk management system:
  - Stop-Loss  
  - Take-Profit  
  - Cooldown mechanism  
- 🔁 Backtesting on historical data  
- 📉 Performance tracking (PnL, trade logs, equity curve)  

---

## 🧮 Strategy Logic

The bot uses a combination of indicators to confirm trades:

### 🟢 Buy Conditions:
- RSI below threshold (oversold zone)  
- Price near EMA support  
- MACD bullish crossover  

### 🔴 Sell Conditions:
- RSI above threshold (overbought zone)  
- Price near EMA resistance  
- MACD bearish crossover  

All trades include predefined **Stop-Loss** and **Take-Profit** levels for controlled risk.

---

## 🏗️ System Architecture

Market Data → Indicator Engine → Signal Logic → Trade Execution → Logging & Monitoring

---

## 📊 Backtesting & Performance

The strategy is tested on historical data to evaluate:

- Win Rate  
- Profit/Loss (PnL)  
- Maximum Drawdown  
- Trade Frequency  

> Note: Performance varies depending on market conditions and parameter tuning.

---

## 🛠️ Tech Stack

- **Python**  
- **Pandas / NumPy** – Data processing  
- **Matplotlib** – Visualization  
- **Binance API (Testnet)** – Market data & execution  
- **REST APIs**

---

## 📁 Project Structure
