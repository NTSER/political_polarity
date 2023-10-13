import sys
import pathlib
import yaml
import os
import scrapy
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from scrape.formulanewsge.formulanewsge.spiders import formula
from scrape.imedinewsge.imedinewsge.spiders import imedi



with open(
    os.path.join(os.path.dirname(__file__), 'pipelines_configuration/scrape_config.yaml'),
      'r',
      ) as yaml_file:
    config_data = yaml.safe_load(yaml_file)

start_date = datetime.strptime(config_data['start_date'], "%d-%m-%Y")
end_date = datetime.strptime(config_data['end_date'], "%d-%m-%Y")

custom_settings = {
        'FEEDS': {
            'sdsm.json': {
                'format': 'json',
                'encoding': 'utf8',
                'overwrite': True,
                'indent': 4,
            },
        },
        # 'LOG_FILE':os.path.join(data_path, f'imedinewsge.log')
    }


process = CrawlerProcess(Settings(custom_settings))
process.crawl(
    formula.FormulaSpider,
    start_date=start_date,
    end_date=end_date
    )

process.start()