import csv
import json
import logging
import os
import re
import requests
import sys
import time

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from lxml import html
from bs4 import BeautifulSoup

FORMAT = '%(asctime)-15s %(levelname)-6s %(message)s'
DATE_FORMAT = '%b %d %H:%M:%S'
formatter = logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
fhandler = logging.FileHandler(os.path.join(os.environ['HOME'],'craigslist-data/log.log'))
fhandler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.addHandler(fhandler)
logger.setLevel(logging.INFO)

def get_post_urls(driver, num_scrolls=5):
    # Use Selenium to scroll to the bottom of the news feed and load more posts.
    for i in range(num_scrolls):
        logger.info("scroll for more posts {}".format(i))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.6)
    # Parse out the post links
    buttons = driver.find_elements_by_xpath('//a[contains(@href, "news_feed/?post=")]')
    urls = []
    for button in buttons:
        try:
            urls.append(button.get_attribute('href'))
        except Exception as e:
            logger.info(e)
    return set(urls)

def parse_comment(comment_soup):
    #TODO: selnium to get reactions
    dic = {}
    dic['comment_id'] = comment_soup.find('div',class_='js-media-comment').attrs.get('id')
    dic['human_timestamp'] = comment_soup.find('div',class_='js-media-comment').find('span',class_='css-1yr85gk').text
    dic['author_name'] = comment_soup.find('div',class_='js-media-comment').find('a',class_='comment-detail-author-name').text
    dic['profile_id'] = comment_soup.find('div',class_='js-media-comment').find('a',class_='comment-detail-author-name').attrs.get('href')
    dic['hood'] = comment_soup.find('div',class_='js-media-comment').find('button',class_=re.compile('comment-byline-cursor.*')).text
    dic['text'] = comment_soup.find('div',class_='js-media-comment').find('span',class_='Linkify').text
    dic['reaction_count'] = comment_soup.find('div',class_='js-media-comment').find('div',class_='comment-thank-container-reaction-count').text #find_all('div',class_='_23VbTEF3 _3udyPGMs')
    # Iterate over comments within the comment - these are replies.
    replies = comment_soup.find_all('div', class_='css-1r3teth')
    reply_comment_ids = []
    for reply in replies:
        try:
            reply_id = reply.find('div',class_='js-media-comment').attrs.get('id')
            if reply_id:
                reply_comment_ids.append(reply_id)
                logger.info("success reply: {}".format(reply_id))
        except:
            logger.info("empty reply: {}".format(reply))
    if reply_comment_ids:
        dic['reply_comment_ids'] = reply_comment_ids
    else:
        dic['reply_comment_ids'] = None
    return dic


def parse_threads(html_soup):
    dics = []
    comments = html_soup.find_all('div', class_='css-1r3teth')
    logger.info("num comments: {}".format(len(comments)))
    for comment in comments:
        try:
            dic = parse_comment(comment)
            dics.append(dic)
        except Exception as e:
            logger.info("comment parse fail: {}".format(comment.prettify()))
            logger.info(e)
    return dics


def parse_post(driver, post_url):
    driver.get(post_url)
    # TODO parse post
    post_dic = {}

    # parse comments
    # First expand the text on the page - click on "view all replies" when necessary to scrape all replies, repeat a few times.
    for _ in range(5):
        more_comments_buttons = driver.find_elements_by_xpath(
            '//button[contains(@class,"see-previous-comments-button-paged")]')
        logger.info("view all replies, more_comments_buttons: {}".format(len(more_comments_buttons)))
        if not more_comments_buttons:
            logger.info("no more comments")
            break
        for more_comments_button in more_comments_buttons:
            time.sleep(2.2)
            try:
                if (more_comments_button.is_displayed()):
                    more_comments_button.click()
            except Exception as e:
                logger.info(e)

    html_soup = BeautifulSoup(driver.page_source, features='html.parser')
    comment_dics = parse_threads(html_soup)
    return post_dic, comment_dics


def main():
    # Set up driver
    driver = webdriver.Chrome(ChromeDriverManager().install())

    # Put url in place of <URL of Neighborhood's Newsfeed>
    driver.get("https://nextdoor.com/news_feed/?")

    # Log In
    username = driver.find_element_by_id("id_email")
    password = driver.find_element_by_id("id_password")
    username.send_keys(os.getenv("NEXTDOOR_USERNAME"))
    password.send_keys(os.getenv("NEXTDOOR_PASSWORD"))

    retry_login = False
    try:
        driver.find_element_by_id("signin_button").click()
    except Exception as e:
        logger.warning(e)
        retry_login = True

    if retry_login:
        import ipdb;ipdb.set_trace()
        driver.find_element_by_class_name("sign-in-sendlink-button button-primary")

    post_urls = get_post_urls(driver)
    for post_url in post_urls:
        time.sleep(2.2)
        logger.info(post_url)
        post_dic, comment_dics = parse_post(driver, post_url)
        import pandas as pd
        df = pd.DataFrame(comment_dics)
        import ipdb;ipdb.set_trace()

if __name__=='__main__':
    main()


## Scrape the page source returned from Chrome driver for posts
#html_source = driver.page_source
#readable_html = html_source.encode('utf-8')
#tree = html.fromstring(readable_html)
#postNodes = tree.xpath(
#    '//div[@id="nf_stories"]/div[@data-class="whole-story"]')
#
## Iterate over each post node to get data (ie authors, neighborhoods, etc)
## in an organized fashion
#posts = [(p.xpath('.//h5[@class="media-author"]//a[@data-class="linked-name"]/*/text()'),
#          p.xpath('.//h5[@class="media-author"]//a[@data-type="neighborhood"]/text() | .//h5[@class="media-author"]//a[@class="notranslate"]/text() | .//p[@class="notranslate"]/text()'),
#          p.xpath(
#              './/h4[@class="media-heading"]//a[@class="notranslate"]/text()'),
#          p.xpath('.//a[@href="/events/"]/text() | .//span[@data-class="topics-label"]/span[@class="notranslate"]/text() | .//span[@data-class="topics-label"]/a/text()'),
#          p.xpath('.//span[@class="timestamp"]/span/@data-utc'),
#          p.xpath('.//p[@data-class="post-content"]/@data-story | .//a[@class="title"]/span[@class="notranslate"]/text() | .//p[@data-class="post-content"]//span[@class="notranslate"]/text() | .//p/text()'),
#          p.xpath(
#              './/div[@data-class="comment-like-container"]/@data-num-comments'),
#          p.xpath('.//h6[@class="media-author"]/span[@class="user-name js-profile-menu-init"]/a/span/text() | .//h6[@class="media-author"]/span[@class="user-name js-profile-menu-init"]/span/text()'),
#          p.xpath('.//span[@class="notranslate"]/@data-story')) for p in postNodes if p.xpath('.//h5[@class="media-author"]//a[@data-class="linked-name"]/*/text()') != []]



