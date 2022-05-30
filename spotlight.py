__doc__ = """
Crawls a given website for text, analyzes topics for that text.

Spotlight will take a given url and crawl that url given two arguments: the
amount of articles/pages to crawl, and what language that website is in.
Currently two languages are supported: English and Swedish, specified with
'en' and 'sv' respectively.

SYNOPSIS:
    spotlight.py [URL] [COUNT] [LANG] [OPTION]

OPTIONS:
    --sloppy        will extract both links and text without checking for valid
                    CSS class, i.e. without discrimination.
    --sloppytext    will extract text without discrimination.
    --sloppylink    will extract links without discrimation.

Typical usage example:
        python3 spotlight.py URL 500 en
        python3 spotlight.py URL 1000 sv --sloppytext
"""

import logging
import sys
import re
from bs4 import BeautifulSoup
import numpy as np
import lda
import spacy
import requests

# Basic logging configuration
logging.basicConfig(format='%(asctime)s %(message)s')
logging.getLogger().setLevel(logging.INFO)


class Crawler():
    """Handles link crawling and link extraction.

    This class handles, and keeps track of, the visited websites as well as
    giving the appropriate arguments for the extraction class 'Digger'.

    Attributes:
        vis_count: amount of visited websites.
        to_visit: the list of websites to visit.
        visited: the set of visited websites, i.e. already crawled websites.
        vocab_set: the set of unique (lemmatized) words in all the articles.
        article_list: a list where each element is one article. Is used for
                      the numpy array in topic extraction.
        url_classes: a list of manually inspected CSS classes; inline comments
                     for the appropriate place where I found them. Teddit was
                     chosen instead of reddit because of its lack of
                     javascript.
        embedded_url_classes: a list of manually inspected *embedded* CSS
                              classes; meaning that they are classes which
                              links are subordinate to. These are necessary
                              because some websites have links
                              without CSS classes, but which are always
                              subordinate to other classes.
    """
    def __init__(self):
        self.vis_count = 0
        self.to_visit = list()
        self.visited = set()
        self.vocab_set = set()
        self.article_list = list()
        self.url_classes = [
                'css-826iu8',  # Aftonbladets ledarsida
                'css-1gd0wp5',  # Aftonbladets ledarsida, nav
                'js-headline-text',  # The Guardian Editorial: main page
                'pagination__action--static',  # The Guardian, nav
                'css-cywksh',  # The Guardian Opinion: inline
                'comments'  # teddit comment section
                ]
        self.embedded_url_classes = [
                'view-more-links',  # teddit nav button
                'teaser-wrapper',  # Friatider opinion
                'pager-next'  # Friatider opinion, nav
                ]

    def request(self, url):
        """Takes a URL as input and handles the HTML request of that link"""
        url_base = re.match(r'.+\.\w+', url).group(0)
        html_request = requests.get(url)

        try:
            # i.e. if the request is successful.
            if html_request.status_code == 200:
                html = html_request.text
            else:
                html = '<!-- -->'
                print('404 error, but keepin\' on keepin\' on...')
        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.InvalidSchema):
            html = '<!-- -->'
            print('404 error, but keepin\' on keepin\' on...')

        soup = BeautifulSoup(html, 'html.parser')
        chefsoup = soup.find_all('a')
        peasoup = soup.find_all('p')
        soups_and_chowders = {'soup': soup,
                              'url_base': url_base,
                              'peasoup': peasoup,
                              'chefsoup': chefsoup}
        return soups_and_chowders

    def spider(self, url, count, lang, sloppy):
        """Handles the "delegation of labor" to the other functions in this,
           as well as the attribution of the other digger, class. Finally
           it composes the output when it is finished."""
        url_base = re.search(r'\w+\.\w+', url).group(0)
        if url not in self.to_visit:
            self.to_visit.append(url)
            for link in self.to_visit:
                if link not in self.visited and self.vis_count <= count:
                    soups = self.request(link)
                    extracter = Digger()
                    # Only for logging purposes, a simple solution
                    # so that logging lines don't exceed 80 lines while
                    # also providing a simple progress bar.
                    rel_count = f"{self.vis_count}/{count}"

                    logging.info(f"{rel_count} Extracting text from {link}")
                    text = extracter.extract_text(soups['soup'],
                                                  soups['peasoup'],
                                                  sloppy['text'])
                    lemma = extracter.lemmatize(text, lang)
                    # Checks the extracted lemmatized words for uniqueness
                    # to the vocabulary set, and then adds the article if it
                    # isn't empty.
                    if lemma != []:
                        for word in lemma:
                            if word not in self.vocab_set:
                                self.vocab_set.add(word)
                        self.article_list.append(' '.join(lemma))

                    logging.info(f"{rel_count} Extracting links from {link}")
                    self.get_links(soups['soup'],
                                   soups['chefsoup'],
                                   soups['url_base'],
                                   sloppy['link'])
                    self.visited.add(link)
                    self.vis_count += 1
                else:
                    pass
            try:
                result = extracter.extract_topic(
                        self.article_list, tuple(self.vocab_set))
                with open(f'{url_base}.txt', 'a') as filename:
                    filename.write(f'\ncrawled {len(self.visited)} pages\
                                    on {url}\
                                    \n{result} \n')
                print(f'\ncrawled {len(self.visited)} pages on {url}\
                        \n{result} \n')
            except UnboundLocalError:
                print('Something went wrong during extraction; which'
                      + '\n probably means that you entered a website where'
                      + '\n there are no appropriate CSS classes. Try again'
                      + '\n with either the --sloppytext or --sloppy flag.')

    def format_links(self, url_base, link):
        """ Ensures that relative links will be handled correctly."""
        try:
            if link.get('href').startswith('/'):
                final_link = url_base + link.get('href')
                return final_link
            else:
                final_link = link.get('href')
                return final_link
        except(AttributeError, UnboundLocalError):
            return url_base

    def get_links(self, soup, chefsoup, url_base, sloppy):
        """ Handles links in closed CSS-classes, and handles the --sloppy
            flag """
        for link in chefsoup:
            final_link = self.format_links(url_base, link)
            try:
                # Ensures that it doesn't crawl outside of the domain.
                if final_link.startswith(url_base):
                    if not sloppy:
                        for cl in self.url_classes:
                            try:
                                if cl in link.attrs['class']:
                                    self.to_visit.append(final_link)
                            except KeyError:
                                if sloppy:
                                    self.to_visit.append(final_link)
                                else:
                                    pass
                    if sloppy:
                        self.to_visit.append(final_link)
            except UnboundLocalError:
                pass

        # Handles links for embedded_url classes.
        if not sloppy:
            for cl in self.embedded_url_classes:
                embedded = soup.find_all(class_=cl)
                for link in embedded:
                    try:
                        final_link = self.format_links(
                                url_base, link.find('a'))
                        # Ensures that it doesn't crawl outside of the domain.
                        if final_link.startswith(url_base):
                            self.to_visit.append(final_link)
                        else:
                            pass
                    except UnboundLocalError:
                        pass


class Digger:
    """ Responsible for extracting text and topics from raw HTML.

    Includes functions for: 
        extract_text, 
        lemmatize, 
        extract_topic.
    """

    def extract_text(self, soup, peasoup, sloppy):
        """Extracts text from the <p> soup that it takes as input according
           to the CSS classes below and the sloppy flag. Also creates new
           <p> soups according to the list of embedded classes for text
           that lacks classes in their <p> tags but are subordinate to other
           classes."""
        extracted_text = list()
        # These are checked by manually inspecting the CSS of articles.
        css_classes = [
                'css-1dznooa',  # Aftonbladet
                'dcr-xry7m2',  # The Guardian
                'dcr-1of5t9g'  # The Guardian Editorial Article
                ]
        embedded_classes = [
                'md',  # teddit comments
                'field-item'  # Friatider article text
                ]

        for paragraph in peasoup:
            if paragraph.get_text() not in extracted_text:
                # Goes through each of the css_classes and appends the 
                # extracted text iff there is a match.
                if not sloppy:
                    for cl in css_classes:
                        try:
                            if cl in paragraph.attrs['class']:
                                extracted_text.append(paragraph.get_text())
                        # Because some <p> tags lack classes.
                        except KeyError:
                            pass
                # If sloppy is detected, add the text. Note here that
                # if the paragraph also has a class that is in the
                # CSS-classes it will be added twice.
                if sloppy:
                    extracted_text.append(paragraph.get_text())
        if not sloppy:
            for cl in embedded_classes:
                embedded = soup.find_all(class_=cl)
                for paragraph in embedded:
                    try:
                        small_peasoup = paragraph.find('p')
                        if small_peasoup.get_text() not in extracted_text:
                            extracted_text.append(small_peasoup.get_text())
                    except AttributeError:
                        pass

        return ' '.join(extracted_text)

    def lemmatize(self, article, lang):
        """Lemmatizes the words of an article using spacy, as well as sorting
        out any words lacking meaningful semantic meaning (by use of a
        frequency list)."""

        # Grabbed from https://universaldependencies.org/u/pos/,
        # "closed class words"
        closed_class_words = ['PUNCT',
                              'SYM',
                              'ADP',
                              'AUX',
                              'CCONJ',
                              'DET',
                              'NUM',
                              'PART',
                              'PRON',
                              'SCONJ']
        frequency_count = 0
        frequency_list = list()

        # There is most certainly a cleaner way to do this, but seeing that the
        # datasets are so different I thought the simplest, and most fool-
        # proof method was by duplicating the conditionals 
        # and then changing small things as needed. 
        # This can easily be expanded to encompass for more
        # languages as needed. See https://spacy.io/usage/models/#languages.
        if lang == 'en':
            nlp = spacy.load("en_core_web_sm")
            with open("frequency-en.csv", 'r') as frequency:
                for word in frequency:
                    word_list = word.split()
                    if frequency_count <= 150:
                        frequency_list.append(word_list[1])
                        frequency_count += 1
                    if frequency_count > 150:
                        break

        elif lang == 'sv':
            nlp = spacy.load("sv_core_news_sm")
            with open("frequency-sv.tsv", 'r') as frequency:
                for word in frequency:
                    word_list = word.split('\t')
                    if frequency_count <= 150:
                        frequency_list.append(word_list[0])
                        frequency_count += 1
                    if frequency_count > 150:
                        break
        else:
            raise NameError('Please enter either sv or en as language')

        vocab = list()
        doc = nlp(article)
        for token in doc:
            lemma = token.lemma_
            if (lemma not in vocab
                    and token.pos_ not in closed_class_words
                    # Because it is very uncommon that a word with less than
                    # three characters has any significant semantic meaning.
                    and len(lemma) > 3
                    and lemma not in frequency_list
                    # Manually added exceptions that spacy lemmatized 
                    # wrong during testing.
                    and '%' not in lemma
                    and '"' not in lemma):
                vocab.append(lemma)
        return vocab

    def extract_topic(self, articles, uniq_words):
        """ Takes a list of articles, as well as a set of vocabulary. This is
            used to create a numpy array that is then analyzed through lda."""
        article_count = 0
        for article in articles:
            article_count += 1
            logging.info(f"Analyzing text in article {article_count}")
            array_column = list()
            for word in uniq_words:
                word_count = 0
                for article_word in article.split():
                    if article_word == word:
                        word_count += 1
                array_column.append(word_count)
            try:
                row_to_add = np.array([array_column])
                topic_array = np.concatenate([topic_array, row_to_add], axis=0)
            except NameError:
                topic_array = np.array([array_column])
        model = lda.LDA(n_topics=10, n_iter=155, random_state=1)
        model.fit(topic_array)
        topic_word = model.topic_word_
        n_top = 8
        result = "TOPICS:"
        for i, topic_dist in enumerate(topic_word):
            topic_words = np.array(
                    uniq_words)[np.argsort(topic_dist)][:-n_top:-1]
            result = result + '\nTopic {}: {}'.format(i, ' '.join(topic_words))
        return result


# This simply deals with the input when you run the program, so that the 
# correct flags are set, etc.
if __name__ == '__main__':
    url = sys.argv[1]
    sloppy = dict()
    try:
        count = int(sys.argv[2])
        lang = sys.argv[3]
        if sys.argv[4] == '--sloppytext':
            sloppy['text'] = True
            sloppy['link'] = False
        elif sys.argv[4] == '--sloppylink':
            sloppy['link'] = True
            sloppy['text'] = False
        elif sys.argv[4] == '--sloppy':
            sloppy['link'] = True
            sloppy['text'] = True
    except IndexError:
        sloppy['link'] = False
        sloppy['text'] = False

    if url == '':
        print('Please enter a valid URL')
    else:
        try:
            run = Crawler()
            run.spider(url, count, lang, sloppy)
        except KeyboardInterrupt:
            print('User interrupt')
