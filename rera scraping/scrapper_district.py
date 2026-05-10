#!/usr/bin/env python3
"""
UP RERA Web Scraper Agent - District-Based Scraping with PDF Export
====================================================================
Navigates to https://up-rera.in/, extracts districts from the agents table,
allows user to select a district, then scrapes agents for that district and exports to PDF.

Requirements:
    pip install selenium webdriver-manager pandas reportlab

Usage:
    python3 scrapper_district.py [num_agents] [headless]

Examples:
    python3 scrapper_district.py 10 headless    # Scrape 10 agents in headless mode
    python3 scrapper_district.py 5              # Scrape 5 agents with visible browser
    python3 scrapper_district.py                # Interactive mode
"""

import sys
import time
import pandas as pd
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

class UPRERAScraperAgent:
    def __init__(self, headless=False):
        """Initialize the scraper agent with Chrome browser"""
        print("🤖 Initializing UP-RERA Scraper Agent...")

        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        if not headless:
            chrome_options.add_argument("--start-maximized")
        else:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Initialize the driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

        print("✅ Browser initialized successfully!")

    def navigate_to_homepage(self):
        """Navigate to UP-RERA homepage"""
        print("\n📍 Step 1: Navigating to UP-RERA homepage...")
        self.driver.get("https://up-rera.in/")
        time.sleep(4)
        print(f"✅ Loaded: {self.driver.title}")

    def close_popup_if_exists(self):
        """Close any popups that appear"""
        print("\n🔍 Step 2: Checking for popups...")
        try:
            time.sleep(2)

            # Try multiple popup selectors
            popup_selectors = [
                "//button[contains(text(), 'No thanks')]",
                "//button[contains(text(), 'Close')]",
                "//button[@class='close']",
                "//*[@id='closeModal']"
            ]

            for selector in popup_selectors:
                try:
                    popup_btn = self.driver.find_element(By.XPATH, selector)
                    if popup_btn.is_displayed():
                        popup_btn.click()
                        print(f"✅ Closed popup")
                        time.sleep(1)
                        break
                except:
                    continue

            # Force close using JavaScript
            self.driver.execute_script("""
                var modals = document.querySelectorAll('.modal');
                modals.forEach(function(modal) {
                    modal.style.display = 'none';
                });
                var backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(function(backdrop) {
                    backdrop.remove();
                });
                document.body.classList.remove('modal-open');
                document.body.style.overflow = 'auto';
            """)
            print("✅ Popup handling complete")

        except Exception as e:
            print(f"ℹ️  Popup handling: {e}")

    def scroll_to_important_links(self):
        """Scroll down to the Important Links section and find SEARCH div"""
        print("\n📜 Step 3: Finding 'Important Links' and 'SEARCH' div...")

        try:
            # Scroll in small increments to find it
            print("   Scrolling down slowly...")

            for i in range(10):
                self.driver.execute_script(f"window.scrollBy(0, 300);")
                time.sleep(0.5)

                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "Important Links" in page_text or "IMPORTANT LINKS" in page_text:
                    print(f"   ✅ Found 'Important Links' after {i+1} scrolls")
                    time.sleep(1)
                    break

            # Find "Important Links" heading
            important_links_element = None
            search_div = None

            try:
                important_links_element = self.driver.find_element(By.XPATH,
                    "//*[contains(text(), 'Important Links') or contains(text(), 'IMPORTANT LINKS')]")

                self.driver.execute_script(
                    "arguments[0].style.border='5px solid red'; arguments[0].style.backgroundColor='yellow';",
                    important_links_element
                )

                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    important_links_element)

                print("✅ Found and highlighted 'Important Links' section")
                time.sleep(2)

                # Find SEARCH div
                search_patterns = [
                    "//div[contains(., 'SEARCH') or contains(., 'Search')]",
                    "//*[contains(text(), 'Important Links')]/following-sibling::*//div[contains(., 'SEARCH')]",
                ]

                print("   Looking for SEARCH div...")
                for pattern in search_patterns:
                    try:
                        search_divs = self.driver.find_elements(By.XPATH, pattern)
                        for div in search_divs:
                            if div.is_displayed() and 'SEARCH' in div.text.upper():
                                search_div = div
                                print(f"   ✅ Found SEARCH div")
                                break
                        if search_div:
                            break
                    except:
                        continue

                if search_div:
                    self.driver.execute_script(
                        "arguments[0].style.border='5px solid blue'; arguments[0].style.backgroundColor='lightgreen';",
                        search_div
                    )
                    print("✅ Highlighted SEARCH div!")
                    time.sleep(2)

            except Exception as e:
                print(f"⚠️  Error finding sections: {e}")

        except Exception as e:
            print(f"⚠️  Scroll error: {e}")

        return search_div

    def click_registered_agents(self):
        """Find and click on Registered Agents link with retry logic"""
        print("\n👥 Step 4: Looking for Registered Agents link...")

        try:
            self.driver.execute_script("window.scrollBy(0, 200);")
            time.sleep(1)

            # Target the specific ID from HTML
            agent_patterns = [
                ("id", "ctl00_ContentPlaceHolder1_lnkAgents"),
                ("xpath", "//span[contains(text(), 'Registered Agent')]/parent::a"),
                ("xpath", "//a[.//span[contains(text(), 'Registered Agent')]]"),
            ]

            # Keep trying for up to 30 seconds if no match found
            start_time = time.time()
            timeout = 30  # seconds
            attempt = 0

            while time.time() - start_time < timeout:
                attempt += 1
                print(f"   🔄 Attempt {attempt} (elapsed: {time.time() - start_time:.1f}s)")

                for method, selector in agent_patterns:
                    try:
                        print(f"   Trying: {method} = '{selector[:50]}...'")

                        if method == "id":
                            agent_element = self.driver.find_element(By.ID, selector)
                        else:
                            agent_element = self.driver.find_element(By.XPATH, selector)

                        if agent_element.tag_name == "span":
                            agent_link = agent_element.find_element(By.XPATH, "./..")
                        else:
                            agent_link = agent_element

                        if agent_link and agent_link.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                agent_link)
                            time.sleep(1)

                            self.driver.execute_script(
                                "arguments[0].style.border='5px solid red'; arguments[0].style.backgroundColor='yellow';",
                                agent_link
                            )

                            print(f"✅ Found Registered Agents link!")
                            print(f"   ID: {agent_link.get_attribute('id')}")
                            time.sleep(2)

                            self.driver.execute_script("arguments[0].click();", agent_link)

                            time.sleep(4)
                            print(f"✅ Clicked! Current URL: {self.driver.current_url}")

                            if "agents" in self.driver.current_url.lower():
                                print("✅ Successfully navigated to agents page!")
                                return

                    except Exception as e:
                        print(f"   Failed with {method}: {e}")
                        continue

                # If no match found in this iteration, wait a bit before retrying
                if time.time() - start_time < timeout:
                    print(f"   ⏳ No match found. Waiting 0.5s before retry...")
                    time.sleep(0.5)

            # If we've exhausted all attempts
            print("⚠️  Could not find Registered Agents link after timeout")
            print("⚠️  Navigating directly to agents page...")
            self.driver.get("https://up-rera.in/agents")
            time.sleep(3)

        except Exception as e:
            print(f"⚠️  Error: {e}")
            self.driver.get("https://up-rera.in/agents")
            time.sleep(3)

    def extract_districts_from_table(self):
        """Extract unique district values from the agents table"""
        print("\n🗺️  Step 5: Extracting districts from table...")

        districts = set()
        agent_district_map = []  # List of (agent_row_index, district) tuples

        try:
            # Wait for table to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(2)

            # Get all rows from the table
            all_rows = self.driver.find_elements(By.XPATH, "//table//tr")

            if len(all_rows) <= 1:
                print("⚠️  No data rows found in table")
                return [], []

            # First row is header - find the district column index
            header_row = all_rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, "th")

            district_col_index = -1

            print(f"  🔍 Found {len(header_cells)} columns")
            for idx, cell in enumerate(header_cells):
                header_text = cell.text.strip().lower()
                print(f"     Column {idx}: {header_text}")
                if 'district' in header_text or 'city' in header_text:
                    district_col_index = idx
                    print(f"  ✅ District column found at index {district_col_index}")
                    break

            if district_col_index == -1:
                print("  ⚠️  District column not found in header, trying to detect from data...")
                # Try to find district column by looking at data patterns
                # Assume it's one of the middle columns
                district_col_index = 2  # Common position for district column

            # Skip header row (first row) and get data rows
            data_rows = all_rows[1:]

            print(f"  📊 Processing {len(data_rows)} agent rows...")

            for row_idx, row in enumerate(data_rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if len(cells) > district_col_index:
                        district_value = cells[district_col_index].text.strip()

                        # Clean and validate district value
                        if district_value and len(district_value) > 0 and len(district_value) < 50:
                            # Skip if it looks like a number or registration ID
                            if not district_value.isdigit() and not re.match(r'^[A-Z0-9\-/]+$', district_value):
                                districts.add(district_value)
                                agent_district_map.append({
                                    'row_index': row_idx,
                                    'district': district_value
                                })
                except Exception as e:
                    print(f"  ⚠️  Error processing row {row_idx}: {e}")
                    continue

            # Convert set to sorted list
            districts_list = sorted(list(districts))

            print(f"  ✅ Found {len(districts_list)} unique districts")
            print(f"  ✅ Mapped {len(agent_district_map)} agents to districts")

            return districts_list, agent_district_map

        except Exception as e:
            print(f"  ❌ Error extracting districts: {e}")
            import traceback
            traceback.print_exc()
            return [], []

    def get_agents_for_district(self, district_name, agent_district_map, num_agents):
        """Get row indices of agents belonging to a specific district"""
        print(f"\n🎯 Step 6: Finding agents for district: {district_name}")

        matching_agents = []

        # If "All Districts", get all agents
        if district_name == "All Districts":
            for item in agent_district_map:
                matching_agents.append(item['row_index'])
        else:
            # Filter by specific district
            for item in agent_district_map:
                if item['district'] == district_name:
                    matching_agents.append(item['row_index'])

        print(f"  ✅ Found {len(matching_agents)} agents in {district_name}")

        # Limit to requested number (unless num_agents is -1, meaning "all")
        if num_agents == -1:
            print(f"  ✅ Will scrape ALL {len(matching_agents)} agents")
        elif len(matching_agents) > num_agents:
            matching_agents = matching_agents[:num_agents]
            print(f"  ℹ️  Limited to first {num_agents} agents")
        elif len(matching_agents) < num_agents:
            print(f"  ⚠️  Only {len(matching_agents)} agents available (requested {num_agents})")

        return matching_agents

    def scrape_from_detail_page(self, agent_number):
        """Scrape agent information from the currently open detail page"""
        agent_data = {
            'Agent_Number': agent_number,
            'Name': 'N/A',
            'Phone': 'N/A',
            'Email': 'N/A',
            'District': 'N/A'
        }

        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Extract all data from table in modal
            tds = self.driver.find_elements(By.TAG_NAME, "td")

            for i, td in enumerate(tds):
                td_text = td.text.strip().lower()
                next_td_text = tds[i + 1].text.strip() if i + 1 < len(tds) else ''

                # Extract Name
                if "agent name" in td_text or ("name" in td_text and agent_data['Name'] == 'N/A'):
                    agent_data['Name'] = next_td_text
                    print(f"  🔍 Found Name: {next_td_text}")

                # Extract District
                elif any(keyword in td_text for keyword in ["district", "city", "location", "region"]):
                    if next_td_text and agent_data['District'] == 'N/A':
                        agent_data['District'] = next_td_text
                        print(f"  🔍 Found District: {next_td_text}")

            # If district still not found, try to extract from page text
            if agent_data['District'] == 'N/A':
                district_patterns = [
                    r'District[\s:]+([A-Za-z\s]+?)(?:\n|$|Registration|Phone|Email|Address)',
                    r'City[\s:]+([A-Za-z\s]+?)(?:\n|$|Registration|Phone|Email|Address)',
                ]
                for pattern in district_patterns:
                    district_match = re.search(pattern, page_text, re.IGNORECASE)
                    if district_match:
                        agent_data['District'] = district_match.group(1).strip()
                        break

            # Extract phone number
            phone_patterns = [
                r'(?:Mobile|Phone|Contact)[\s:]*(\+91[\-\s]?)?([6-9][0-9]{9})',
                r'(\+91[\-\s]?)?([6-9][0-9]{9})',
            ]

            for pattern in phone_patterns:
                phone_match = re.search(pattern, page_text, re.IGNORECASE)
                if phone_match:
                    agent_data['Phone'] = phone_match.group(2) if phone_match.lastindex >= 2 else phone_match.group(1)
                    break

            # Extract email
            email_match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', page_text)
            if email_match:
                agent_data['Email'] = email_match.group(0)

            print(f"  📝 Agent {agent_number}: {agent_data['Name']}")
            print(f"  📍 District: {agent_data['District']} | 📞 {agent_data['Phone']} | 📧 {agent_data['Email']}")

        except Exception as e:
            print(f"  ⚠️  Error scraping agent {agent_number}: {e}")

        return agent_data

    def get_view_details_button_by_row_index(self, row_index):
        """Get view details button for a specific row index"""
        try:
            # Wait for table to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(0.5)

            # Get all rows from the table
            all_rows = self.driver.find_elements(By.XPATH, "//table//tr")

            # Skip the header row (first row) to get only data rows
            data_rows = all_rows[1:]  # Skip header at index 0

            if row_index >= len(data_rows):
                print(f"  ⚠️  Row index {row_index} not found in table")
                return None

            row = data_rows[row_index]

            # Find View Details button/link
            view_detail_buttons = row.find_elements(By.XPATH, ".//a[contains(text(), 'VIEW DETAIL') or contains(text(), 'View Detail')]")

            if view_detail_buttons:
                return view_detail_buttons[0]
            else:
                print(f"  ⚠️  No View Details button for row {row_index}")
                return None

        except Exception as e:
            print(f"  ⚠️  Error finding button for row {row_index}: {e}")
            return None

    def scrape_agents_by_row_indices(self, row_indices, district_name):
        """Scrape agents based on their row indices in the table"""
        print(f"\n🔄 Starting to scrape {len(row_indices)} agents from {district_name}...")
        print(f"⚡ Using optimized mode - fetching button for each agent individually")
        print("=" * 70)

        all_agents_data = []
        main_window = self.driver.current_window_handle
        agents_list_url = self.driver.current_url  # Save the agents list URL

        for idx, row_index in enumerate(row_indices, 1):
            try:
                print(f"\n📋 Agent {idx}/{len(row_indices)} (Row {row_index + 1})...")

                # Close any popup
                try:
                    no_thanks = self.driver.find_element(By.XPATH, "//button[contains(text(), 'No thanks')]")
                    no_thanks.click()
                    time.sleep(0.5)
                except:
                    pass

                # Get fresh button reference for this row
                button = self.get_view_details_button_by_row_index(row_index)

                if button is None:
                    print(f"  ⚠️  No valid button for row {row_index}, skipping")
                    all_agents_data.append({
                        'Agent_Number': idx,
                        'Name': 'N/A',
                        'Phone': 'N/A',
                        'Email': 'N/A',
                        'District': district_name
                    })
                    continue

                print(f"  🖱️  Clicking View Details button...")

                # Click the button
                self.driver.execute_script("arguments[0].click();", button)
                time.sleep(2)  # Wait for postback to complete

                # Check if new window/tab opened
                all_windows = self.driver.window_handles

                if len(all_windows) > 1:
                    # New window opened - switch to it
                    print(f"  ✅ Detail page opened in new window")
                    for window in all_windows:
                        if window != main_window:
                            self.driver.switch_to.window(window)
                            break

                    time.sleep(1.5)  # Wait for page to fully load

                    # Scrape the data
                    agent_data = self.scrape_from_detail_page(idx)
                    # Only override district if not "All Districts" and district is N/A
                    if district_name != "All Districts" and agent_data['District'] == 'N/A':
                        agent_data['District'] = district_name
                    all_agents_data.append(agent_data)

                    # Close the detail window and switch back
                    self.driver.close()
                    self.driver.switch_to.window(main_window)
                    time.sleep(0.5)

                    print(f"  ✓ Agent {idx} complete")

                else:
                    # Modal or same page - skip this agent
                    print(f"  ⚠️  Detail modal/page opened - skipping this agent")

                    all_agents_data.append({
                        'Agent_Number': idx,
                        'Name': 'SKIPPED_MODAL',
                        'Phone': 'N/A',
                        'Email': 'N/A',
                        'District': district_name
                    })

                    print(f"  ⏭️  Agent {idx} skipped")

                    # Navigate back to agents list for next iteration
                    print(f"  ↩️  Navigating back to agents list...")
                    self.driver.get(agents_list_url)
                    time.sleep(1.5)

            except Exception as e:
                print(f"  ❌ Error with agent {idx} (row {row_index}): {e}")
                import traceback
                traceback.print_exc()

                all_agents_data.append({
                    'Agent_Number': idx,
                    'Name': 'ERROR',
                    'Phone': 'N/A',
                    'Email': 'N/A',
                    'District': district_name
                })

                # Try to recover - go back to agents list
                try:
                    all_windows = self.driver.window_handles
                    if len(all_windows) > 1:
                        for window in all_windows:
                            if window != main_window:
                                self.driver.switch_to.window(window)
                                self.driver.close()
                        self.driver.switch_to.window(main_window)

                    # Navigate back to agents list
                    print(f"  ↩️  Recovering - navigating back to agents list...")
                    self.driver.get(agents_list_url)
                    time.sleep(1.5)
                except Exception as recovery_error:
                    print(f"  ❌ Recovery failed: {recovery_error}")

        return all_agents_data

    def save_to_csv(self, data, district_name, filename=None):
        """Save scraped data to CSV"""
        if not data:
            print("\n⚠️  No data to save")
            return None

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize district name for filename
            safe_district = district_name.replace(" ", "_").replace("/", "_")
            filename = f"rera_agents_{safe_district}_{timestamp}.csv"

        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 Data saved to: {filename}")
        print(f"📊 Total records: {len(data)}")

        # Show summary
        phone_count = sum(1 for agent in data if agent['Phone'] != 'N/A')
        email_count = sum(1 for agent in data if agent['Email'] != 'N/A')
        print(f"📞 Phone numbers found: {phone_count}/{len(data)}")
        print(f"📧 Emails found: {email_count}/{len(data)}")

        return filename

    def save_to_pdf(self, data, district_name, filename=None):
        """Save scraped data to PDF with formatted table"""
        if not data:
            print("\n⚠️  No data to save to PDF")
            return None

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize district name for filename
            safe_district = district_name.replace(" ", "_").replace("/", "_")
            filename = f"rera_agents_{safe_district}_{timestamp}.pdf"

        print(f"\n📄 Creating PDF: {filename}")

        try:
            # Create PDF document
            doc = SimpleDocTemplate(filename, pagesize=A4,
                                   rightMargin=30, leftMargin=30,
                                   topMargin=30, bottomMargin=18)

            # Container for PDF elements
            elements = []

            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#555555'),
                spaceAfter=20,
                alignment=TA_CENTER
            )

            # Add title
            title = Paragraph("UP-RERA Registered Agents Report", title_style)
            elements.append(title)

            # Add district and metadata
            timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
            subtitle = Paragraph(f"<b>District:</b> {district_name}<br/><b>Generated:</b> {timestamp}<br/><b>Total Agents:</b> {len(data)}", subtitle_style)
            elements.append(subtitle)
            elements.append(Spacer(1, 20))

            # Prepare data for table
            table_data = []

            # Add header row
            headers = ['#', 'Name', 'Phone', 'Email', 'District']
            table_data.append(headers)

            # Add data rows
            for agent in data:
                row = [
                    str(agent['Agent_Number']),
                    agent['Name'][:30] + '...' if len(agent['Name']) > 30 else agent['Name'],
                    agent['Phone'],
                    agent['Email'][:30] + '...' if len(agent['Email']) > 30 else agent['Email'],
                    agent['District'][:20] + '...' if len(agent['District']) > 20 else agent['District']
                ]
                table_data.append(row)

            # Create table
            col_widths = [0.5*inch, 2.2*inch, 1.3*inch, 2.2*inch, 1.5*inch]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)

            # Style the table
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

                # Data rows styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Agent number centered
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1f4788')),

                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ]))

            elements.append(table)

            # Add footer with statistics
            elements.append(Spacer(1, 20))
            phone_count = sum(1 for agent in data if agent['Phone'] != 'N/A')
            email_count = sum(1 for agent in data if agent['Email'] != 'N/A')

            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#555555'),
                alignment=TA_LEFT
            )

            stats = Paragraph(
                f"<b>Statistics:</b> Phone numbers found: {phone_count}/{len(data)} | "
                f"Emails found: {email_count}/{len(data)}",
                footer_style
            )
            elements.append(stats)

            # Build PDF
            doc.build(elements)

            print(f"✅ PDF created successfully: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Error creating PDF: {e}")
            import traceback
            traceback.print_exc()
            return None

    def close(self):
        """Close the browser"""
        print("\n🔚 Closing browser in 3 seconds...")
        time.sleep(3)
        try:
            self.driver.quit()
            print("✅ Browser closed")
        except Exception as e:
            print(f"ℹ️  Browser already closed: {e}")


def display_districts_menu(districts):
    """Display available districts and get user selection"""
    print("\n" + "=" * 70)
    print("  🗺️  AVAILABLE DISTRICTS")
    print("=" * 70)

    if not districts:
        print("❌ No districts found!")
        return None

    # Add "All Districts" option at the top
    print(f"   0. All Districts (No Filter)")
    print()

    for idx, district in enumerate(districts, 1):
        print(f"  {idx:2d}. {district}")

    print("=" * 70)

    while True:
        try:
            choice = input(f"\nSelect district (0 for all, 1-{len(districts)} for specific): ").strip()

            if not choice:
                print("❌ Please enter a number")
                continue

            choice_num = int(choice)

            if choice_num == 0:
                print(f"\n✅ Selected: All Districts (No Filter)")
                return "All Districts"
            elif 1 <= choice_num <= len(districts):
                selected = districts[choice_num - 1]
                print(f"\n✅ Selected: {selected}")
                return selected
            else:
                print(f"❌ Please enter a number between 0 and {len(districts)}")

        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled by user")
            return None


def get_user_input():
    """Get number of agents from user via command line"""
    print("\n" + "=" * 70)
    print("  🎯 AGENT SCRAPING CONFIGURATION")
    print("=" * 70)

    try:
        num_input = input("\nHow many agents to scrape? (enter number or 'all', default: 10): ").strip().lower()

        # Check if user wants all agents
        if num_input in ['all', 'a', '*']:
            num_agents = -1  # Use -1 to represent "all agents"
            print(f"\n✅ Will scrape ALL available agents")
        elif num_input:
            num_agents = int(num_input)
            print(f"\n✅ Will scrape {num_agents} agents")
        else:
            num_agents = 10
            print(f"\n✅ Will scrape {num_agents} agents")

        headless_input = input("Run in headless mode? (y/n, default: y): ").strip().lower()
        headless = headless_input not in ['n', 'no', 'false', '0']  # Default to yes unless explicitly no

        print(f"✅ Headless mode: {'ON' if headless else 'OFF'}")
        print("=" * 70)

        return num_agents, headless

    except (ValueError, KeyboardInterrupt):
        print("\n❌ Invalid input or cancelled by user")
        sys.exit(1)


def main():
    """Main execution function"""
    print("=" * 70)
    print("  UP-RERA SCRAPER AGENT - DISTRICT-BASED SCRAPING")
    print("  🤖 Automated Web Scraping with PDF Export")
    print("=" * 70)

    # Start timing
    start_time = time.time()
    print(f"\n⏱️  Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check for command-line arguments
    if len(sys.argv) > 1:
        try:
            # Check if user wants all agents
            if sys.argv[1].lower() in ['all', 'a', '*']:
                num_agents = -1  # Use -1 to represent "all agents"
                print(f"\n✅ CLI Mode: Will scrape ALL available agents")
            else:
                num_agents = int(sys.argv[1])
                print(f"\n✅ CLI Mode: Will scrape {num_agents} agents")

            headless = len(sys.argv) > 2 and sys.argv[2].lower() == 'headless'
            print(f"✅ Headless mode: {'ON' if headless else 'OFF'}")
            print("=" * 70)
        except ValueError:
            print("\n❌ Invalid argument. Usage: python3 scrapper_district.py [num_agents|all] [headless]")
            print("   Example: python3 scrapper_district.py 10 headless")
            print("   Example: python3 scrapper_district.py all headless")
            sys.exit(1)
    else:
        # Get user input via CLI
        num_agents, headless = get_user_input()

    # Initialize agent
    agent = UPRERAScraperAgent(headless=headless)

    try:
        # Navigate to agents page
        agent.navigate_to_homepage()
        agent.close_popup_if_exists()

        search_div = agent.scroll_to_important_links()
        agent.click_registered_agents()

        # Ask user if they want to filter by district
        print("\n" + "=" * 70)
        print("  🗺️  DISTRICT FILTERING OPTION")
        print("=" * 70)
        filter_choice = input("\nDo you want to filter agents by district? (y/n, default: n): ").strip().lower()
        use_district_filter = filter_choice in ['y', 'yes', 'true', '1']

        if use_district_filter:
            # Extract districts from the table
            districts_list, agent_district_map = agent.extract_districts_from_table()

            if not districts_list or not agent_district_map:
                print("❌ Could not extract districts from table. Exiting...")
                return

            # Let user select district
            selected_district = display_districts_menu(districts_list)

            if selected_district is None:
                print("❌ No district selected. Exiting...")
                return

            # Get agents for the selected district
            agent_row_indices = agent.get_agents_for_district(selected_district, agent_district_map, num_agents)
        else:
            # No district filtering - extract all agents directly
            print("\n✅ Skipping district filtering - will scrape agents sequentially")
            selected_district = "All_Districts"

            # Get all row indices (simple sequential list)
            try:
                # Wait for table to load
                agent.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                time.sleep(2)

                all_rows = agent.driver.find_elements(By.XPATH, "//table//tr")
                data_rows = all_rows[1:]  # Skip header row

                total_agents = len(data_rows)
                print(f"  ✅ Found {total_agents} total agents in table")

                # Create simple list of row indices
                if num_agents == -1:
                    # Scrape all agents
                    agent_row_indices = list(range(total_agents))
                    print(f"  ✅ Will scrape ALL {len(agent_row_indices)} agents")
                else:
                    # Limit to requested number
                    agent_row_indices = list(range(min(num_agents, total_agents)))
                    print(f"  ✅ Will scrape first {len(agent_row_indices)} agents")
            except Exception as e:
                print(f"  ❌ Error getting agent rows: {e}")
                return

        if not agent_row_indices:
            print(f"❌ No agents found for district: {selected_district}")
            return

        # Scrape agents
        print(f"\n{'=' * 70}")
        print(f"  🚀 STARTING SCRAPING PROCESS")
        print(f"{'=' * 70}")

        scrape_start_time = time.time()
        agents_data = agent.scrape_agents_by_row_indices(agent_row_indices, selected_district)
        scrape_duration = time.time() - scrape_start_time

        # Save to CSV
        csv_file = None
        if agents_data:
            csv_file = agent.save_to_csv(agents_data, selected_district)

        # Save to PDF
        pdf_file = None
        if agents_data:
            pdf_file = agent.save_to_pdf(agents_data, selected_district)

        # Calculate and display timing
        total_duration = time.time() - start_time

        print("\n" + "=" * 70)
        print("  ✅ SCRAPING COMPLETE!")
        print("=" * 70)

        if csv_file:
            print(f"\n📁 CSV File: {csv_file}")
        if pdf_file:
            print(f"📄 PDF File: {pdf_file}")

        print(f"\n⏱️  Performance Metrics:")
        print(f"   • Scraping time: {scrape_duration:.2f} seconds ({scrape_duration/60:.2f} minutes)")
        print(f"   • Total execution time: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
        print(f"   • Average time per agent: {scrape_duration/len(agents_data):.2f} seconds")
        print(f"   • Script ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()

    finally:
        agent.close()

        # Final timing summary
        final_duration = time.time() - start_time
        print(f"\n⏱️  Total script duration: {final_duration:.2f} seconds ({final_duration/60:.2f} minutes)")


if __name__ == "__main__":
    main()