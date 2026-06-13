# PDF inbox

Drop PDF files here (`*.pdf`) and Joni reads them on his next cycle: he extracts a few
claim-like sentences and files them as **candidate** claims, anchored to the file as their
source. The Semantic Layer still governs every relation, so dropping a paper here never
lets Joni decide more on its own — it only gives him more to read.

For papers behind a URL (arXiv, SSRN download links, …), add the **direct PDF url** to
`state/pdf_urls.json` (a JSON list of strings) instead; Joni drains the queue respectfully.
arXiv hits are read in full automatically.
