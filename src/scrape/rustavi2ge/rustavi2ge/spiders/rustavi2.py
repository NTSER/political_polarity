import pathlib
import os
import sys

import scrapy
from scrapy.loader import ItemLoader
from ..items import Rustavi2GeItem
from ..utils import get_other_day_url, get_next_page_in_day, get_date_url, extract_date

sys.path.append(os.path.join(pathlib.Path(__file__).parents[4]))
from pipelines_configuration.scrape_configuration import ScrapeConfig


class Rustavi2Spider(scrapy.Spider):
    name = "rustavi2"
    allowed_domains = ["rustavi2.ge"]
    config = ScrapeConfig().get_config()
    start_date = config["start_date"]
    end_date = config["end_date"]
    start_urls = [get_date_url(end_date)]

    def parse(self, response):
        yield from response.follow_all(
            xpath="//div[@class='nw_line']//a[not(descendant::img[contains(@src, 'video')])]/@href",
            callback=self.parse_content,
        )

        date = extract_date(response.url)
        if date >= self.start_date:
            if response.xpath(
                "//ul[@class='pag']/li[@class='cur']/following-sibling::li/@onclick"
            ):
                next_url = get_next_page_in_day(
                    response.xpath(
                        "//ul[@class='pag']/li[@class='cur']/following-sibling::li/@onclick"
                    ).get()
                )
            else:
                next_url = get_other_day_url(response.url)
            yield response.follow(next_url, callback=self.parse)

    def parse_content(self, response):
        loader = ItemLoader(item=Rustavi2GeItem(), selector=response)
        loader.add_xpath("date", "//div[@itemprop='datePublished']/@content")
        loader.add_xpath("title", "//div[@itemprop='name']//text()")
        loader.add_value("content_url", response.url)
        loader.add_xpath("content", "//span[@itemprop='articleBody']//text()")
        loader.add_value("source", "rustavi2ge")

        date = loader.get_collected_values("date")
        if isinstance(date, list):
            if (date[0] >= self.start_date) and (date[0] < self.end_date):
                yield loader.load_item()
