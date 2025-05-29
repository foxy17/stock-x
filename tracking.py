import requests
from bs4 import BeautifulSoup
import datetime
import logging
import hashlib
import sqlite3
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
DATABASE_FILE = os.path.join(SCRIPT_DIR, 'seen_items.db') # SQLite database file
MAX_STORED_IDENTIFIERS = 100

# --- Database Functions ---

def init_database(db_path=DATABASE_FILE):
    """Initialize the SQLite database and create the items table if it doesn't exist."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table with unique constraint on identifier only
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                title TEXT,
                description TEXT,
                link TEXT,
                identifier TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on identifier for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_identifier ON seen_items(identifier)')
        
        conn.commit()
        conn.close()
        logging.info(f"Database initialized at: {os.path.abspath(db_path)}")
    except sqlite3.Error as e:
        logging.error(f"Error initializing database: {e}")

def load_seen_items(db_path=DATABASE_FILE):
    """Loads seen item dictionaries from SQLite database."""
    abs_db_path = os.path.abspath(db_path)
    logging.info(f"Attempting to load seen items from: {abs_db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all items ordered by creation time (most recent last)
        cursor.execute('''
            SELECT timestamp, title, description, link, identifier 
            FROM seen_items 
            ORDER BY created_at ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to the same format as before
        item_objects_list = []
        # Track identifiers instead of composite keys
        identifiers_set = set()
        
        for row in rows:
            timestamp, title, description, link, identifier = row
            item_object = {
                "timestamp": timestamp,
                "title": title,
                "description": description,
                "link": link,
                "identifier": identifier
            }
            item_objects_list.append(item_object)
            identifiers_set.add(identifier)
        
        logging.info(f"Loaded {len(item_objects_list)} items ({len(identifiers_set)} unique identifiers) from {abs_db_path}")
        return item_objects_list, identifiers_set
        
    except sqlite3.Error as e:
        logging.error(f"Error loading seen items from {abs_db_path}: {e}. Starting fresh.")
        return [], set()

def save_seen_items(item_objects_list, db_path=DATABASE_FILE, max_items=MAX_STORED_IDENTIFIERS):
    """Saves seen item dictionaries to SQLite database, keeping only the most recent ones."""
    abs_db_path = os.path.abspath(db_path)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clean up old items if we exceed max_items
        cursor.execute('SELECT COUNT(*) FROM seen_items')
        current_count = cursor.fetchone()[0]
        
        if current_count > max_items:
            # Keep only the most recent max_items
            cursor.execute('''
                DELETE FROM seen_items 
                WHERE id NOT IN (
                    SELECT id FROM seen_items 
                    ORDER BY created_at DESC 
                    LIMIT ?
                )
            ''', (max_items,))
            
            deleted_count = cursor.rowcount
            logging.info(f"Trimmed seen items storage by removing {deleted_count} old items. Keeping {max_items} most recent items.")
        
        conn.commit()
        conn.close()
        
    except sqlite3.Error as e:
        logging.error(f"Error trimming seen items in {abs_db_path}: {e}")

def add_new_item(item_object, db_path=DATABASE_FILE):
    """Add a single new item to the SQLite database."""
    abs_db_path = os.path.abspath(db_path)
    logging.info(f"Attempting to add new item to database: {abs_db_path}")
    logging.debug(f"Item details: {item_object['title'][:50]}... (ID: {item_object['identifier'][:20]}...)")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if item already exists first
        cursor.execute('SELECT COUNT(*) FROM seen_items WHERE identifier = ?', (item_object['identifier'],))
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            logging.debug(f"Item already exists in database (duplicate identifier): {item_object['title'][:50]}...")
            conn.close()
            return False
        
        # Insert the new item
        cursor.execute('''
            INSERT INTO seen_items (timestamp, title, description, link, identifier)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            item_object['timestamp'],
            item_object['title'], 
            item_object['description'],
            item_object['link'],
            item_object['identifier']
        ))
        
        if cursor.rowcount > 0:
            logging.info(f"✓ Successfully added new item to database: {item_object['title'][:50]}...")
            conn.commit()
            conn.close()
            return True
        else:
            logging.warning(f"✗ Failed to add item to database (no rows affected): {item_object['title'][:50]}...")
            conn.close()
            return False
        
    except sqlite3.Error as e:
        logging.error(f"✗ Database error adding item: {e}")
        return False

# --- End Database Functions ---

# Initialize database on module load
init_database()
logging.info(f"Database file path: {os.path.abspath(DATABASE_FILE)}")

# Load seen items on module initialization
seen_item_objects_list, seen_item_identifiers_set = load_seen_items()
logging.info(f"Module initialization complete. Loaded {len(seen_item_objects_list)} items, {len(seen_item_identifiers_set)} unique identifiers")

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
    global seen_item_objects_list, seen_item_identifiers_set
    
    # If in-memory list is empty, reload from database
    if not seen_item_objects_list:
        logging.warning("In-memory item list is empty, reloading from database...")
        seen_item_objects_list, seen_item_identifiers_set = load_seen_items()
    
    logging.info(f"Returning {len(seen_item_objects_list)} items from get_initial_items()")
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

            # Check if this identifier is already seen
            if identifier not in seen_item_identifiers_set:
                item_object = {
                    "timestamp": pub_date,
                    "title": title,
                    "description": description,
                    "link": link_text,
                    "identifier": identifier
                }
                
                # Add to SQLite database
                if add_new_item(item_object):
                    # Update in-memory tracking only if successfully added to DB
                    seen_item_objects_list.append(item_object)
                    seen_item_identifiers_set.add(identifier)
                    new_items_found.append(item_object)
                    logging.info(f"New item found: {title[:50]}... (Published: {pub_date})")
                    
                    # Trim database if it exceeds the limit
                    save_seen_items(seen_item_objects_list)
            else:
                logging.debug(f"Duplicate item skipped (identifier already exists): {title[:50]}... (Published: {pub_date})")

    except Exception as e:
        logging.error(f"Error parsing content from {url}: {e}", exc_info=True) # Log traceback for parsing errors

    return new_items_found
