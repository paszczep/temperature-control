from requests import Session
from bs4 import BeautifulSoup
from dotenv import dotenv_values
from typing import Union
from login import filled_login_params
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Measure:
    device_id: int
    device_name: str
    temperature: str
    measure_time: str
    database_time: str


dotenv_path = Path(__file__).parent.parent / '.env'

env_values = dotenv_values(dotenv_path)
base_url = env_values['MEASURE_URL']
login = env_values['MEASURE_LOGIN']
password = env_values['MEASURE_PASSWORD']


def _login_and_get_first_view(session: Session) -> bytes:
    login_response = session.get(base_url)
    login_content = login_response.content
    login_params = filled_login_params(
        login_page_content=login_content,
        login=login,
        password=password
    )
    login_url = login_response.url
    response_after_login = session.post(login_url, login_params)
    response_content = response_after_login.content
    return response_content


def _measure_table_rows(soup: BeautifulSoup) -> list:
    table = [
        [cell.text.strip() for cell in row.find_all('td')]
        for row in soup.find_all('tr')]
    rows_with_values = [row for row in table if len(row) == 7]
    return rows_with_values


def _measures_from_page(content: BeautifulSoup) -> list[Measure]:
    table_rows = _measure_table_rows(content)
    devices_readings = list()
    time_now = str(datetime.now())
    for table_row in table_rows:
        _, _, name, _, value, device_time, _id = table_row
        devices_readings.append(
            Measure(int(_id), name, value, device_time, time_now))
    return devices_readings


def _get_next_page_href(content_soup: BeautifulSoup) -> Union[str, IndexError]:
    next_page = content_soup.find_all('li', {'class': 'next'})
    if not next_page:
        raise IndexError('No more pages')
    next_page_href = next_page.pop().find_all(href=True).pop()['href']
    return next_page_href


def _recursively_read_table_pages(session: Session, response_content: bytes, all_measures: list) -> list[Measure]:
    content_soup = BeautifulSoup(response_content, 'html.parser')
    page_measures = _measures_from_page(content_soup)
    all_measures += page_measures
    try:
        next_href = _get_next_page_href(content_soup)
    except IndexError:
        pass
    else:
        next_url = f'{base_url}{next_href}'
        response_content = session.get(next_url).content
        _recursively_read_table_pages(session, response_content, all_measures)
    finally:
        return all_measures


def read_all_thermometers() -> list[Measure]:
    session = Session()
    response_content = _login_and_get_first_view(session)
    all_devices = []
    all_devices = _recursively_read_table_pages(session, response_content, all_devices)
    return all_devices
