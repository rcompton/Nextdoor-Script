from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

import sys
import time
import csv
import os

from lxml import html
import requests
import json

def get_post_urls(driver):
    # Use Selenium to scroll to the bottom of the news feed and load more posts.
    for _ in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.6)
    # Parse out the post links
    buttons = driver.find_elements_by_xpath('//a[contains(@href, "news_feed/?post=")]')
    urls = []
    for button in buttons:
        try:
            urls.append(button.get_attribute('href'))
        except Exception as e:
            print(e)
    return urls

def parse_post(driver, post_url):
    time.sleep(1.3)
    driver.get(post_url)
    # Click on "view all replies" when necessary to scrape all replies, do it a few times.
    #TODO "see more comments" and "See more to expand posts"
    for _ in range(4):
        more_comments_buttons = driver.find_elements_by_xpath(
            '//button[contains(@class,"see-previous-comments-button-paged")]')
        print("view all replies, more_comments_buttons: ", len(more_comments_buttons))
        if not more_comments_buttons:
            break
        for more_comments_button in more_comments_buttons:
            time.sleep(1.2)
            try:
                if (more_comments_button.is_displayed()):
                    more_comments_button.click()
            except Exception as e:
                print(e)


# Set up driver
#driver = webdriver.Chrome()
driver = webdriver.Chrome(ChromeDriverManager().install())

# Put url in place of <URL of Neighborhood's Newsfeed>
driver.get("https://nextdoor.com/news_feed/?")

# Log In
username = driver.find_element_by_id("id_email")
password = driver.find_element_by_id("id_password")

# Put your username in place of <Username>
username.send_keys(os.getenv("NEXTDOOR_USERNAME"))
# Put your password in place of <Password>
password.send_keys(os.getenv("NEXTDOOR_PASSWORD"))

driver.find_element_by_id("signin_button").click()

post_urls = get_post_urls(driver)
import ipdb;ipdb.set_trace()
print("num posts: ", len(post_urls))
for post_url in post_urls:
    time.sleep(1.2)
    print(post_url)
    parse_post(driver, post_url)

driver.quit()




# Scrape the page source returned from Chrome driver for posts
html_source = driver.page_source
readable_html = html_source.encode('utf-8')
tree = html.fromstring(readable_html)
postNodes = tree.xpath(
    '//div[@id="nf_stories"]/div[@data-class="whole-story"]')

# Iterate over each post node to get data (ie authors, neighborhoods, etc)
# in an organized fashion
posts = [(p.xpath('.//h5[@class="media-author"]//a[@data-class="linked-name"]/*/text()'),
          p.xpath('.//h5[@class="media-author"]//a[@data-type="neighborhood"]/text() | .//h5[@class="media-author"]//a[@class="notranslate"]/text() | .//p[@class="notranslate"]/text()'),
          p.xpath(
              './/h4[@class="media-heading"]//a[@class="notranslate"]/text()'),
          p.xpath('.//a[@href="/events/"]/text() | .//span[@data-class="topics-label"]/span[@class="notranslate"]/text() | .//span[@data-class="topics-label"]/a/text()'),
          p.xpath('.//span[@class="timestamp"]/span/@data-utc'),
          p.xpath('.//p[@data-class="post-content"]/@data-story | .//a[@class="title"]/span[@class="notranslate"]/text() | .//p[@data-class="post-content"]//span[@class="notranslate"]/text() | .//p/text()'),
          p.xpath(
              './/div[@data-class="comment-like-container"]/@data-num-comments'),
          p.xpath('.//h6[@class="media-author"]/span[@class="user-name js-profile-menu-init"]/a/span/text() | .//h6[@class="media-author"]/span[@class="user-name js-profile-menu-init"]/span/text()'),
          p.xpath('.//span[@class="notranslate"]/@data-story')) for p in postNodes if p.xpath('.//h5[@class="media-author"]//a[@data-class="linked-name"]/*/text()') != []]

# Create CSV Writer for first document (Posts)
ofile = open('posts.csv', "wb")
writer = csv.writer(ofile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

# Create CSV Writer for second document (Replies)
rfile = open('replies.csv', "wb")
rWriter = csv.writer(
    rfile,
    delimiter=',',
    quotechar='"',
    quoting=csv.QUOTE_ALL)
counter = 1

# Output to csv files
for p in posts:
    # Posts
    author = p[0][0]
    author = author.encode('utf8')
    location = p[1][0]
    location = location.encode('utf8')

    try:
        title = p[2][0]
        title = title.encode('utf8')
        category = p[3][0]
        category = category.encode('utf8')
    except BaseException:
        pass

    date = p[4][0]
    date = date.encode('utf8')
    content = p[5][0]
    if content != []:
        content = content.encode('utf8')
    else:
        content = "Poll"
    numReplies = p[6][0]
    numReplies = numReplies.encode('utf8')
    writer.writerow([author, location, title, category,
                     date, content, numReplies])

    # Replies
    for c in range(0, len(p[7])):
        try:
            n = p[7][c]
            r = p[8][c]
            rWriter.writerow([counter, n.encode('utf-8'), r.encode('utf-8')])
        except BaseException:
            pass

    counter += 1

