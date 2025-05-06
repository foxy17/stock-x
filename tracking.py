import requests
from bs4 import BeautifulSoup
import datetime
import logging
import hashlib
# Removed Playwright imports
# from playwright.sync_api import sync_playwright, Error as PlaywrightError
# from playwright_stealth import stealth_sync
import json
import os
import random # Keep for now, might not be needed with SB UC
import time # Keep for potential waits if needed

# Import SeleniumBase
from seleniumbase import SB
# Removed selenium-wire/uc imports
# import seleniumwire.undetected_chromedriver as uc
# from selenium.webdriver.chrome.options import Options
# Removed Selenium exceptions, SB might handle differently or raise its own
# from selenium.common.exceptions import WebDriverException, TimeoutException

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for persistent storage
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Get the directory of the current script
STORAGE_FILE = os.path.join(SCRIPT_DIR, 'seen_items_store.json') # Path relative to the script
MAX_STORED_IDENTIFIERS = 500

# --- Persistence Functions ---

def load_seen_items(filename=STORAGE_FILE):
    """Loads seen item dictionaries from a JSON file."""
    abs_filename = os.path.abspath(filename)
    logging.info(f"Attempting to load seen items from: {abs_filename}")
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                item_objects_list = json.load(f)
                if not isinstance(item_objects_list, list):
                    logging.error(f"Invalid format in {abs_filename}. Expected a list. Starting fresh.")
                    return [], set()
                
                # Derive the set of identifiers from the loaded objects
                identifiers_set = set(item.get('identifier') for item in item_objects_list if item.get('identifier'))
                logging.info(f"Loaded {len(item_objects_list)} items ({len(identifiers_set)} unique identifiers) from {abs_filename}")
                return item_objects_list, identifiers_set
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading seen items from {abs_filename}: {e}. Starting fresh.")
            return [], set()
    else:
        logging.info(f"Storage file {abs_filename} not found. Starting fresh.")
        return [], set()

def save_seen_items(item_objects_list, filename=STORAGE_FILE, max_items=MAX_STORED_IDENTIFIERS):
    """Saves seen item dictionaries to a JSON file, keeping only the most recent ones."""
    abs_filename = os.path.abspath(filename)
    try:
        # Keep only the latest max_items objects
        if len(item_objects_list) > max_items:
            trimmed_list = item_objects_list[-max_items:]
            logging.info(f"Trimming seen items storage from {len(item_objects_list)} to {len(trimmed_list)}.")
        else:
            trimmed_list = item_objects_list

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(trimmed_list, f, ensure_ascii=False, indent=4)
        # logging.info(f"Saved {len(trimmed_list)} items to {abs_filename}") # Can be noisy
    except IOError as e:
        logging.error(f"Error saving seen items to {abs_filename}: {e}")

# --- End Persistence Functions ---

# Load seen items on module initialization
seen_item_objects_list, seen_item_identifiers_set = load_seen_items()

# Define User Agents - Keep for now, SB UC might handle this or we might re-add if needed
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36", # Updated to a more recent common one
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def get_initial_items():
    """Returns the list of item objects loaded at startup."""
    # Return a copy to prevent external modification of the original list
    return list(seen_item_objects_list)

def fetch_content(url):
    """Fetches XML content using SeleniumBase with UC Mode."""
    xml_content = None
    logging.info(f"Initializing SeleniumBase SB with UC Mode for URL: {url}")

    try:
        # Using SB context manager with UC Mode enabled
        # headless=True runs browser in the background
        # Randomly select a user agent for this run
        selected_agent = random.choice(USER_AGENTS)
        logging.info(f"Using User-Agent: {selected_agent}")

        with SB(uc=True, headless=True, test=True, locale_code="en", agent=selected_agent) as sb:
            logging.info(f"Navigating to: {url}")
            sb.open(url)

            # Get source immediately. SeleniumBase UC mode aims to handle challenges transparently.
            # More complex challenge handling might be needed if this fails.
            xml_content = sb.get_page_source()

            # Optional: Basic check AFTER getting source if it looks like a challenge page still
            # This is less reliable than proactive checks during navigation if SB provides them
            if xml_content and ("challenge-page" in sb.get_current_url() or "Just a moment..." in xml_content):
                 logging.warning(f"Page source might still contain challenge elements for {url}. Check content validity.")
                 # Depending on requirements, you might want to return None or raise an error here
                 # return None

            if xml_content:
                logging.info(f"Successfully fetched page source for {url}.")
                # Log preview (optional, can be verbose)
                # logging.info(f"Page source preview (first 500 chars):\n{xml_content[:500]}...")
            else:
                logging.warning(f"Fetched page source for {url} is empty.")

    except Exception as e:
        # Catch broader exceptions as SB might raise different types
        logging.error(f"An error occurred during SeleniumBase operation for {url}: {e}", exc_info=True) # Log traceback
    # SB context manager handles driver closing automatically

    return xml_content

def get_new_items(url):
    """Fetches XML, parses it, and returns a list of new items (dictionaries) based on NSE structure, using persistent memory."""
    xml_content = fetch_content(url)
    if not xml_content:
        logging.warning(f"fetch_content returned no data for {url}. Skipping parsing.")
        return []

    new_items_found = []
    try:
        # Use 'lxml-xml' for potentially stricter XML parsing
        soup = BeautifulSoup(xml_content, 'lxml-xml') 

        items = soup.find_all('item')
        if not items:
            # Fallback: Try html.parser if lxml-xml fails and content might be malformed HTML/XML
            logging.warning("No <item> tags found using 'lxml-xml'. Trying 'html.parser'.")
            soup = BeautifulSoup(xml_content, 'html.parser')
            items = soup.find_all('item')
            if not items:
                 logging.warning("No <item> tags found using 'html.parser' either.")


        logging.info(f"Found {len(items)} <item> tags in the fetched content.")

        for item in items:
            title_tag = item.find('title')
            description_tag = item.find('description')
            link_tag = item.find('link')
            pub_date_tag = item.find('pubDate')

            title = title_tag.text.strip() if title_tag else "No Title"
            description = description_tag.text.strip() if description_tag else "No Description"
            # Link tag might contain the URL directly or within CDATA
            link_text = link_tag.text.strip() if link_tag else None 
            pub_date = pub_date_tag.text.strip() if pub_date_tag else ""

            identifier = None
            if link_text:
                identifier = link_text
            else:
                logging.warning(f"Link tag missing or empty for item '{title[:30]}...'. Using content hash as identifier.")
                content_to_hash = (title + description).encode('utf-8')
                identifier = hashlib.sha256(content_to_hash).hexdigest()

            if identifier and identifier not in seen_item_identifiers_set:
                item_object = {
                    "timestamp": pub_date,
                    "title": title,
                    "description": description,
                    "link": link_text,
                    "identifier": identifier
                }
                
                seen_item_objects_list.append(item_object)
                seen_item_identifiers_set.add(identifier)
                
                new_items_found.append(item_object)
                logging.info(f"New item found: {title[:50]}... (Published: {pub_date})")
                
                save_seen_items(seen_item_objects_list)

    except Exception as e:
        logging.error(f"Error parsing content from {url}: {e}", exc_info=True) # Log traceback for parsing errors

    return new_items_found
