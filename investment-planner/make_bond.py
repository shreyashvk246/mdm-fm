import pandas as pd, numpy as np
df = pd.read_csv('data/nifty50_monthly.csv')
d = pd.to_datetime(df['Date'])
np.random.seed(42)
r = np.random.normal(0.06/12, 0.01, len(d))
p = 100 * (1+r).cumprod()
out = pd.DataFrame({'Date': d.dt.strftime('%Y-%m-%d'), 'Ticker': 'BOND_PROXY', 'Close': p, 'Adj Close': p})
out.to_csv('data/giltbees_monthly.csv', index=False)
print('done')
