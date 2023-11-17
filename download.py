import asyncio
import os
import re
import sys
from typing import List
from playwright.async_api import async_playwright
import logging
import requests


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
base_logger = logging.getLogger("lego")

folder_name = "lego-instructions"
instructions_base_url = "https://www.lego.com/de-de/service/buildinginstructions"


class ContextualLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra):
        super(ContextualLoggerAdapter, self).__init__(logger, extra)

    def process(self, msg, kwargs):
        context = " | ".join(f"{key}: {value}" for key, value in self.extra.items())
        return f"[{context}] {msg}", kwargs


def translate_image_url_to_pdf_url(url: str) -> str:
    replacees = [".img", ".png", ".jpg", ".jpeg"]
    for replacee in replacees:
        url = url.replace(replacee, ".pdf")

    return url


async def download_instructions(set_id: int, folder_name: str) -> None:
    logger = ContextualLoggerAdapter(base_logger, {"set_id": set_id})
    instructions_url = f"{instructions_base_url}/{set_id}"
    try:
        logger.debug(f"Ensuring folder '{folder_name}' does exist")
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # Start Playwright
        async with async_playwright() as p:
            # Launch the browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Navigate to the URL
            await page.goto(instructions_url)

            # Search for the text in all elements
            elements = await page.query_selector_all("*")
            search_title = "Bauanleitungen für"
            title = None
            for element in elements:
                text = await element.text_content()
                if text and text.strip().startswith(search_title):
                    title = " - ".join(
                        text.strip()
                        .replace("®", "")
                        .replace("Bauanleitungen", "Bauanleitung")
                        .split(", ")
                    )
                    break

            if title:
                logger.debug(f"Found instruction set title: '{title}'")
            else:
                logger.error(f"Title starting with '{search_title}' not found.")
                await browser.close()
                return

            # Find all divs that potentially contain PDF links
            divs = await page.query_selector_all("div")

            for div in divs:
                style_attr = await div.get_attribute("style")
                title_attr = await div.get_attribute("title")
                if style_attr is None:
                    continue

                img_url_match = re.search(r"url\(['\"](.+)['\"]\)", style_attr)
                if img_url_match is None:
                    continue

                img_url = img_url_match.group(1)
                # valid download urls apparently contain `product.bi`
                if "product.bi" not in img_url:
                    continue

                pdf_url = translate_image_url_to_pdf_url(img_url)
                file_name = f"{title} - {title_attr}.pdf".replace("/", "-").replace(
                    ",", ""
                )
                file_path = os.path.join(folder_name, file_name)

                if os.path.exists(file_path):
                    logger.info(
                        f"Skipping download as file already exists: {file_name}"
                    )
                    continue

                logger.info(f"Attempting to download from '{pdf_url}' to '{file_name}'")
                pdf_response = requests.get(pdf_url)
                if pdf_response.status_code == 200:
                    with open(file_path, "wb") as file:
                        file.write(pdf_response.content)
                    logger.info(f"Downloaded instruction: '{file_name}'")
                else:
                    logger.error(f"Failed to download from: '{pdf_url}'")

            await browser.close()

    except Exception as e:
        logger.error(f"An error occurred: {e}")


async def process_sets(sets: List[int]) -> None:
    for set_id in sets:
        await download_instructions(set_id, folder_name)
        await asyncio.sleep(10)  # don't attempt to DoS the LEGO page 😇


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a comma-separated list of set numbers.")
        sys.exit(1)

    set_ids_raw = sys.argv[1]
    set_ids = [int(set_id) for set_id in set_ids_raw.split(",")]

    asyncio.run(process_sets(set_ids))
