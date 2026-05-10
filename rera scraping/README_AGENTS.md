# UP-RERA Scraper & HTML Generator System

A two-agent system that scrapes RERA agent data and generates interactive HTML dashboards.

## 📁 Files Overview

### 1. `scrapper_district.py`
- **Purpose**: Web scraper for UP-RERA website
- **Features**:
  - Extracts registered agent information
  - Filters by district
  - Exports to CSV and PDF
- **Status**: ⚠️ DO NOT EDIT (as requested)

### 2. `html_generator.py` ✨ NEW
- **Purpose**: Generates interactive HTML dashboard from CSV data
- **Features**:
  - Automatically filters out invalid entries (SKIPPED_MODAL, ERROR)
  - Filter agents by district dropdown
  - Search agents by name (real-time)
  - Download filtered data as CSV
  - Download filtered data as PDF
  - Beautiful responsive design
  - Statistics dashboard

### 3. `main.py` ✨ NEW
- **Purpose**: Orchestrator that runs both agents
- **Features**:
  - Runs scraper first
  - Automatically generates HTML from scraped data
  - Provides summary of all generated files
  - Error handling and recovery

## 🚀 Quick Start

### Run Everything Together (Recommended)
```bash
# Interactive mode (will prompt for inputs)
python3 main.py

# Automated mode - scrape 10 agents in headless mode
python3 main.py 10 headless

# Scrape 5 agents with visible browser
python3 main.py 5
```

### Run Individual Agents

#### Scraper Only
```bash
# Interactive mode
python3 scrapper_district.py

# Scrape 10 agents in headless mode
python3 scrapper_district.py 10 headless
```

#### HTML Generator Only
```bash
# Auto-detect latest CSV file
python3 html_generator.py

# Use specific CSV file
python3 html_generator.py rera_agents_All_Districts_20260510_140751.csv
```

## 📦 Dependencies

Install all required packages:
```bash
pip install selenium webdriver-manager pandas reportlab jinja2
```

Or if you have a requirements.txt:
```bash
pip install -r requirements.txt
```

## 📊 Output Files

After running the system, you'll get:

1. **CSV File**: `rera_agents_[District]_[timestamp].csv`
   - Raw data in spreadsheet format
   - Can be opened in Excel, Google Sheets, etc.

2. **PDF File**: `rera_agents_[District]_[timestamp].pdf`
   - Formatted report with tables
   - Ready to print or share

3. **HTML File**: `rera_agents_report_[timestamp].html`
   - Interactive dashboard
   - Open in any web browser
   - No internet connection required (standalone file)

## 🌐 HTML Dashboard Features

The generated HTML dashboard includes:

### Filtering & Search
- **District Filter**: Dropdown to filter by specific district
- **Name Search**: Real-time search as you type
- **Reset Button**: Clear all filters instantly

### Export Options
- **Download CSV**: Export filtered data to CSV
- **Download PDF**: Generate PDF from filtered results
- Both downloads respect current filters

### User Interface
- 📊 Statistics cards showing total agents, filtered count, phone/email availability
- 📱 Responsive design works on mobile, tablet, and desktop
- 🎨 Modern gradient design with smooth animations
- ⚡ Fast and lightweight (all-in-one HTML file)

### Data Display
- Sortable table with all agent information
- Alternating row colors for better readability
- Hover effects for better UX
- Sticky header when scrolling

## 📋 Workflow

```
┌─────────────────────────────┐
│   User runs main.py         │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Agent 1: Scraper           │
│  • Scrapes UP-RERA website  │
│  • Saves CSV + PDF          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Agent 2: HTML Generator    │
│  • Reads CSV file           │
│  • Generates HTML dashboard │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  All files ready!           │
│  • CSV  ✅                  │
│  • PDF  ✅                  │
│  • HTML ✅                  │
└─────────────────────────────┘
```

## 💡 Usage Examples

### Example 1: Quick Scrape & View
```bash
python3 main.py 5 headless
# This will:
# 1. Scrape 5 agents without showing browser
# 2. Generate HTML dashboard
# 3. Show you the file:// URL to open in browser
```

### Example 2: Regenerate HTML from Existing Data
```bash
python3 html_generator.py scrapped\ data/rera_agents_Lucknow_20260510_132122.csv
# Useful when you want a new dashboard from old data
```

### Example 3: Full Interactive Scrape
```bash
python3 main.py
# This will:
# 1. Ask how many agents to scrape
# 2. Ask if headless mode
# 3. Show available districts
# 4. Let you select a district
# 5. Generate all outputs
```

## 🔧 Troubleshooting

### Issue: "No CSV files found"
**Solution**: Run the scraper first:
```bash
python3 scrapper_district.py
```

### Issue: HTML not opening in browser
**Solution**: Copy the `file://` URL from terminal and paste in browser address bar

### Issue: Scraper failing
**Solution**: Check your internet connection and ensure ChromeDriver is installed:
```bash
pip install --upgrade webdriver-manager
```

### Issue: PDF download not working in HTML
**Solution**: Ensure you're using a modern browser (Chrome, Firefox, Safari, Edge)

## 📝 Notes

- The scrapper_district.py file is **not modified** as requested
- Both new files work independently and together
- All files are standalone and well-documented
- No external server needed for HTML dashboard
- CSV files from "scrapped data/" folder are automatically detected

## 🎯 Benefits

1. **Automated Workflow**: One command runs everything
2. **User-Friendly**: Beautiful HTML interface anyone can use
3. **Flexible**: Run agents separately or together
4. **No Dependencies for HTML**: Just open in browser, no setup needed
5. **Export Options**: Multiple formats (CSV, PDF, HTML) for different needs

## 🌟 Features Summary

| Feature | Scraper | HTML Generator | Main |
|---------|---------|----------------|------|
| Web Scraping | ✅ | ❌ | ✅ |
| District Filter | ✅ | ✅ | ✅ |
| CSV Export | ✅ | ✅ | ✅ |
| PDF Export | ✅ | ✅ | ✅ |
| Interactive UI | ❌ | ✅ | ✅ |
| Name Search | ❌ | ✅ | ✅ |
| Auto Run Both | ❌ | ❌ | ✅ |

---

**Created**: May 2026
**Version**: 1.0
**Status**: Production Ready ✅
