import pathlib
import os

from datetime import datetime

import scrapy

from ..utils import URLS, get_next_url, content_from_quote
from ..items import FormulanewsgeItem

from scrapy.loader import ItemLoader


class FormulaSpider(scrapy.Spider):

    name = "formula"
    allowed_domains = ["formulanews.ge"]
    start_urls = URLS
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
            os.path.join(os.path.relpath(data_path, pathlib.Path(__file__).parents[2]), 'formulanewsge.json'): {
                'format': 'json',
                'encoding': 'utf8',
                'overwrite': True,
                'indent': 4,
            },
        },
        'LOG_FILE':os.path.join(data_path, f'formulanewsge.log')
    }

    def parse(self, response):
        items = response.xpath("//div[@class='col-lg-3 news__box__card']")
        for item in items:
            url = item.xpath(".//div[contains(@class,'date')]/following-sibling::a/@href").get()
            is_quote = item.xpath("./div[@class='main__phrases__box']")

            if is_quote:
                yield response.follow(url=url, callback=self.parse_quote)
            else:
                yield response.follow(url=url, callback=self.parse_content)

        next_page_exist = response.xpath("//body/*")
        if next_page_exist and self.date >= self.start_date:
            next_url = get_next_url(response.url)
            yield response.follow(next_url, callback=self.parse)

    def parse_content(self, response):
        loader = ItemLoader(item=FormulanewsgeItem(), selector=response, response=response)
        loader.add_xpath('date', "//*[@class='news__inner__images_created']")
        loader.add_xpath('title', "//*[@class='news__inner__desc__title']/text()")
        loader.add_value('content_url', response.url)
        loader.add_xpath('content', "//section[@class='article-content']//text()")
        date = loader.get_collected_values('date')
        if isinstance(date, list):
            self.date = date[0]
            if (date[0] >= self.start_date) and (date[0] <= self.end_date):
                yield loader.load_item()

    def parse_quote(self, response):

        loader = ItemLoader(item=FormulanewsgeItem(), selector=response, response=response)
        loader.add_xpath('date', "//div[@class='phrase-date']")
        loader.add_xpath('title', "//div[@class='phrase-title']/text()")
        loader.add_value('content_url', response.url)
        quote = response.xpath("//div[@id='phrase-main']//text()").getall()
        quote_description = response.xpath("//div[@class='phrase-text'][2]//text()").getall()

        content = content_from_quote(quote, quote_description)
        loader.add_value('content', content)
        date = loader.get_collected_values('date')
        if isinstance(date, list):
            self.date = date[0]
            if (date[0] >= self.start_date) and (date[0] <= self.end_date):
                yield loader.load_item()
