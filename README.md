# 💸 SahiRate — know your real rate before you quote

A small SaaS for Pakistani freelancers. It works backwards from the rupees you need each
month to the minimum rate you should quote, after every marketplace fee, withdrawal
charge, currency-conversion markup and tax.

## The problem

Pakistan's freelance economy is large and growing fast. Freelancers earned a record
**$1.76 billion in FY2025-26**, up 78% on the year before, and the country has over
**2.37 million registered freelancers**. September 2026 set a new monthly record of
$197 million.

But the dollars a client pays are not the rupees that arrive. Between the two sit:

| Deduction | Typical size |
|---|---|
| Marketplace fee | Upwork 0–15% per contract (variable since May 2025); Fiverr a flat 20% |
| Withdrawal fees | $0–3 per withdrawal depending on route |
| Conversion markup | About 2% on Payoneer (up to 3% on some routes); ~0.4–0.7% on Wise |
| Withholding tax | 0.25% if registered with PSEB, 1% if not |

On top of that, a large share of working hours is unpaid: proposals, revisions, admin
and learning. Most freelancers set rates by gut feel or by copying competitors, so they
never see that a "$10/hr" Fiverr job can be paying them less than their costs.

**SahiRate makes that whole chain visible in one screen.**

## What it does

1. **Find my rate.** Enter the take-home you want, your work expenses, a buffer for slow
   months and your real working hours. SahiRate returns your *floor rate*: the hourly
   price below which a job loses you money.
2. **Check a quote.** Enter an hourly or fixed-price offer and see exactly how many rupees
   land in your bank, your effective hourly rate, and the minimum price to ask for.
3. **Compare platforms.** Upwork vs Fiverr vs a direct client, side by side, for the same
   income goal.
4. **Download** your rate plan as a CSV.

Every default (fees, markups, tax rate, USD→PKR) is editable in the sidebar.

## Project files

```
app.py                  Streamlit interface
calculator.py           Pricing engine (pure Python, no Streamlit import)
tests/test_calculator.py  11 unit tests for the pricing engine
requirements.txt        streamlit, plotly, pandas
.streamlit/config.toml  Theme
```

## Run it on your computer

```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -v   # run the tests
```

## Publish it free on Streamlit Community Cloud

1. **Put the code on GitHub.** Create a new public repository (for example `sahirate`)
   and upload every file above, keeping the folder structure. On GitHub's website use
   *Add file → Upload files* and drag the files in. The `.streamlit` folder is hidden on
   most computers; if it doesn't upload, the app still works with the default theme.
2. **Sign in to Streamlit Cloud.** Go to <https://share.streamlit.io> and sign in with your
   GitHub account.
3. **Create the app.** Click *Create app* → *Deploy a public app from GitHub*. Choose your
   repository, branch `main`, and main file `app.py`. Pick a custom URL such as
   `sahirate.streamlit.app`.
4. **Deploy.** The first build takes a few minutes. After that, every change you push to
   GitHub redeploys the app automatically.

## SaaS model

| Plan | Price | What's in it |
|---|---|---|
| Free | PKR 0 | All three calculators (current beta) |
| Pro (planned) | ~PKR 499 / month | Saved clients and quotes, branded PDF quotes and invoices, live USD/PKR rate, GBP/EUR/AED support |
| Agency (planned) | ~PKR 1,999 / month | Team rates, project margin tracking, multiple payout accounts |

**Who it's for:** new and mid-level freelancers on Upwork and Fiverr, students in
freelancing training programmes, and small agencies pricing team work.

**How to reach them:** freelancer Facebook and WhatsApp communities, freelancing courses
and university career centres, and short "how much do you really keep?" videos on
YouTube and TikTok.

## Assumptions and sources (checked November 2026)

- Freelancer earnings FY26 and growth: [Profit / Pakistan Today](https://profit.pakistantoday.com.pk/2026/07/21/pakistans-freelancer-earnings-hit-record-dollar176-billion-in-fy26)
- Registered freelancers: [startup.pk](https://startup.pk/pakistan-freelancers-billion-dollar-it-exports/)
- September 2026 monthly record: [ProPakistani](https://propakistani.pk/2026/10/18/freelancers-set-new-monthly-earnings-record/)
- Upwork variable fee: [Upwork Help Center](https://support.upwork.com/hc/en-us/articles/211062538), [Elevate Pay: Upwork fees in Pakistan](https://www.elevatepay.co/blog/upwork-fees-pakistan)
- Fiverr 20% fee: [AiProposer](https://aiproposer.com/learn/fiverr-service-fee)
- Payoneer and Wise conversion costs: [AbroadMate](https://abroadmate.me/guides/payoneer-vs-wise-pakistan-freelancers-2026), [Aaj News on Payoneer's 3% fee](https://english.aaj.tv/news/amp/330415412)
- 0.25% / 1% tax and extension to June 2029: [Beancount](https://beancount.io/bg/blog/2026/08/13/pakistan-it-freelancers-0-25-percent-pseb-2029-guide), [ETTC](https://ettc.pk/freelancer-tax-in-pakistan-2026/)
- USD/PKR interbank around Rs 277.7: [BOL News](https://www.bolnews.com/pakistan/us-dollar-rate-in-pakistan-down-by-15-paisa-to-rs277-70)

The Upwork Direct to Local Bank conversion markup (1%) is an estimate; users should edit it
to match their own statement.

*SahiRate is a planning tool, not tax or financial advice.*
