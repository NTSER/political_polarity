import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join

from datetime import datetime


def join_and_strip(values):
    joined_values = Join()(values)
    stripped_values = joined_values.strip()
    return stripped_values


def convert_to_date(date_str):
    datetime_object = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
    return datetime_object


class Rustavi2GeItem(scrapy.Item):
    date = scrapy.Field(
        input_processor=MapCompose(convert_to_date), output_processor=TakeFirst()
    )
    title = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=TakeFirst()
    )
    content_url = scrapy.Field(output_processor=TakeFirst())
    content = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=join_and_strip
    )
    source = scrapy.Field(output_processor=TakeFirst())
