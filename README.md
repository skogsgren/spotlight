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

The syntax for usage is `python3 spotlight.py URL COUNT LANG`, where `URL` is
replaced by the website you want it to crawl, `COUNT` by the number of articles
you want it to crawl before stopping (larger number gives better results), and
`LANG` by either 'en' for English or 'sv' for Swedish.

Output will be written to a txt-file with the base URL as filename (e.g. 
'theguardian.txt' for the example given above, as well as the same output 
being given in the terminal. Example output for the command
`python3 spotlight.py https://aftonbladet.se/ledare 1500 sv`:

```
crawled 1501 pages on https://aftonbladet.se/ledare
TOPICS:
Topic 0: finnas barn komma samhälle rätt ställe länge
Topic 1: Sverige hålla säga ändå fall därför komma
Topic 2: skola ekonomisk pengar skatt välfärd värld sänka
Topic 3: människa person egen vecka politisk gång våld
Topic 4: jobb företag betala pengar svensk krona arbetsmarknad
Topic 5: direkt Aftonbladet Facebook medi skriva bild tidning
Topic 6: säga stor Stockholm vård pandemin region annan
Topic 7: land finnas stor annan visa komma Sverige
Topic 8: politik regering fråga politisk parti hålla säga
Topic 9: Ryssland president Ukraina rysk Lindberg riksdag makt
```

and `python3 spotlight.py https://theguardian.com/profile/editorial 3000 en`:

```
crawled 3001 pages on https://www.theguardian.com/profile/editorial
TOPICS:
Topic 0: health pandemic government minister England public week
Topic 1: country political election economic voter party politic
Topic 2: century book moment write once history London
Topic 3: election democracy most power party political president
Topic 4: Brexit minister Britain Boris Johnson party Theresa
Topic 5: most human such important show example form
Topic 6: long week already case seem happen clear
Topic 7: government decade money company income high market
Topic 8: president Trump international China country Donald military
Topic 9: report police case abuse government court public
```

and `python3 spotlight.py https://www.friatider.se/opinion 2000 sv --sloppytext`:

```
crawled 2001 pages on https://www.friatider.se/opinion
TOPICS:
Topic 0: bild plus lika därför höra negativ dålig
Topic 1: cool bluff låta Låter därför ensam fungera
Topic 2: utmanas Einár Jönsson bild därför september liberal
Topic 3: enskild istället varför tidning vänster varför?0 politik
Topic 4: skriva bild plus kalla anse åsikt endast
Topic 5: fler egen finnas stenålder problem bikini olik
Topic 6: fokus journalist folkslag icke-interventionism nyhet underkläd Utrikespolitisk
Topic 7: cool yrkesområde intressant avskaffande Aron Afghanistan etablissemangen
Topic 8: bild plus skriva sätt säga stark amerikansk
Topic 9: vanlig därför säga växa länge lång skriva 
```