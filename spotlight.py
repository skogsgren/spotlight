"""Spotlight: Crawls a given website for text, analyzes topics for that text.

This program will take a given url and crawl that url given two arguments: the
amount of articles/pages to crawl, and what language that website is in. 
Currently two languages are supported: English and Swedish, specified with 
'en' and 'sv' respectively. Additionally there is a third optional flag for 
the program, '--sloppy', '--sloppytext' or '--sloppylink'. '--sloppy' 
pays no heed to CSS classes, which means that it will crawl the entire URL 
without discrimination. '--sloppytext' will adhere to the CSS 
classes of links, but the classes in the text. '--sloppylink' will 
adhere to the CSS classes of text, but not links.

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

logging.basicConfig(format='%(asctime)s %(message)s')
logging.getLogger().setLevel(logging.INFO)


class Crawler():
    """Handles link crawling and link extraction.

    This class handles, and keeps track of, the visited websites as well as
    giving the appropriate arguments for the extraction class 'Digger'.

    Attributes:
        vis_count: amount of visited websites.
        vis_list: the list of websites to visit.
        vis: the set of visited websites, i.e. already crawled websites.
        vocab_set: the set of unique (lemmatized) words in all the articles.
        article_list: a list where each element is one article. Is used for
                      the numpy array in topic extraction.
    """
    def __init__(self):
        self.vis_count = 0
        self.vis_list = list()
        self.vis = set()
        self.vocab_set = set()
        self.article_list = list()
        # These are checked by manually inspecting the CSS of the nav page
        # (i.e. the page that houses say editorial articles) of URLs in order
        # to determine what URLs we actually want the crawler to
        # parse.
        #
        # For reddit I instead opted for teddit.net, seeing that it's simply
        # a front end that doesn't contain any javascript, which makes it
        # easier to crawl.
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
        url_base = re.match(r'.+\.\w+', url).group(0)
        html_request = requests.get(url)

        try:
            if html_request.status_code == 200:
                html = html_request.text
            else:
                html = '<!-- -->'
                print('404 error, but keepin\' on keepin\' on...')
        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError):
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
        url_base = re.match(r'.+\.\w+', url).group(0)
        url_base = url_base.strip('https://')
        url_base = url_base.strip('www.')
        url_base = re.sub(r'\.(se|com|nu|org|xyz|cyou|net)', '', url_base)
        if url not in self.vis_list:
            self.vis_list.append(url)
            for link in self.vis_list:
                if link not in self.vis and self.vis_count <= count:
                    soups = self.request(link)
                    extracter = Digger()
                    # Only for logging purposes, a simple solution
                    # so that logging lines don't exceed 80 lines
                    rel_count = f"{self.vis_count}/{count} Extracting"

                    logging.info(f"{rel_count} text from {link}")
                    text = extracter.extract_text(soups['peasoup'],
                                                  sloppy['text'])
                    lemma = extracter.lemmatize(text, lang)
                    # Checks the extracted lemmatized words for uniqueness
                    # to the vocabulary, and then adds the article if it 
                    # isn't empty.
                    for word in lemma:
                        if word not in self.vocab_set:
                            self.vocab_set.add(word)
                    if lemma != []:
                        self.article_list.append(' '.join(lemma))

                    logging.info(f"{rel_count} links from {link}")
                    self.get_links(soups['soup'],
                                   soups['chefsoup'],
                                   soups['url_base'],
                                   sloppy['link'])
                    self.vis.add(link)
                    self.vis_count += 1
                else:
                    pass
            try:
                result = extracter.topic_extraction(
                        self.article_list, tuple(self.vocab_set))
                with open(f'{url_base}.txt', 'a') as filename:
                    filename.write(f'\ncrawled {len(self.vis)} pages\
                                    on {url}\
                                    \n{result} \n')
                print(f'\ncrawled {len(self.vis)} pages on {url}\
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
        # Handles links in closed CSS-classes, and handles the --sloppy flag.
        for link in chefsoup:
            final_link = self.format_links(url_base, link)
            try:
                # Ensures that it doesn't crawl outside of the domain.
                if url_base in final_link:
                    for cl in self.url_classes:
                        try:
                            if cl in link.attrs['class']:
                                self.vis_list.append(final_link)
                        except KeyError:
                            if sloppy:
                                self.vis_list.append(final_link)
                            else:
                                pass
                    if sloppy:
                        self.vis_list.append(final_link)
            except UnboundLocalError:
                pass

        # Handles links for embedded_url classes.
        for cl in self.embedded_url_classes:
            embedded = soup.find_all(class_=cl)
            for link in embedded:
                try:
                    final_link = self.format_links(url_base, link.find('a'))
                    # Ensures that it doesn't crawl outside of the domain.
                    if url_base in final_link:
                        self.vis_list.append(final_link)
                    else:
                        pass
                except UnboundLocalError:
                    pass


class Digger:
    """ Responsible for extracting text and topics from raw HTML.

    Includes functions for: extracting text from <p> tags, lemmatization,
    topic extraction.
    """

    def extract_text(self, peasoup, sloppy):
        extracted_text = list()
        # These are checked by manually inspecting the CSS of articles.
        css_classes = [
                'css-1dznooa',  # Aftonbladet
                'dcr-xry7m2',  # The Guardian
                'dcr-1of5t9g'  # The Guardian Editorial Article
                ]

        for paragraph in peasoup:
            if paragraph.get_text() not in extracted_text:
                # Goes through each of the css_classes and appends the text
                # if there is a match, unless the --sloppy flag is used.
                for cl in css_classes:
                    try:
                        if cl in paragraph.attrs['class']:
                            extracted_text.append(paragraph.get_text())
                    # Because some <p> tags lack classes.
                    except KeyError:
                        pass

                if sloppy:
                    extracted_text.append(paragraph.get_text())

        return ' '.join(extracted_text)

    def lemmatize(self, article, lang):
        """Lemmatizes the words of an article using spacy, as well as sorting
        out any words lacking meaningful semantic meaning (by use of a
        frequency list)."""

        # Taken from https://universaldependencies.org/u/pos/,
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
        # proof method was by duplicating them and then changing small things
        # as needed. This can easily be expanded to encompass for more
        # languages as needed. See https://spacy.io/usage/models/#languages
        # Note that spacy's lemmatization requires explicit installation in
        # your shell for these corpora, which can be performed by:
        #
        # python3 -m spacy download en_core_web_sm
        # python3 -m spacy download sv_core_news_sm
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
                    and len(lemma) > 3
                    and lemma not in frequency_list
                    # These below are manually added exceptions
                    # that spacy lemmatized wrong during testing.
                    and '%' not in lemma
                    and '.' not in lemma
                    and '"' not in lemma):
                vocab.append(lemma)
        return vocab

    def topic_extraction(self, articles, uniq_words):
        logging.info("Analyzing text...")
        for article in articles:
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
