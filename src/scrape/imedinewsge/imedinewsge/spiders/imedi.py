import json
import pathlib
import os

from datetime import datetime

import scrapy

from ..items import ImedinewsgeItem
from ..utils import URL, get_next_url

from scrapy.loader import ItemLoader



class ImediSpider(scrapy.Spider):
    name = "imedi"
    allowed_domains = ["imedinews.ge"]
    start_urls = URL
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
            os.path.join(os.path.relpath(data_path, pathlib.Path(__file__).parents[2]), 'imedinewsge.json'): {
                'format': 'json',
                'encoding': 'utf8',
                'overwrite': True,
                'indent': 4,
            },
        },
        'LOG_FILE':os.path.join(data_path, f'imedinewsge.log')
    }
    def parse(self, response):
        try:
            json_resp = json.loads(response.text)
            next_page_exists = json_resp['LoadMore']
            items = json_resp['List']

            for item in items:
                loader = ItemLoader(item=ImedinewsgeItem())
                loader.add_value('date', item['DateValue'])
                loader.add_value('title', item['Title'])
                loader.add_value('content_url', item['Url'])
                loader.add_value('content', item['Content'])
                date = loader.get_collected_values('date')
                if isinstance(date, list):
                    if (date[0] >= self.start_date) and (date[0] <= self.end_date):
                        yield loader.load_item()

            if next_page_exists and loader.get_output_value('date') >= self.start_date:
                next_url = get_next_url(response.url)
                yield response.follow(next_url, callback=self.parse)

        except json.decoder.JSONDecodeError:
            self.logger.warning(f"Failed to parse JSON from {response.url}")
            next_url = get_next_url(response.url)
            yield response.follow(next_url, callback=self.parse)

