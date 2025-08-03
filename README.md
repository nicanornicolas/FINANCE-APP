# Simple Finance App

## Overview
A Streamlit-based finance application that helps you analyze and categorize your financial transactions.

## Features
- Upload transaction files
- Automatically categorize transactions
- Create and manage expense categories
- Visualize expenses with interactive pie charts
- Track and summarize credits and debits

## Requirements
- Python 3.8+
- Streamlit
- Pandas
- Plotly Express

## Installation
1. Clone the repository
2. Install dependencies: `pip install streamlit pandas plotly`
3. Run the app: `streamlit run main.py`

## Usage
1. Upload a CSV file with transaction details
2. View and edit transaction categories
3. Explore expense summaries and visualizations

## File Structure
- `main.py`: Main Streamlit application
- `categories.json`: Stores user-defined transaction categories
- `sample_bank_statement.csv`: Example transaction file

## Notes
- Supports CSV files with columns: Date, Details, Type, Amount
- Transactions can be manually categorized
- Categories are saved between sessions

## License
Open-source project. Feel free to contribute!
