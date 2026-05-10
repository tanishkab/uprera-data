#!/usr/bin/env python3
"""
UP RERA Web Scraper Agent - CLI Version (No GUI)
=================================================
Navigates to https://up-rera.in/, finds Registered Agents,
clicks View Details for each agent, and scrapes their information.

Requirements:
    pip install selenium webdriver-manager pandas

Usage:
    python3 scrapper_nogui.py [num_agents] [headless]

Examples:
    python3 scrapper_nogui.py 10 headless    # Scrape 10 agents in headless mode
    python3 scrapper_nogui.py 5              # Scrape 5 agents with visible browser
    python3 scrapper_nogui.py                # Interactive mode
"""

import sys
import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

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

            # Keep trying for up to 5 seconds if no match found
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

            # If we've exhausted all attempts for 5 seconds
            print("⚠️  Could not find Registered Agents link after 5 seconds")
            print("⚠️  Navigating directly to agents page...")
            self.driver.get("https://up-rera.in/agents")
            time.sleep(3)

        except Exception as e:
            print(f"⚠️  Error: {e}")
            self.driver.get("https://up-rera.in/agents")
            time.sleep(3)

    def scrape_from_detail_page(self, agent_number):
        """Scrape all agent information from the currently open detail page"""
        agent_data = {
            'Agent_Number': agent_number,
            'Name': 'N/A',
            'Phone': 'N/A',
            'District': 'N/A',
            'Registration_No': 'N/A',
            'Registration_Date': 'N/A',
            'Valid_Upto': 'N/A',
            'Email': 'N/A',
            'Address': 'N/A'
        }

        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Extract all data from table in modal
            tds = self.driver.find_elements(By.TAG_NAME, "td")

            print(f"  🔍 DEBUG: Found {len(tds)} td elements")

            for i, td in enumerate(tds):
                td_text = td.text.strip().lower()
                next_td_text = tds[i + 1].text.strip() if i + 1 < len(tds) else ''

                # Extract Name
                if "agent name" in td_text or ("name" in td_text and agent_data['Name'] == 'N/A'):
                    agent_data['Name'] = next_td_text
                    print(f"  🔍 Found Name: {next_td_text}")

                # Extract Registration Number
                elif "registration no" in td_text or "registration number" in td_text:
                    agent_data['Registration_No'] = next_td_text
                    print(f"  🔍 Found Registration No: {next_td_text}")

                # Extract Registration Date
                elif "registration date" in td_text or "date of registration" in td_text:
                    agent_data['Registration_Date'] = next_td_text
                    print(f"  🔍 Found Registration Date: {next_td_text}")

                # Extract Valid Upto
                elif "valid upto" in td_text or "validity" in td_text:
                    agent_data['Valid_Upto'] = next_td_text
                    print(f"  🔍 Found Valid Upto: {next_td_text}")

                # Extract District - with more patterns
                elif any(keyword in td_text for keyword in ["district", "city", "location", "region"]):
                    if next_td_text and agent_data['District'] == 'N/A':
                        agent_data['District'] = next_td_text
                        print(f"  🔍 Found District (matched '{td_text}'): {next_td_text}")

                # Extract Address
                elif "address" in td_text:
                    agent_data['Address'] = next_td_text
                    print(f"  🔍 Found Address: {next_td_text[:50]}...")

            # If district still not found, try to extract from page text
            if agent_data['District'] == 'N/A':
                print(f"  ⚠️  District not found in table, trying page text...")
                district_patterns = [
                    r'District[\s:]+([A-Za-z\s]+?)(?:\n|$|Registration|Phone|Email|Address)',
                    r'City[\s:]+([A-Za-z\s]+?)(?:\n|$|Registration|Phone|Email|Address)',
                ]
                for pattern in district_patterns:
                    district_match = re.search(pattern, page_text, re.IGNORECASE)
                    if district_match:
                        agent_data['District'] = district_match.group(1).strip()
                        print(f"  🔍 Found District from page text: {agent_data['District']}")
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
            print(f"  📍 District: {agent_data['District']} | 📞 Phone: {agent_data['Phone']} | 📧 Email: {agent_data['Email']}")

        except Exception as e:
            print(f"  ⚠️  Error scraping agent {agent_number}: {e}")

        return agent_data

    def get_single_view_details_button(self, agent_number):
        """Get a single view details button for a specific agent number"""
        try:
            # Wait for table to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            time.sleep(0.5)

            # Get all rows from the table
            all_rows = self.driver.find_elements(By.XPATH, "//table//tr")

            # Skip the header row (first row) to get only data rows
            data_rows = all_rows[1:]  # Skip header at index 0

            # Agent 1 should be at index 0 of data_rows
            row_index = agent_number - 1

            if row_index >= len(data_rows):
                print(f"  ⚠️  Agent {agent_number} not found in table")
                return None

            row = data_rows[row_index]

            # Find View Details button/link
            view_detail_buttons = row.find_elements(By.XPATH, ".//a[contains(text(), 'VIEW DETAIL') or contains(text(), 'View Detail')]")

            if view_detail_buttons:
                return view_detail_buttons[0]
            else:
                print(f"  ⚠️  No View Details button for agent {agent_number}")
                return None

        except Exception as e:
            print(f"  ⚠️  Error finding button for agent {agent_number}: {e}")
            return None

    def scrape_multiple_agents(self, num_agents):
        """Scrape multiple agents - get button fresh for each agent to avoid stale references"""
        print(f"\n🔄 Starting to scrape {num_agents} agents...")
        print(f"⚡ Using optimized mode - fetching button for each agent individually")
        print("=" * 70)

        all_agents_data = []
        main_window = self.driver.current_window_handle
        agents_list_url = self.driver.current_url  # Save the agents list URL

        for agent_number in range(1, num_agents + 1):
            try:
                print(f"\n📋 Agent {agent_number}/{num_agents}...")

                # Close any popup
                try:
                    no_thanks = self.driver.find_element(By.XPATH, "//button[contains(text(), 'No thanks')]")
                    no_thanks.click()
                    time.sleep(0.5)
                except:
                    pass

                # Get fresh button reference for this agent
                button = self.get_single_view_details_button(agent_number)

                if button is None:
                    print(f"  ⚠️  No valid button for agent {agent_number}, skipping")
                    all_agents_data.append({
                        'Agent_Number': agent_number,
                        'Name': 'N/A',
                        'Phone': 'N/A',
                        'District': 'N/A',
                        'Registration_No': 'N/A',
                        'Registration_Date': 'N/A',
                        'Valid_Upto': 'N/A',
                        'Email': 'N/A',
                        'Address': 'N/A'
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
                    agent_data = self.scrape_from_detail_page(agent_number)
                    all_agents_data.append(agent_data)

                    # Close the detail window and switch back
                    self.driver.close()
                    self.driver.switch_to.window(main_window)
                    time.sleep(0.5)

                    print(f"  ✓ Agent {agent_number} complete")

                else:
                    # Modal or same page - skip this agent
                    print(f"  ⚠️  Detail modal/page opened - skipping this agent")

                    all_agents_data.append({
                        'Agent_Number': agent_number,
                        'Name': 'SKIPPED_MODAL',
                        'Phone': 'N/A',
                        'District': 'N/A',
                        'Registration_No': 'N/A',
                        'Registration_Date': 'N/A',
                        'Valid_Upto': 'N/A',
                        'Email': 'N/A',
                        'Address': 'N/A'
                    })

                    print(f"  ⏭️  Agent {agent_number} skipped")

                    # Navigate back to agents list for next iteration
                    print(f"  ↩️  Navigating back to agents list...")
                    self.driver.get(agents_list_url)
                    time.sleep(1.5)

            except Exception as e:
                print(f"  ❌ Error with agent {agent_number}: {e}")
                import traceback
                traceback.print_exc()

                all_agents_data.append({
                    'Agent_Number': agent_number,
                    'Name': 'ERROR',
                    'Phone': 'N/A',
                    'District': 'N/A',
                    'Registration_No': 'N/A',
                    'Registration_Date': 'N/A',
                    'Valid_Upto': 'N/A',
                    'Email': 'N/A',
                    'Address': 'N/A'
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

    def save_to_csv(self, data, filename="rera_agents_complete.csv"):
        """Save scraped data to CSV"""
        if data:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 Data saved to: {filename}")
            print(f"📊 Total records: {len(data)}")

            # Show summary
            phone_count = sum(1 for agent in data if agent['Phone'] != 'N/A')
            email_count = sum(1 for agent in data if agent['Email'] != 'N/A')
            print(f"📞 Phone numbers found: {phone_count}/{len(data)}")
            print(f"📧 Emails found: {email_count}/{len(data)}")
        else:
            print("\n⚠️  No data to save")

    def close(self):
        """Close the browser"""
        print("\n🔚 Closing browser in 3 seconds...")
        time.sleep(3)
        try:
            self.driver.quit()
            print("✅ Browser closed")
        except Exception as e:
            print(f"ℹ️  Browser already closed: {e}")


def get_user_input():
    """Get number of agents from user via command line"""
    print("\n" + "=" * 70)
    print("  🎯 AGENT SCRAPING CONFIGURATION")
    print("=" * 70)

    try:
        num_input = input("\nHow many agents to scrape? (default: 10): ").strip()
        num_agents = int(num_input) if num_input else 10

        headless_input = input("Run in headless mode? (y/n, default: n): ").strip().lower()
        headless = headless_input in ['y', 'yes', 'true', '1']

        print(f"\n✅ Will scrape {num_agents} agents")
        print(f"✅ Headless mode: {'ON' if headless else 'OFF'}")
        print("=" * 70)

        return num_agents, headless

    except (ValueError, KeyboardInterrupt):
        print("\n❌ Invalid input or cancelled by user")
        sys.exit(1)


def main():
    """Main execution function"""
    print("=" * 70)
    print("  UP-RERA SCRAPER AGENT - CLI VERSION")
    print("  🤖 Automated Web Scraping with Detail Extraction")
    print("=" * 70)

    # Check for command-line arguments
    if len(sys.argv) > 1:
        try:
            num_agents = int(sys.argv[1])
            headless = len(sys.argv) > 2 and sys.argv[2].lower() == 'headless'
            print(f"\n✅ CLI Mode: Will scrape {num_agents} agents")
            print(f"✅ Headless mode: {'ON' if headless else 'OFF'}")
            print("=" * 70)
        except ValueError:
            print("\n❌ Invalid argument. Usage: python3 scrapper_nogui.py [num_agents] [headless]")
            print("   Example: python3 scrapper_nogui.py 10 headless")
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

        # Scrape multiple agents
        agents_data = agent.scrape_multiple_agents(num_agents)

        # Save to CSV
        if agents_data:
            agent.save_to_csv(agents_data)

        print("\n" + "=" * 70)
        print("  ✅ SCRAPING COMPLETE!")
        print("=" * 70)
        print("\n📁 Check 'rera_agents_complete.csv' for results")

    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()

    finally:
        agent.close()


if __name__ == "__main__":
    main()
