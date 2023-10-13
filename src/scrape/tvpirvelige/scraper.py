import csv
import pathlib
import os
import re
from datetime import datetime
from urllib.parse import urljoin
import logging

import cloudscraper
from bs4 import BeautifulSoup



class NewsScraperSpider:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.start_date = datetime(2023, 3, 1)
        self.end_date = datetime(2023, 10, 10)
        self.data_path = os.path.join(
        pathlib.Path(__file__).parents[3],
        'data',
        'scrape_data',
       f'{self.start_date.date()}_{self.end_date.date()}'
    )
        os.makedirs(self.data_path)
        
    def get_next_url(self, url):
        current_page = int(re.search(r'\d+$', url).group(0))
        next_page = str(current_page + 1)
        next_url = re.sub(r'\d+$', next_page, url)
        return next_url

    def parse(self, url):
        response = self.scraper.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='col-md-6')[:24]
        for item in items:
            loader = {}
            date_string = item.find('div', class_='tvpcard__date').find('span').text.strip()
            loader['date'] = datetime.strptime(date_string, "%d.%m.%y %H:%M")
            loader['title'] = item.find('h3', class_='tvpcard__title').text.strip()
            loader['content_url'] = urljoin(url, item.find('div').find('a')['href'])
            next_url = self.get_next_url(url)
            if loader['date'] < self.start_date:
                next_url = None
            yield (loader, next_url)

    def parse_content(self, loader):
        response = self.scraper.get(loader['content_url'])
        soup = BeautifulSoup(response.text, 'html.parser')
        content_element = soup.find_all('div', class_='page__usercontent')
        if isinstance(content_element, list) and len(content_element) >= 2:
            loader['content'] = content_element[1].get_text().strip()
        else:
            loader['content'] = None
        
        return loader
            

    def load_and_save(self, loader):
        if (loader['date'] >= self.start_date) and (loader['date'] <= self.end_date):
            new_row = list(loader.values())
            with open(os.join(self.data_path, 'tvpirveli.csv'), "a", encoding="utf-8", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(new_row)
                logging.log(logging.INFO, 'Saved. current date: {}'.format(loader['date']))

