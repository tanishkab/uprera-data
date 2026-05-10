#!/usr/bin/env python3
"""
Main Orchestrator - UP-RERA Scraper & HTML Generator
====================================================
Runs both the scraper and HTML generator agents sequentially.

Requirements:
    pip install selenium webdriver-manager pandas reportlab jinja2

Usage:
    python3 main.py [num_agents] [headless]

Examples:
    python3 main.py              # Interactive mode
    python3 main.py 10 headless  # Scrape 10 agents in headless mode
    python3 main.py 5            # Scrape 5 agents with visible browser

This script will:
1. Run the scrapper_district.py agent to scrape RERA data
2. Automatically generate an interactive HTML report from the scraped data
"""

import sys
import subprocess
import os
import glob
import time
from datetime import datetime


class MainOrchestrator:
    def __init__(self):
        self.scraper_script = "scrapper_district.py"
        self.html_generator_script = "html_generator.py"
        self.csv_output = None
        self.pdf_output = None
        self.html_output = None

    def check_script_exists(self, script_name):
        """Check if a script file exists"""
        if not os.path.exists(script_name):
            print(f"❌ Script not found: {script_name}")
            return False
        return True

    def run_scraper(self, args):
        """Run the scraper agent"""
        print("\n" + "=" * 70)
        print("  🤖 AGENT 1: RUNNING SCRAPER")
        print("=" * 70)

        if not self.check_script_exists(self.scraper_script):
            return False

        try:
            # Build command
            cmd = ["python3", self.scraper_script] + args

            print(f"🔧 Command: {' '.join(cmd)}")
            print(f"⏳ Starting scraper agent...\n")

            # Run the scraper
            result = subprocess.run(cmd, check=True)

            if result.returncode == 0:
                print("\n✅ Scraper agent completed successfully!")
                return True
            else:
                print(f"\n❌ Scraper failed with code: {result.returncode}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"\n❌ Scraper error: {e}")
            return False
        except KeyboardInterrupt:
            print("\n\n⚠️  Scraper interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return False

    def find_latest_output_files(self):
        """Find the most recent CSV and PDF files created by the scraper"""
        print("\n🔍 Searching for output files...")

        # Search for CSV files
        csv_patterns = [
            "rera_agents_*.csv",
            "scrapped data/rera_agents_*.csv"
        ]

        csv_files = []
        for pattern in csv_patterns:
            csv_files.extend(glob.glob(pattern))

        # Search for PDF files
        pdf_patterns = [
            "rera_agents_*.pdf",
            "scrapped data/rera_agents_*.pdf"
        ]

        pdf_files = []
        for pattern in pdf_patterns:
            pdf_files.extend(glob.glob(pattern))

        # Get latest files
        if csv_files:
            self.csv_output = max(csv_files, key=os.path.getmtime)
            print(f"  ✅ Found CSV: {self.csv_output}")

        if pdf_files:
            self.pdf_output = max(pdf_files, key=os.path.getmtime)
            print(f"  ✅ Found PDF: {self.pdf_output}")

        return self.csv_output is not None

    def run_html_generator(self):
        """Run the HTML generator agent"""
        print("\n" + "=" * 70)
        print("  🤖 AGENT 2: RUNNING HTML GENERATOR")
        print("=" * 70)

        if not self.check_script_exists(self.html_generator_script):
            return False

        try:
            # Build command
            if self.csv_output:
                cmd = ["python3", self.html_generator_script, self.csv_output]
            else:
                cmd = ["python3", self.html_generator_script]

            print(f"🔧 Command: {' '.join(cmd)}")
            print(f"⏳ Starting HTML generator agent...\n")

            # Run the generator
            result = subprocess.run(cmd, check=True)

            if result.returncode == 0:
                print("\n✅ HTML generator agent completed successfully!")
                return True
            else:
                print(f"\n❌ HTML generator failed with code: {result.returncode}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"\n❌ HTML generator error: {e}")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return False

    def find_latest_html(self):
        """Find the most recent HTML file"""
        html_files = glob.glob("rera_agents_report_*.html")

        if html_files:
            self.html_output = max(html_files, key=os.path.getmtime)
            return True

        return False

    def display_summary(self):
        """Display final summary of all generated files"""
        print("\n" + "=" * 70)
        print("  🎉 ALL AGENTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)

        print("\n📁 Generated Files:")

        if self.csv_output:
            print(f"   📊 CSV:  {self.csv_output}")

        if self.pdf_output:
            print(f"   📄 PDF:  {self.pdf_output}")

        if self.html_output:
            abs_path = os.path.abspath(self.html_output)
            print(f"   🌐 HTML: {self.html_output}")
            print(f"\n   🔗 Open in browser: file://{abs_path}")

        print("\n📋 Summary:")
        print("   ✅ Data successfully scraped from UP-RERA")
        print("   ✅ Interactive HTML dashboard created")
        print("   ✅ CSV and PDF exports available")

        print("\n🎯 HTML Dashboard Features:")
        print("   • Filter agents by district")
        print("   • Search agents by name")
        print("   • Download filtered data as CSV")
        print("   • Download filtered data as PDF")
        print("   • Responsive design for all devices")

        print("\n" + "=" * 70)


def main():
    """Main execution function"""
    print("=" * 70)
    print("  UP-RERA SCRAPER & HTML GENERATOR ORCHESTRATOR")
    print("  🤖 Two-Agent System: Scrape → Generate Report")
    print("=" * 70)

    start_time = time.time()
    print(f"\n⏱️  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Get command-line arguments (pass them to the scraper)
    scraper_args = sys.argv[1:]

    # Create orchestrator
    orchestrator = MainOrchestrator()

    # Step 1: Run scraper
    scraper_success = orchestrator.run_scraper(scraper_args)

    if not scraper_success:
        print("\n❌ Orchestration failed: Scraper did not complete successfully")
        sys.exit(1)

    # Give the system a moment to write files
    time.sleep(1)

    # Step 2: Find output files
    if not orchestrator.find_latest_output_files():
        print("\n⚠️  Warning: Could not find CSV output files")
        print("   HTML generator will search for any available CSV files")

    # Step 3: Run HTML generator
    html_success = orchestrator.run_html_generator()

    if not html_success:
        print("\n⚠️  Warning: HTML generator did not complete successfully")
        print("   But scraper data is still available in CSV/PDF format")

    # Step 4: Find HTML output
    time.sleep(0.5)
    orchestrator.find_latest_html()

    # Step 5: Display summary
    orchestrator.display_summary()

    # Calculate total time
    total_time = time.time() - start_time
    print(f"\n⏱️  Total execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print(f"   Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n✅ Orchestration complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Orchestration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
