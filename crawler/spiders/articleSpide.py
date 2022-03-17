import scrapy
import re
from datetime import datetime
import psycopg2
import psycopg2.extras
from PostgreSQL.database import database

# month dictionary
months_dict = ['January',
               'February',
               'March',
               'April',
               'May',
               'June',
               'July',
               'August',
               'September',
               'October',
               'November',
               'December']

class articleSpide(scrapy.Spider):
    '''
        Scrapy web crawler that extracts article title/content, author, and publisher from one article URL
    '''
    name = "articles"



    def __init__(self, **kw):
        super(articleSpide, self).__init__(**kw)
        self.id = kw.get('id')  # id used for this data in PostgreSQL
        self.url = kw.get('url')  # one URL from user input
        self.database = database()
        self.profile = kw.get('profile') # profile of crawler for this website


    def start_requests(self):
        '''
        Scrapy built-in method to start crawling by calling parse
        '''

        yield scrapy.Request(url=self.url, callback=self.parse)

    def parse(self, response):
        '''
        Scrapy built-in method for scraping pages
        Please do not use this parse function. Scrapy will use it automatically
        :param response: a HTML response from URL
        :returns Article title, article content, author name, author page and publisher name
                will be saved in article Table (PostgreSQL) with id
                if the given url does not have website profile, None will be stored in table
        '''

        '''
        Extract article title, article content, author name, author page and publisher name from one URL
        '''

        # article title and content
        article_title = response.css(self.profile["article_title"]+"::text").get().strip()  # tested
        raw_article_content = response.css(self.profile["article_content"]).extract()
        clean_paragraphs = self.get_clean_article_contents(raw_article_content)
        article_content = "'\n\n".join(clean_paragraphs)

        # publisher information
        publisher_name = self.profile["name"] # tested

        # author information
        author_name = response.css(self.profile["author_name"]+"::text").get() # tested

        # get article published time
        published_time_raw = response.css(self.profile["published_time"]).get()

        # use regex to extract the published date
        published_time = re.search(self.profile["published_time_regex"], published_time_raw).groups()[0]

        # convert the date format to "20XX-XX-XX" if not
        if re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", published_time) is None:
            # check the pattern eg. "November 27th 2020"
            pattern1 = re.search("([A-Z][a-z]+) ([0-9]+).*?([0-9]{4})", published_time)
            if pattern1 is not None:
                month = self.match_month_index(pattern1.groups()[0])+1
                day = pattern1.groups()[1]
                year = pattern1.groups()[2]
                # convert "November 27th 2020" to "20XX-XX-XX"
                published_time = datetime.strptime("{}-{}-{}".format(year, month, day), "%Y-%m-%d").strftime("%Y-%m-%d")

        # store information in PostgreSQL articles Table
        self.database.insert_article(self.id, article_title, article_content,
                                     publisher_name, author_name, published_time, self.url)



        ## TODO: CITIATION MODE: OFF
        # if citations is required to check, store citation information
        # citations = self.get_citations(raw_article_content)
        # self.database.insert_citation(self.id, clean_paragraphs, citations)


    def match_month_index(self, month_string):
        '''
        helper function to get the published month by mathcing months_dict
        '''

        for i in range(len(months_dict)):
            if month_string in months_dict[i]:
                return i



    def get_clean_article_contents(self, article_content_html):
        '''
        extract all article content from HTML response
        :param article_content_html: HTML response of article contents
        :return: pure article content without any html tags
        '''
        article_paragraphs = list()

        for paragraph in article_content_html:
            # create line for <br>
            clean_paraggraph = re.sub(r'<br.*?>', '\n', paragraph).strip()

            # remove html tags
            clean_paraggraph = re.sub(r'<.*?>', '', clean_paraggraph).strip()
            # remove &nbsp
            clean_paraggraph = clean_paraggraph.replace(u'\xa0', u' ')

            if clean_paraggraph != "":
                article_paragraphs.append(clean_paraggraph)


        return article_paragraphs


    def get_citations(self, paragraphs):
        '''
        extract all citations in article content
        :param paragraphs, a list of paragraph string from article content
            eg. ["None", "www.google.com", "None", ...]
            each one corresponds to each paragraph
        :return:
        '''

        # create tags for regex and get the cited words
        citation_tag = re.compile(r'<a.*?href=\"(.*?)\".*?>.*?</a>')

        # create citations list to store all citations link for each paragraph
        citations = list()


        for paragraph in paragraphs:
            potential_citations = re.findall(citation_tag, paragraph)
            # no citations in this paragraph
            if len(potential_citations) == 0:
                citations.append("None")
            else:
                # use the first citation for the whole paragraph for convenience
                # TODO: advance multiple citations in one paragraph
                citations.append(potential_citations[0])

        return citations