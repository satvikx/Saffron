import json
import datetime
import pandas as pd
from mstarpy import Funds

class PortfolioAnalyzer:
    def __init__(self, transaction_file):
        self.transactions = self.load_transactions(transaction_file)
        if not self.transactions:
            raise ValueError("No transactions found in the file")
        self.portfolio = {}
        self.current_navs = {}

    def load_transactions(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        transactions = []
        for item in data['data']:
            if 'dtTransaction' in item:
                transactions.extend(item['dtTransaction'])
        return transactions

    def process_transactions(self):
        for transaction in self.transactions:
            scheme = transaction['scheme']
            folio = transaction['folio']
            units = float(transaction['trxnUnits'])
            price = float(transaction['purchasePrice'])
            
            if scheme not in self.portfolio:
                self.portfolio[scheme] = {}
            if folio not in self.portfolio[scheme]:
                self.portfolio[scheme][folio] = []
            
            if units > 0:  # Buy transaction
                self.portfolio[scheme][folio].append((units, price))
            else:  # Sell transaction
                self.process_sell(scheme, folio, abs(units))

    def process_sell(self, scheme, folio, units_to_sell):
        while units_to_sell > 0 and self.portfolio[scheme][folio]:
            units, price = self.portfolio[scheme][folio][0]
            if units <= units_to_sell:
                units_to_sell -= units
                self.portfolio[scheme][folio].pop(0)
            else:
                self.portfolio[scheme][folio][0] = (units - units_to_sell, price)
                units_to_sell = 0

    def fetch_current_navs(self):
        for scheme in self.portfolio:
            isin = next(t['isin'] for t in self.transactions if t['scheme'] == scheme)
            fund = Funds(term=isin, country="in")
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=1)
            history = fund.nav(start_date=start_date, end_date=end_date, frequency="daily")
            if isinstance(history, list):
                history = pd.DataFrame(history)
            
            self.current_navs[scheme] = history.iloc[-1]['nav']

    def calculate_portfolio_value(self):
        total_value = 0
        total_gain = 0
        
        for scheme, folios in self.portfolio.items():
            scheme_units = sum(sum(units for units, _ in folio) for folio in folios.values())
            current_nav = self.current_navs[scheme]
            scheme_value = scheme_units * current_nav
            
            acquisition_cost = sum(sum(units * price for units, price in folio) for folio in folios.values())
            scheme_gain = scheme_value - acquisition_cost
            
            total_value += scheme_value
            total_gain += scheme_gain
            
            print(f"Scheme: {scheme}")
            print(f"  Net Units: {scheme_units}")
            print(f"  Current Value: {scheme_value}")
            print(f"  Gain: {scheme_gain}")
        
        print(f"Total Portfolio Value: {total_value}")
        print(f"Total Portfolio Gain: {total_gain}")

    def analyze(self):
        self.process_transactions()
        self.fetch_current_navs()
        self.calculate_portfolio_value()

try:
    analyzer = PortfolioAnalyzer('transaction_detail.json')
    analyzer.analyze()
except ValueError as e:
    print(f"Error: {e}")
except FileNotFoundError:
    print("Error: Transaction file not found")
except json.JSONDecodeError:
    print("Error: Invalid JSON format in the transaction file")