# SEC Concept Mapping Registry

Only standard US-GAAP/DEI concepts are mapped automatically. Company extensions are flagged as unmapped.

| Variable | Candidate concepts, priority order | Unit | Kind | Audit status |
|---|---|---|---|---|
| Revenue | RevenueFromContractWithCustomerExcludingAssessedTax; SalesRevenueNet; Revenues | USD | duration | present in all 8 audited issuers |
| Net income | NetIncomeLoss | USD | duration | present in all 8 |
| Assets | Assets | USD | instant | present in all 8 |
| Liabilities | Liabilities | USD | instant | missing for KO audit mapping |
| Equity | StockholdersEquity; StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest | USD | instant | present in all 8 |
| Operating income | OperatingIncomeLoss | USD | duration | unavailable for XOM/JPM audit mapping |
| Gross profit | GrossProfit | USD | duration | unavailable for XOM/JPM/WMT audit mapping |
| Cash | CashAndCashEquivalentsAtCarryingValue | USD | instant | present in all 8 |
| Shares outstanding | dei:EntityCommonStockSharesOutstanding | shares | instant | present in all 8 |
| Capex | PaymentsToAcquirePropertyPlantAndEquipment | USD | duration | unavailable for JPM audit mapping |

Facts retain CIK, taxonomy, concept, unit, fiscal period, form, accession, filing and acceptance times, amendment flag, and mapping confidence. No extension is silently substituted.
