import json
import pathlib
import os

from datetime import datetime

import scrapy

from ..items import MtavaritvItem
from ..utils import URLS

from scrapy.loader import ItemLoader



class MtavariSpider(scrapy.Spider):
    name = "mtavari"
    allowed_domains = ["mtavari.tv"]
    start_urls = URLS
    start_date = datetime(2023, 3, 1)
    end_date = datetime(2023, 10, 10)
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
            os.path.join(os.path.relpath(data_path, pathlib.Path(__file__).parents[2]), 'mtavaritv.json'): {
                'format': 'json',
                'encoding': 'utf8',
                'overwrite': True,
                'indent': 4,
            },
        },
        'LOG_FILE':os.path.join(data_path, f'mtavaritv.log')
    }

    def parse(self, response):
        json_resp = json.loads(response.body)
        items = json_resp['data']

        for item in items:
            loader = ItemLoader(item=MtavaritvItem(), response=response)
            content_url = item.get('links').get('self').get('href')

            loader.add_value('date', item.get('attributes').get('created'))
            loader.add_value('title', item.get('attributes').get('title'))
            loader.add_value('content_url', content_url)

            yield response.follow(url=content_url, callback=self.parse_content, meta={'loader':loader})

        next_page = json_resp.get('links').get('next')
        if next_page is not None and loader.get_output_value('date') >= self.start_date:
            yield response.follow(next_page['href'], callback=self.parse)

    def parse_content(self, response):
        loader = response.meta['loader']
        json_resp = json.loads(response.body)
        html = json_resp.get('data').get('attributes').get('body')
        loader.add_value('content', html)
        date = loader.get_collected_values('date')
        if isinstance(date, list):
            if (date[0] >= self.start_date) and (date[0] <= self.end_date):
                yield loader.load_item()
