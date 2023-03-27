import json
import time
import chromedriver_autoinstaller
import pandas as pd
import logging
# from concurrent.futures import ThreadPoolExecutor
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
import selenium.common
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


class DataGet:
    BASE_URL = "https://www.vrbo.com"
    FORMATTED_URL = "https://www.vrbo.com/search/keywords:{}-{}/page:{}/"

    def __init__(self):
        chromedriver_autoinstaller.install()
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("—-no-sandbox")

        self.driver = webdriver.Chrome(options=options)

    @staticmethod
    def clean_url(url: str):
        """clean url and remove params attached"""
        return url.split("?")[0]

    @staticmethod
    def generate_listing_urls(
            states: list,
            max_pagination: int = 11,
            country: str = None,
    ) -> list:
        """generate url for each paginated page"""
        all_listing_url = []
        for state in states:
            for x in range(1, max_pagination):
                url = DataGet.FORMATTED_URL.format(state, country, x)
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
            with open(file_name, "a", encoding="utf-8") as file:
                file.write(json.dumps(data, ensure_ascii=False) + "\n")

    def load_listing_pages(self, listing_urls: str, wait_time: int = None) -> list:
        """get each room url"""
        self.driver.get(listing_urls)
        time.sleep(wait_time)

        # page content load dynamically, scroll slowly to the bottom for all data to be available
        height = int(self.driver.execute_script("return document.body.scrollHeight"))
        for i in range(1, height, 400):
            self.driver.execute_script("window.scrollTo(0, {})".format(i))
            time.sleep(1)

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        listing_tags = soup.find(name="div", class_="HitCollection")

        listing = [
            self.clean_url(listing.find(name="a").get("href"))
            for listing in listing_tags.find_all(name="div", class_="Hit")
        ]
        return listing

    def generate_room_data(self,
                           states: list,
                           file_name: str,
                           country: str = "united-states-of-america",
                           wait_time: int = 10
                           ) -> None:
        """start the job for extracting data"""

        all_listing = self.generate_listing_urls(states, country=country)

        for listing in all_listing:
            room_urls = self.load_listing_pages(listing, wait_time)
            for room_url in room_urls:
                url = DataGet.BASE_URL + room_url
                self.driver.get(url)
                time.sleep(wait_time)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                if soup.find(name="h1", class_="h2 margin-bottom-0x"):
                    try:
                        data = self.get_room_data(url, wait_time)
                    except AttributeError:
                        time.sleep(3)
                        data = self.get_room_data(url, wait_time)

                    self.save(data, file_name)

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
        attributes = soup.find(name="ul", class_="four-pack list-unstyled")

        for element in attributes.find_all(name="li", class_="four-pack__block")[1:]:
            header = element.find(name="div", class_="four-pack__block-title h3 margin-bottom-0x").text
            # get data that is not about spaces
            if header != "Spaces":
                header_attribute = header.split(" ")
                if len(header_attribute) == 2:
                    if header_attribute[1].startswith("bedroom"):
                        room_data["bedrooms"] = float(header_attribute[0])

                    elif header_attribute[1].startswith("bathroom"):
                        room_data["bathrooms"] = float(header_attribute[0])
                # get inner data
                for body in element.find_all(name="li", class_="four-pack__detail-item"):
                    body_attribute = body.text
                    if body_attribute.startswith("Sleep"):
                        body_attribute_split = body_attribute.split(" ")
                        if len(body_attribute_split) == 2:
                            room_data["sleeps"] = float(body_attribute_split[1])
                    else:
                        body_attribute_split = body.text.split(" ")
                        if len(body_attribute_split) == 2:
                            if body_attribute_split[1].startswith("bed"):
                                room_data["beds"] = float(body_attribute_split[0])

                        elif len(body_attribute_split) > 2:
                            join_bath_text = " ".join(body_attribute_split[1:])
                            if join_bath_text.startswith("full bath"):
                                room_data["full_baths"] = float(body_attribute_split[0])

                            elif join_bath_text.startswith("half bath"):
                                room_data["half_baths"] = float(body_attribute_split[0])
            # get space data
            elif header.startswith("Space"):
                room_data["spaces"] = [body.text for body in
                                       element.find_all(name="li", class_="four-pack__detail-item")]

        return room_data

    def get_amenities_data(self, room_data: dict, wait_time: int = None) -> dict:
        """get amenities data from property listing"""

        # try to click on amenities, if failed try again, if failed again, button does not exist
        try:
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/main/div[1]/div[2]/div/div[2]/div[2]/div[4]/div/div/div/div/button'
            ).click()

        except selenium.common.NoSuchElementException:
            time.sleep(3)

            try:
                self.driver.find_element(
                    By.XPATH,
                    '/html/body/div[1]/div[2]/main/div[1]/div[2]/div/div[2]/div[2]/div[4]/div/div/div/div/button'
                ).click()

            except selenium.common.NoSuchElementException:
                room_data["amenities"] = {}
                return room_data

        time.sleep(wait_time)
        amenities_soup = BeautifulSoup(self.driver.page_source, "html.parser")

        room_data["amenities"] = {}
        amenities = amenities_soup.find(
            name="div", class_="Modal__body"
        ).find_all("div", class_="amenities-categorized-modal__category")
        for element in amenities:
            header = element.find(name="h3", class_="")
            value = element.find_all(name="li", class_="amenities-categorized-modal__amenity-list-item")

            room_data["amenities"][header.text] = [v.find(name="div", class_="").text for v in value]

        return room_data

    def get_room_data(self, room_url: str, wait_time: int = None) -> dict:
        """Get data from property listing and save to file"""
        logging.info(f"extracting data from: {room_url}")
        # self.driver.get(room_url)
        # time.sleep(wait_time)
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        location = soup.find(name="div", class_="Description--location").text.split(",")
        if len(location) == 3:
            city, state, country = location

        elif len(location) == 2:
            state, country = location
            city = ""

        elif len(location) == 4:
            city, state, country = location[1:4]
        else:
            city, state, country = [" ", " ", " "]

        room_data = {
            "url": room_url,
            "title": soup.find(name="h1", class_="h2 margin-bottom-0x").text,
            "review_rating": float(soup.find(name="strong", class_="reviews-summary__rounded-rating").text)
            if soup.find(name="strong", class_="reviews-summary__rounded-rating")
            else "",
            "review_number": int(
                "".join(
                    soup.find(
                        name="strong", class_="reviews-summary__num-reviews-right-rail text-link"
                    ).text
                    .split(" ")[0]
                    .replace("(", "")
                    .split(",")
                )
            )
            if soup.find(name="strong", class_="reviews-summary__num-reviews-right-rail text-link")
            else "",
            "owner": soup.find(name="h4", class_="host-summary__name").text.split("by")[1],
            "listing_type": soup.find(name="div", class_="four-pack__block-title h3 margin-bottom-0x").text,
            "price": float(
                "".join(
                    soup.find(name="span", class_="rental-price__amount")
                        .text.replace("$", "")
                        .strip().split(",")
                )
                if soup.find(name="span", class_="rental-price__amount")
                else 0
            ),

            "premier_host": "Yes"
            if soup.find(name="p", class_="host-summary__title text-muted")
            else "No",
            "year_joined": int(soup.find(name="div", class_="owner-details__member-since").text.split(" ")[-1]),
            "city": city.strip(),
            "state": state.strip(),
            "country": country.strip(),
        }

        room_data = self.get_attributes(soup, room_data)

        room_data = self.get_amenities_data(room_data, wait_time)

        return room_data


if __name__ == "__main__":
    states_to_scrape = ["florida", "arizona", "colorado"]
    file_dir = "./data/raw_data/vrbo-data.json"
    DataGet().generate_room_data(states_to_scrape, file_dir)

