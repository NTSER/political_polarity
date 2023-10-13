import json
import pathlib
import os

from datetime import datetime

import scrapy
from scrapy.loader import ItemLoader

from ..items import Tv1GeItem
from ..utils import URLS, get_next_url

class Tv1Spider(scrapy.Spider):
    name = "tv1"
    allowed_domains = ["1tv.ge"]
    start_date = datetime(2023, 3, 1)
    end_date = datetime(2023, 10, 10)
    date = end_date
    filename = f'{start_date.date()}_{end_date.date()}'
    data_path = os.path.join(
        pathlib.Path(__file__).parents[5],
        'data',
        'scrape_data',
        f'{filename}'
    )
    os.makedirs(data_path, exist_ok=True)
    
    custom_settings = {
        'FEEDS': {
            os.path.join(os.path.relpath(data_path, pathlib.Path(__file__).parents[2]), 'tv1ge.json'): {
                'format': 'json',
                'encoding': 'utf8',
                'overwrite': True,
                'indent': 4,
            },
        },
        'LOG_FILE':os.path.join(data_path, f'tv1ge.log')
    }
    def start_requests(self):
        for url in URLS:
            yield scrapy.Request(url, method='POST', callback=self.parse)

    def parse(self, response):
        json_resp = json.loads(response.body)
        items = json_resp.get('data')
        page_exists = (items != "no ids")
        if page_exists and self.date >= self.start_date:
            links = [item.get('post_permalink') for item in items]
            yield from response.follow_all(links, callback=self.parse_content)

            next_url = get_next_url(response.url)
            yield response.follow(next_url, callback=self.parse, method="POST")

    def parse_content(self, response):
        loader = ItemLoader(Tv1GeItem(), selector=response)
        loader.add_xpath('date', "//div[@class='article-date']/text()")
        loader.add_xpath('title', "//div[contains(@class, 'article-title')]/text()")
        loader.add_value('content_url', response.url)
        loader.add_xpath('content', "//div[contains(@class, 'article-intro')]//p//text()")
        date = loader.get_collected_values('date')
        if isinstance(date, list):
            self.date = date[0]
            if (date[0] >= self.start_date) and (date[0] <= self.end_date):
                yield loader.load_item()
