import json
import time
import chromedriver_autoinstaller
import pandas as pd
import logging
# from concurrent.futures import ThreadPoolExecutor
import selenium.common.exceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from iteration_utilities import unique_everseen
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


class DataGet:
    BASE_URL = "https://www.airbnb.com"
    FORMATTED_URL = "https://www.airbnb.com/s/{}-{}/homes?items_offset={}"

    def __init__(self):
        chromedriver_autoinstaller.install()
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("—-no-sandbox")

        self.driver = webdriver.Chrome(options=options)

    @staticmethod
    def clean_url(url: str) -> str:
        """clean url and remove params attached"""
        return url.split("?")[0]

    @staticmethod
    def generate_listing_urls(
            states: list,
            max_pagination: int = 15,
            item_per_page: int = 18,
            country: str = None,
    ) -> list:
        """generate url for each paginated page"""
        all_listing_url = []
        for state in states:
            all_listing_url.append(
                DataGet.FORMATTED_URL.split("?")[0].format(state, country)
            )
            for x in range(1, max_pagination):
                url = DataGet.FORMATTED_URL.format(state, country, x * item_per_page)
                all_listing_url.append(url)

        return all_listing_url

    @staticmethod
    def save(data: dict, file_name: str) -> None:
        """save data to json file"""

        try:
            with open(file_name, "r") as file:
                file_data = [json.loads(line) for line in file]

            # remove duplicates using url as unique identifier
            file_data.append(data)
            json_unique = pd.DataFrame(file_data).astype("str").drop_duplicates(subset=["url"]).to_dict('records')

            with open(file_name, "w", encoding="utf-8") as file:
                for new_data in json_unique:
                    file.write(json.dumps(new_data, ensure_ascii=False) + "\n")

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(json.dumps(data, ensure_ascii=False) + "\n")

    def load_listing_pages(self, listing_urls: str, wait_time: int = None) -> list:
        """get each room url"""
        self.driver.get(listing_urls)
        time.sleep(wait_time)
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        listing_tags = soup.find_all(name="div", class_="cy5jw6o dir dir-ltr")
        listing = [
            self.clean_url(listing.find(name="a").get("href"))
            for listing in listing_tags
        ]
        return listing

    def generate_room_data(self,
                           states: list,
                           file_name: str,
                           country: str = "united-states",
                           wait_time: int = 10,
                           ) -> None:
        """start the job for extracting data"""

        all_listing = self.generate_listing_urls(states=states, country=country)

        for listing in all_listing:
            room_urls = self.load_listing_pages(listing, wait_time)
            for room_url in room_urls:
                url = DataGet.BASE_URL + room_url
                try:
                    data = self.get_room_data(url, wait_time)

                except AttributeError:
                    time.sleep(3)
                    data = self.get_room_data(url, wait_time)

                self.save(data, file_name)

        self.driver.quit()

        # room_urls = []
        # for listing in all_listing:
        #     room_urls.extend(self.load_listing_pages(listing))
        #
        # for room_url in room_urls:
        #     url = DataGet.BASE_URL + room_url
        #     self.get_room_data(url)

        # with ThreadPoolExecutor(max_workers=2) as executor: #10
        #     executor.map(self.load_listing_pages, all_listing)

    @staticmethod
    def get_attributes(soup: BeautifulSoup, room_data: dict) -> dict:
        """get attributes for property listing"""
        attributes = soup.find(name="ol", class_="lgx66tx dir dir-ltr")
        for element in attributes.find_all(name="span", class_=""):
            attribute = element.text.split(" ")

            if len(attribute) == 2:
                if attribute[1].startswith("bedroom"):
                    room_data["bedrooms"] = float(attribute[0])

                elif attribute[1].startswith("bed"):
                    room_data["beds"] = float(attribute[0])

                elif attribute[1].startswith("bath"):
                    room_data["baths"] = float(attribute[0])

                elif attribute[1].startswith("guest"):
                    room_data["guests"] = attribute[0]
        return room_data

    def get_amenities_data(self, room_data: dict, wait_time: int = None) -> dict:
        """get amenities data from property listing"""
        self.driver.execute_script("window.scrollTo(0, 80)")

        # click amenities button
        try:
            wait = WebDriverWait(self.driver, wait_time)
            wait.until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[5]/div/div/div[1]/div/div[2]/div/div/div/div[1]/main/div/div[1]/div[3]/div/div[1]/div/div[6]/div/div[2]/section/div[4]/button")))
            self.driver.find_element(
                By.XPATH, "/html/body/div[5]/div/div/div[1]/div/div[2]/div/div/div/div[1]/main/div/div[1]/div[3]/div/div[1]/div/div[6]/div/div[2]/section/div[4]/button"
            ).click()
        except (selenium.common.exceptions.ElementNotInteractableException,
                selenium.common.exceptions.TimeoutException):

            self.driver.execute_script("document.querySelector('.b9672i7 button').click()")

        time.sleep(wait_time)
        amenities_soup = BeautifulSoup(self.driver.page_source, "html.parser")

        room_data["amenities"] = {}
        amenities = amenities_soup.find(
            name="div", class_="_17itzz4"
        ).find_all("div", class_="_11jhslp")
        for element in amenities:
            header = element.find(name="h3", class_="hghzvl1 dir dir-ltr")
            value = element.find_all(name="div", class_="t1dx2edb dir dir-ltr")

            if header.text == "Not included":
                room_data["amenities"][header.text] = [
                    v.text.split(" ")[1]
                    for v in element.find_all(
                        name="span", class_="a8jt5op dir dir-ltr"
                    )
                ]

            else:
                room_data["amenities"][header.text] = [v.text for v in value]

        return room_data

    def get_room_data(self, room_url: str, wait_time: int = None) -> dict:
        """Get data from property listing"""
        logging.info(f"extracting data from: {room_url}")

        self.driver.get(room_url)
        time.sleep(wait_time)
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        location = soup.find(name="span", class_="_9xiloll").text.split(",")
        if len(location) == 3:
            city, state, country = location
        else:
            city, abv, state, country = location

        label = soup.find(name="h2", class_="hghzvl1 dir dir-ltr").text

        date_joined = soup.find(
            name="div", class_="tehcqxo dir dir-ltr"
        ).find(
            name="li", class_="l7n4lsf dir dir-ltr"
        ).text.split(" ")

        # dictionary to store data
        room_data = {
            "url": room_url,
            "title": soup.find(name="h1", class_="hghzvl1 i1wofiac dir dir-ltr").text,
            "review_rating": float(
                soup.find(name="span", class_="_12si43g").text.split(" ")[0]
                if soup.find(name="span", class_="_12si43g")
                else 0
            ),
            "review_number": int(
                "".join(soup.find(name="span", class_="_1jlwy4xq").text.split(" ")[0].split(","))
                if soup.find(name="span", class_="_1jlwy4xq")
                else 0
            ),
            "owner": label.split("by")[1].strip(),
            "listing_type": label.split("hosted")[0].strip(),
            "price": float(
                "".join(
                    soup.find(name="span", class_="_tyxjp1")
                        .text.replace("$", "")
                        .strip().split(",")
                )
                if soup.find(name="span", class_="_tyxjp1")
                else 0
            ),
            "is_superhost": "Yes"
            if soup.find(name="span", class_="_1mhorg9")
            else "No",
            "month_joined": date_joined[2],
            "year_joined": int(date_joined[3]),
            "city": city,
            "state": state,
            "country": country,
        }

        room_data = self.get_attributes(soup, room_data)
        room_data = self.get_amenities_data(room_data, wait_time)

        return room_data


if __name__ == "__main__":
    states_to_scrape = ["florida", "arizona", "colorado"]
    file_dir = "./data/raw_data/airbnb-data.json"
    DataGet().generate_room_data(states_to_scrape, file_dir)

