# Spotlight

Simple web crawler and topic extractor written in Python, using `requests` for 
HTML-requests, `lda` for topic extraction, `BeautifulSoup` for HTML parsing,
and `spacy` for lemmatization.

## Requirements

`requests`, `lda`, `spacy`, `numpy`, `bs4` installed through for example `pip`

The following corpora for `spacy`: `en_core_web_sm` and `sv_core_news_sm`, 
which can be downloaded using the following commands:

```
python3 -m spacy download en_core_web_sm
python3 -m spacy download sv_core_news_sm
```

## Typical usage

`python3 spotlight.py https://theguardian.com/profile/editorial 50 en` \\
Will crawl the Guardians editorial page 50 times


`python3 spotlight.py https://foxnews.com 100 en --sloppy` \\
Will crawl Fox News 100 times without discrimination, meaning that it will
not adhere to the CSS classes hard coded to ensure a more accurate extraction.
