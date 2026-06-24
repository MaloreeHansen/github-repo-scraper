# GitHub Repository Scraper

A beginner-friendly Python web scraper built with [Selenium](https://www.selenium.dev/) that extracts key information from any public GitHub repository defined. 
Pass in a repository URL and get a clean, readable Markdown summary.
The summary includes the description, topics, full README content, language breakdown, health stats, and dependencies.

---

## Features

- Extracts the **About** description from the repository sidebar
- Collects all **topic tags** associated with the repository
- Pulls the full **README** content with proper formatting (headings, code blocks, tables, links, lists)
- **Language breakdown** — shows each programming language used and its percentage
- **Repository health check** — captures star count, fork count, open issues, license type, and last commit date
- **Dependency extraction** — detects and lists dependencies from common manifest files (`requirements.txt`, `package.json`, `Cargo.toml`, `Gemfile`, `go.mod`, `pom.xml`, `build.gradle`, `pyproject.toml`)
- Saves everything to a structured **Markdown file** for offline reading
- Supports a configurable output directory

---

## Prerequisites

Before getting started, make sure the following are installed:

- **Python 3.8+** — [Download here](https://www.python.org/downloads/)
- **Google Chrome** — [Download here](https://www.google.com/chrome/)
- **Git** (optional, for cloning) — [Download here](https://git-scm.com/downloads)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/github-repo-scraper.git
cd github-repo-scraper
```

### 2. Create a virtual environment

```bash
python3 -m venv selenium_env
```

### 3. Activate the virtual environment

**macOS / Linux:**
```bash
source selenium_env/bin/activate
```

**Windows:**
```bash
selenium_env\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

This installs three packages:

| Package | Purpose |
|---------|---------|
| `selenium` | Automates the Chrome browser to navigate to GitHub |
| `webdriver-manager` | Automatically downloads the correct Chrome driver |
| `markdownify` | Converts the scraped HTML into clean, formatted Markdown |

---

## Usage

### Basic usage

Run the script and pass any public GitHub repository URL as an argument:

```bash
python github_scraper.py <GITHUB_REPOSITORY_URL>
```

**Example:**
```bash
python github_scraper.py https://github.com/SeleniumHQ/selenium
```

This will create an `output/` folder in the current directory and save a file named `SeleniumHQ_selenium_summary.md` inside it.

### Custom output directory

To save the summary to a specific folder, pass the desired path as a second argument:

```bash
python github_scraper.py <GITHUB_REPOSITORY_URL> <OUTPUT_DIRECTORY>
```

**Example:**
```bash
python github_scraper.py https://github.com/pallets/flask ~/Desktop/Research
```

The script will create the folder if it does not already exist.

---

## Output

After a successful run, the terminal will display:

```
Scraping repository: https://github.com/SeleniumHQ/selenium
  Extracting language breakdown...
  Extracting repository health stats...
✅ Successfully scraped main page data from https://github.com/SeleniumHQ/selenium
  Checking for dependency files...
    Found 12 dependencies in requirements.txt

Successfully saved repository summary to: output/SeleniumHQ_selenium_summary.md
```

The generated Markdown file will contain:

| Section | Description |
|---------|-------------|
| **Repository overview** | A metadata table with the source URL, description, and topic tags |
| **Repository health** | Star count, fork count, open issues, license type, and last commit date |
| **Language breakdown** | A table showing each language used in the repo and its percentage |
| **Dependencies** | Lists of dependencies extracted from manifest files, grouped by ecosystem |
| **README contents** | The full README converted from HTML to Markdown, preserving all formatting |

---

## How it works

1. The script launches a **headless** (invisible) Chrome browser using Selenium.
2. It navigates to the provided GitHub repository URL.
3. It waits for the page to fully load, then extracts:
   - The **About** description from the sidebar
   - All **topic tags** listed on the repository
   - The **language breakdown** percentages from the sidebar
   - **Health stats**: stars, forks, open issues, license, and last commit date
   - The **README** as raw HTML from the `article.markdown-body` element
4. The raw HTML is converted into clean Markdown using the `markdownify` library, preserving all formatting.
5. The script then checks for common **dependency manifest files** (`requirements.txt`, `package.json`, etc.) by navigating to each file path. If a file exists, it parses out the dependency names.
6. Everything is saved to a `.md` file in the output directory.

---

## Supported dependency files

| File | Ecosystem |
|------|-----------|
| `requirements.txt` | Python (pip) |
| `pyproject.toml` | Python (pyproject) |
| `package.json` | JavaScript (npm) |
| `Cargo.toml` | Rust (cargo) |
| `Gemfile` | Ruby (bundler) |
| `go.mod` | Go |
| `pom.xml` | Java (Maven) |
| `build.gradle` | Java (Gradle) |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `cannot find Chrome binary` | Google Chrome is not installed or not found in the default location | Install [Google Chrome](https://www.google.com/chrome/) |
| `URL must start with https://github.com/` | An invalid URL was provided | Double-check that the URL points to a valid GitHub repository |
| `Timed out waiting for page to load` | The page failed to load within 10 seconds | Verify the URL is correct, that the repository is public, and that there is a stable internet connection |

---

## Project structure

```
github-repo-scraper/
├── github_scraper.py      # Main scraper script
├── requirements.txt       # Python dependencies (selenium, webdriver-manager, markdownify)
├── README.md              # Documentation (this file)
├── selenium_env/          # Virtual environment (not committed)
└── output/                # Default output directory (generated on first run)
```

---

## License

This project is open source and available under the [MIT License](LICENSE).
