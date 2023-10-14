import json
import pathlib
import os
import sys

import scrapy

from ..items import ImedinewsgeItem
from ..utils import URL, get_next_url

from scrapy.loader import ItemLoader

sys.path.append(os.path.join(pathlib.Path(__file__).parents[4]))

from pipelines_configuration.scrape_configuration import ScrapeConfig


class ImediSpider(scrapy.Spider):
    name = "imedi"
    allowed_domains = ["imedinews.ge"]
    start_urls = URL
    config = ScrapeConfig().get_config()
    start_date = config["start_date"]
    end_date = config["end_date"]

    def parse(self, response):
        try:
            json_resp = json.loads(response.text)
            next_page_exists = json_resp["LoadMore"]
            items = json_resp["List"]

            for item in items:
                loader = ItemLoader(item=ImedinewsgeItem())
                loader.add_value("date", item["DateValue"])
                loader.add_value("title", item["Title"])
                loader.add_value("content_url", item["Url"])
                loader.add_value("content", item["Content"])
                loader.add_value("source", "imedinewsge")
                date = loader.get_collected_values("date")
                if isinstance(date, list):
                    if (date[0] >= self.start_date) and (date[0] < self.end_date):
                        yield loader.load_item()

            if next_page_exists and loader.get_output_value("date") >= self.start_date:
                next_url = get_next_url(response.url)
                yield response.follow(next_url, callback=self.parse)

        except json.decoder.JSONDecodeError:
            self.logger.warning(f"Failed to parse JSON from {response.url}")
            yield scrapy.Request(response.url, callback=self.parse, dont_filter=True)
