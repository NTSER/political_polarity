from scraper import NewsScraperSpider
import logging
from time import sleep
import random
logging.basicConfig(level=logging.INFO)
spider = NewsScraperSpider()

next_url = 'https://tvpirveli.ge/ka/siaxleebi/politika?p=1'

while True:
    logging.log(logging.INFO, next_url)
    for loader, next_url in spider.parse(next_url):
        sleep(random.uniform(0.1, 0.6))
        loader = spider.parse_content(loader)
        sleep(random.uniform(0.1, 0.6))
        spider.load_and_save(loader)
    if next_url is None:
        break      