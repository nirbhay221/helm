"""A real recorded weekly-demand series, used to drive the dashboard scenario.

Source: UCI Machine Learning Repository, "Sales_Transactions_Dataset_Weekly"
(Tan & San Lau), 800 products x 52 weeks of actual unit sales.
https://archive.ics.uci.edu/dataset/396/sales+transactions+dataset+weekly

This is product P263: it sits near 15-20 units a week for a long stretch, then
genuinely surges to a peak of 44 (about 2.5x its normal level) before collapsing
back to 10. That surge and collapse are real recorded demand, not a shock we
injected. Helm's plan is a flat naive baseline (it does not know the surge is
coming), so the gap between plan and this real demand is the variance the
controller has to close. Using real demand is the point: the controller is
reacting to something it did not author.
"""
from __future__ import annotations

PRODUCT_CODE = "P263"

# Actual weekly unit sales, weeks 0..51 (verbatim from the dataset).
P263_WEEKLY = [
    18, 12, 20, 21, 12, 24, 13, 13, 23, 18, 19, 19, 16, 12, 23, 14, 16, 17,
    26, 23, 30, 19, 21, 27, 44, 32, 10, 10, 13, 16, 13, 10, 15, 14, 11, 15,
    20, 10, 15, 20, 13, 19, 17, 13, 20, 18, 20, 19, 14, 19, 20, 23,
]

# Flat planned (forecast) demand a business would set ahead of time: the rounded
# median of the series. Reality deviates from this plan; that deviation is the job.
PLANNED_DEMAND = 17.0
