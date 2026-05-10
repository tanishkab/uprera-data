#!/usr/bin/env python3
"""
HTML Report Generator for RERA Agents Data
==========================================
Creates an interactive HTML file from CSV data with filtering, search, and download capabilities.

Requirements:
    pip install pandas jinja2

Usage:
    python3 html_generator.py [csv_file]

Examples:
    python3 html_generator.py rera_agents_All_Districts_20260510_140751.csv
    python3 html_generator.py  # Will find the latest CSV file
"""

import sys
import os
import glob
import pandas as pd
from datetime import datetime
import json


class HTMLReportGenerator:
    def __init__(self, csv_file=None):
        """Initialize the HTML generator with a CSV file"""
        self.csv_file = csv_file
        self.data = None

        if csv_file:
            print(f"📊 Loading data from: {csv_file}")
            self.load_data(csv_file)
        else:
            print("⚠️  No CSV file specified. Will search for latest file.")

    def find_latest_csv(self):
        """Find the most recent RERA agents CSV file"""
        print("🔍 Searching for latest CSV file...")

        # Search patterns
        patterns = [
            "rera_agents_*.csv",
            "scrapped data/rera_agents_*.csv"
        ]

        csv_files = []
        for pattern in patterns:
            csv_files.extend(glob.glob(pattern))

        if not csv_files:
            print("❌ No CSV files found!")
            return None

        # Sort by modification time
        latest_file = max(csv_files, key=os.path.getmtime)
        print(f"✅ Found latest file: {latest_file}")
        return latest_file

    def load_data(self, csv_file):
        """Load data from CSV file"""
        try:
            self.data = pd.read_csv(csv_file)
            initial_count = len(self.data)

            # Filter out SKIPPED_MODAL and ERROR entries
            self.data = self.data[~self.data['Name'].isin(['SKIPPED_MODAL', 'ERROR'])]
            filtered_count = len(self.data)

            if filtered_count < initial_count:
                print(f"🧹 Filtered out {initial_count - filtered_count} invalid entries (SKIPPED_MODAL/ERROR)")

            print(f"✅ Loaded {filtered_count} valid records")
            print(f"   Columns: {', '.join(self.data.columns)}")

            # Get unique districts
            unique_districts = self.data['District'].unique()
            print(f"   Districts: {len(unique_districts)}")

            self.csv_file = csv_file
            return True

        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            return False

    def generate_html(self, output_file=None):
        """Generate interactive HTML file with filtering and download capabilities"""

        if self.data is None:
            print("❌ No data loaded!")
            return None

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"rera_agents_report_{timestamp}.html"

        print(f"\n🔧 Generating HTML report: {output_file}")

        # Convert data to JSON for JavaScript
        data_json = self.data.to_json(orient='records')

        # Get unique districts for filter dropdown
        districts = sorted(self.data['District'].unique().tolist())

        # Statistics
        total_agents = len(self.data)
        phone_count = (self.data['Phone'] != 'N/A').sum()
        email_count = (self.data['Email'] != 'N/A').sum()

        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UP-RERA Agents Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #1f4788 0%, #2563eb 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 36px;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .header p {{
            font-size: 16px;
            opacity: 0.9;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px 40px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .stat-card .number {{
            font-size: 32px;
            font-weight: 700;
            color: #1f4788;
            margin-bottom: 5px;
        }}

        .stat-card .label {{
            font-size: 14px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .controls {{
            padding: 30px 40px;
            background: white;
            border-bottom: 1px solid #e2e8f0;
        }}

        .controls-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}

        .control-group {{
            display: flex;
            flex-direction: column;
        }}

        .control-group label {{
            font-size: 14px;
            font-weight: 600;
            color: #475569;
            margin-bottom: 8px;
        }}

        .control-group input,
        .control-group select {{
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 15px;
            transition: all 0.3s;
        }}

        .control-group input:focus,
        .control-group select:focus {{
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }}

        .buttons {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}

        .btn-primary {{
            background: #2563eb;
            color: white;
        }}

        .btn-primary:hover {{
            background: #1d4ed8;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
        }}

        .btn-secondary {{
            background: #10b981;
            color: white;
        }}

        .btn-secondary:hover {{
            background: #059669;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        }}

        .btn-danger {{
            background: #ef4444;
            color: white;
        }}

        .btn-danger:hover {{
            background: #dc2626;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
        }}

        .table-container {{
            padding: 0 40px 40px 40px;
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}

        thead {{
            background: #1f4788;
            color: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        th {{
            padding: 16px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }}

        tbody tr {{
            border-bottom: 1px solid #e2e8f0;
            transition: background 0.2s;
        }}

        tbody tr:hover {{
            background: #f1f5f9;
        }}

        tbody tr:nth-child(even) {{
            background: #f8fafc;
        }}

        tbody tr:nth-child(even):hover {{
            background: #f1f5f9;
        }}

        td {{
            padding: 16px;
            font-size: 14px;
            color: #334155;
        }}

        .no-results {{
            text-align: center;
            padding: 60px;
            color: #64748b;
            font-size: 18px;
        }}

        .footer {{
            background: #f8fafc;
            padding: 20px 40px;
            text-align: center;
            color: #64748b;
            font-size: 14px;
            border-top: 1px solid #e2e8f0;
        }}

        @media (max-width: 768px) {{
            .controls-grid {{
                grid-template-columns: 1fr;
            }}

            .stats {{
                grid-template-columns: 1fr;
            }}

            .header h1 {{
                font-size: 24px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏘️ UP-RERA Registered Agents Report</h1>
            <p>Interactive dashboard with filtering, search, and export capabilities</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number" id="totalCount">{total_agents}</div>
                <div class="label">Total Agents</div>
            </div>
            <div class="stat-card">
                <div class="number" id="filteredCount">{total_agents}</div>
                <div class="label">Filtered Results</div>
            </div>
            <div class="stat-card">
                <div class="number">{phone_count}</div>
                <div class="label">With Phone</div>
            </div>
            <div class="stat-card">
                <div class="number">{email_count}</div>
                <div class="label">With Email</div>
            </div>
        </div>

        <div class="controls">
            <div class="controls-grid">
                <div class="control-group">
                    <label for="districtFilter">🗺️ Filter by District</label>
                    <select id="districtFilter">
                        <option value="">All Districts</option>
                        {''.join(f'<option value="{d}">{d}</option>' for d in districts)}
                    </select>
                </div>

                <div class="control-group">
                    <label for="searchBox">🔍 Search by Name</label>
                    <input type="text" id="searchBox" placeholder="Type to search agent names...">
                </div>
            </div>

            <div class="buttons">
                <button class="btn btn-primary" onclick="downloadCSV()">📥 Download CSV</button>
                <button class="btn btn-secondary" onclick="downloadPDF()">📄 Download PDF</button>
                <button class="btn btn-danger" onclick="resetFilters()">🔄 Reset Filters</button>
            </div>
        </div>

        <div class="table-container">
            <table id="dataTable">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Name</th>
                        <th>Phone</th>
                        <th>Email</th>
                        <th>District</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                    <!-- Data will be populated by JavaScript -->
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")} | Source: {os.path.basename(self.csv_file)}</p>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.31/jspdf.plugin.autotable.min.js"></script>

    <script>
        // Data from Python
        const allData = {data_json};
        let filteredData = [...allData];

        // Initialize the table
        function renderTable(data) {{
            const tbody = document.getElementById('tableBody');

            if (data.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" class="no-results">No results found. Try adjusting your filters.</td></tr>';
                return;
            }}

            tbody.innerHTML = data.map((agent, index) => `
                <tr>
                    <td>${{index + 1}}</td>
                    <td>${{agent.Name}}</td>
                    <td>${{agent.Phone}}</td>
                    <td>${{agent.Email}}</td>
                    <td>${{agent.District}}</td>
                </tr>
            `).join('');

            // Update filtered count
            document.getElementById('filteredCount').textContent = data.length;
        }}

        // Filter function
        function applyFilters() {{
            const districtFilter = document.getElementById('districtFilter').value.toLowerCase();
            const searchText = document.getElementById('searchBox').value.toLowerCase();

            filteredData = allData.filter(agent => {{
                const matchesDistrict = !districtFilter || agent.District.toLowerCase() === districtFilter;
                const matchesSearch = !searchText || agent.Name.toLowerCase().includes(searchText);
                return matchesDistrict && matchesSearch;
            }});

            renderTable(filteredData);
        }}

        // Reset filters
        function resetFilters() {{
            document.getElementById('districtFilter').value = '';
            document.getElementById('searchBox').value = '';
            applyFilters();
        }}

        // Download CSV
        function downloadCSV() {{
            const headers = ['Agent_Number', 'Name', 'Phone', 'Email', 'District'];
            const csvContent = [
                headers.join(','),
                ...filteredData.map((agent, index) => [
                    index + 1,
                    `"${{agent.Name}}"`,
                    agent.Phone,
                    `"${{agent.Email}}"`,
                    `"${{agent.District}}"`
                ].join(','))
            ].join('\\n');

            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);

            link.setAttribute('href', url);
            link.setAttribute('download', `rera_agents_filtered_${{new Date().getTime()}}.csv`);
            link.style.visibility = 'hidden';

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}

        // Download PDF
        function downloadPDF() {{
            const {{ jsPDF }} = window.jspdf;
            const doc = new jsPDF();

            // Add title
            doc.setFontSize(18);
            doc.setTextColor(31, 71, 136);
            doc.text('UP-RERA Registered Agents Report', 14, 20);

            // Add metadata
            doc.setFontSize(10);
            doc.setTextColor(100, 100, 100);
            doc.text(`Generated: ${{new Date().toLocaleString()}}`, 14, 28);
            doc.text(`Total Records: ${{filteredData.length}}`, 14, 33);

            // Prepare table data
            const tableData = filteredData.map((agent, index) => [
                index + 1,
                agent.Name,
                agent.Phone,
                agent.Email,
                agent.District
            ]);

            // Add table
            doc.autoTable({{
                head: [['#', 'Name', 'Phone', 'Email', 'District']],
                body: tableData,
                startY: 40,
                theme: 'grid',
                headStyles: {{
                    fillColor: [31, 71, 136],
                    textColor: 255,
                    fontStyle: 'bold',
                    fontSize: 9
                }},
                bodyStyles: {{
                    fontSize: 8
                }},
                alternateRowStyles: {{
                    fillColor: [245, 245, 245]
                }},
                margin: {{ top: 40 }}
            }});

            // Save PDF
            doc.save(`rera_agents_filtered_${{new Date().getTime()}}.pdf`);
        }}

        // Event listeners
        document.getElementById('districtFilter').addEventListener('change', applyFilters);
        document.getElementById('searchBox').addEventListener('input', applyFilters);

        // Initial render
        renderTable(filteredData);
    </script>
</body>
</html>"""

        # Write HTML file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ HTML report generated successfully!")
            print(f"📁 File: {output_file}")
            print(f"📊 Contains {total_agents} records with {len(districts)} districts")

            # Get absolute path
            abs_path = os.path.abspath(output_file)
            print(f"\n🌐 Open in browser: file://{abs_path}")

            return output_file

        except Exception as e:
            print(f"❌ Error writing HTML file: {e}")
            return None


def main():
    """Main execution function"""
    print("=" * 70)
    print("  HTML REPORT GENERATOR FOR UP-RERA AGENTS")
    print("  📊 Interactive Dashboard with Filtering & Export")
    print("=" * 70)

    # Check for command-line argument
    csv_file = None
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]

        if not os.path.exists(csv_file):
            print(f"\n❌ File not found: {csv_file}")
            sys.exit(1)

    # Create generator
    generator = HTMLReportGenerator(csv_file)

    # If no file provided, find the latest one
    if generator.data is None:
        latest_file = generator.find_latest_csv()

        if latest_file is None:
            print("\n❌ No CSV files found. Please run the scrapper first.")
            sys.exit(1)

        # Load the latest file
        if not generator.load_data(latest_file):
            print("\n❌ Failed to load data")
            sys.exit(1)

    # Generate HTML
    output_file = generator.generate_html()

    if output_file:
        print("\n" + "=" * 70)
        print("  ✅ HTML GENERATION COMPLETE!")
        print("=" * 70)
        print(f"\n📂 Open the file in your browser to view the interactive report")
        print(f"   Features:")
        print(f"   • Filter by district")
        print(f"   • Search by agent name")
        print(f"   • Download filtered data as CSV")
        print(f"   • Download filtered data as PDF")
    else:
        print("\n❌ HTML generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
