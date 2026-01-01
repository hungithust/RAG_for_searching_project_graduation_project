import pandas as pd
import re


df = pd.read_csv("Scrape/DoAn_HUST_Chrome.csv", encoding="utf-8-sig")

df.drop_duplicates(inplace=True)

cols_to_clean = ["Order", "GiangVien", "TenDeTai", "ChiTiet", "LoaiDoAn"]

for col in cols_to_clean:
    df[col] = df[col].astype(str).str.replace(r'\n|\t', ' ', regex=True).str.strip()
    
