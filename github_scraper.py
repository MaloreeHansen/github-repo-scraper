import sys
import os
import re
import json
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from markdownify import markdownify as md

def init_driver():
    """Initializes and returns a headless Chrome webdriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # webdriver_manager is used to automatically get the correct driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def extract_repo_info(url):
    """Scrapes the GitHub repository for About description, tags, README, languages, health stats, and dependencies."""
    print(f"Scraping repository: {url}")
    driver = init_driver()
    
    data = {
        "url": url,
        "name": "",
        "about": "No description provided.",
        "tags": [],
        "languages": [],
        "health": {
            "stars": "N/A",
            "forks": "N/A",
            "open_issues": "N/A",
            "license": "N/A",
            "last_commit": "N/A",
        },
        "dependencies": {},
        "readme": "No README found."
    }
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        
        # Wait for the main repository content to load
        wait.until(EC.presence_of_element_located((By.ID, "repository-container-header")))
        
        # Extract repo name from the URL path
        parsed_url = urlparse(url)
        path_parts = [p for p in parsed_url.path.split('/') if p]
        if len(path_parts) >= 2:
            data["name"] = f"{path_parts[0]}/{path_parts[1]}"
        else:
            data["name"] = "Unknown Repository"
            
        # --- About description (sidebar) ---
        try:
            about_element = driver.find_element(By.CSS_SELECTOR, "div.BorderGrid-cell > p.f4.my-3")
            if about_element:
                data["about"] = about_element.text
        except NoSuchElementException:
            pass
            
        # --- Tags/Topics (sidebar) ---
        try:
            topic_elements = driver.find_elements(By.CSS_SELECTOR, "div.BorderGrid-cell a.topic-tag")
            if topic_elements:
                data["tags"] = [tag.text for tag in topic_elements]
        except NoSuchElementException:
            pass

        # --- Language breakdown ---
        print("  Extracting language breakdown...")
        try:
            lang_items = driver.find_elements(By.CSS_SELECTOR, "li.d-inline a[href*='/search?l=']")
            if lang_items:
                for item in lang_items:
                    try:
                        lang_name = item.find_element(By.CSS_SELECTOR, "span.text-bold").text
                        lang_pct = item.find_element(By.CSS_SELECTOR, "span:not(.text-bold)").text
                        if lang_name and lang_pct:
                            data["languages"].append({"name": lang_name, "percentage": lang_pct})
                    except NoSuchElementException:
                        continue
        except NoSuchElementException:
            pass

        # --- Repo health: stars, forks, issues, license, last commit ---
        print("  Extracting repository health stats...")

        # Stars
        try:
            star_el = driver.find_element(By.CSS_SELECTOR, "a[href$='/stargazers'] strong, #repo-stars-counter-star")
            if star_el:
                data["health"]["stars"] = star_el.text
        except NoSuchElementException:
            pass

        # Forks
        try:
            fork_el = driver.find_element(By.CSS_SELECTOR, "a[href$='/forks'] strong, #repo-network-counter")
            if fork_el:
                data["health"]["forks"] = fork_el.text
        except NoSuchElementException:
            pass

        # Open issues count
        try:
            issues_el = driver.find_element(By.CSS_SELECTOR, "a#issues-tab span.Counter, span#issues-repo-tab-count")
            if issues_el:
                data["health"]["open_issues"] = issues_el.text
        except NoSuchElementException:
            pass

        # License
        try:
            license_el = driver.find_element(By.CSS_SELECTOR, "a[data-analytics-event*='LICENSE'], a[href*='/blob/'] .mr-2")
            if license_el:
                data["health"]["license"] = license_el.text.strip()
        except NoSuchElementException:
            # Fallback: look for license text in the sidebar
            try:
                sidebar_links = driver.find_elements(By.CSS_SELECTOR, "div.BorderGrid-cell a")
                for link in sidebar_links:
                    link_text = link.text.strip().lower()
                    if "license" in link_text:
                        data["health"]["license"] = link.text.strip()
                        break
            except NoSuchElementException:
                pass

        # Last commit date
        try:
            commit_el = driver.find_element(By.CSS_SELECTOR, "relative-time")
            if commit_el:
                data["health"]["last_commit"] = commit_el.get_attribute("datetime") or commit_el.text
        except NoSuchElementException:
            pass

        # --- README content as HTML, then convert to Markdown ---
        try:
            readme_element = driver.find_element(By.CSS_SELECTOR, "article.markdown-body")
            if readme_element:
                readme_html = readme_element.get_attribute("innerHTML")
                data["readme"] = convert_html_to_markdown(readme_html)
        except NoSuchElementException:
            pass
            
        print(f"Successfully scraped main page data from {url}")

        # --- Dependency extraction (requires navigating to additional pages) ---
        print("  Checking for dependency files...")
        data["dependencies"] = extract_dependencies(driver, url)

    except TimeoutException:
        print("Error: Timed out waiting for page to load. Is this a valid GitHub repository URL?")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        driver.quit()
        
    return data


# Map of dependency file names to their ecosystem labels
DEPENDENCY_FILES = {
    "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (pyproject)",
    "package.json": "JavaScript (npm)",
    "Cargo.toml": "Rust (cargo)",
    "Gemfile": "Ruby (bundler)",
    "go.mod": "Go",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)",
}


def extract_dependencies(driver, repo_url):
    """Navigates to common dependency manifest files and extracts dependency names."""
    dependencies = {}
    repo_url = repo_url.rstrip("/")

    for filename, ecosystem in DEPENDENCY_FILES.items():
        # Navigate to the raw file URL on the default branch
        raw_url = f"{repo_url}/blob/HEAD/{filename}"
        try:
            driver.get(raw_url)
            # Brief wait to allow the page to resolve
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # If GitHub returns a 404, the page will not contain a code block
            # Check for the file content container
            try:
                code_block = driver.find_element(By.CSS_SELECTOR, "div.react-code-lines, table.highlight, div[itemprop='text']")
                raw_text = code_block.text
            except NoSuchElementException:
                continue  # File does not exist in this repo

            if not raw_text.strip():
                continue

            # Parse dependency names based on file type
            deps = parse_dependencies(filename, raw_text)
            if deps:
                dependencies[ecosystem] = deps
                print(f"    Found {len(deps)} dependencies in {filename}")

        except (TimeoutException, Exception):
            continue

    if not dependencies:
        print("    No recognized dependency files found.")

    return dependencies


def parse_dependencies(filename, raw_text):
    """Parses dependency names from the raw text content of a manifest file."""
    deps = []
    lines = raw_text.strip().split("\n")

    if filename == "requirements.txt":
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                # Extract package name (before any version specifier)
                dep_name = re.split(r"[=<>!~;\[]", line)[0].strip()
                if dep_name:
                    deps.append(dep_name)

    elif filename == "package.json":
        try:
            # Reconstruct JSON from the text (GitHub may add line numbers)
            # Try to find JSON content
            json_text = raw_text
            data = json.loads(json_text)
            for key in ["dependencies", "devDependencies"]:
                if key in data:
                    deps.extend(data[key].keys())
        except (json.JSONDecodeError, Exception):
            # Fallback: extract quoted strings that look like package names
            for line in lines:
                match = re.search(r'"([a-zA-Z@][a-zA-Z0-9_./-]*)"\s*:', line)
                if match and match.group(1) not in ("dependencies", "devDependencies", "name", "version", "description", "scripts", "main", "repository", "keywords", "author", "license"):
                    deps.append(match.group(1))

    elif filename == "Cargo.toml":
        in_deps = False
        for line in lines:
            if re.match(r"\[.*dependencies.*]", line):
                in_deps = True
                continue
            if line.startswith("[") and in_deps:
                in_deps = False
                continue
            if in_deps:
                match = re.match(r"([a-zA-Z0-9_-]+)\s*=", line)
                if match:
                    deps.append(match.group(1))

    elif filename == "Gemfile":
        for line in lines:
            match = re.match(r"gem\s+['\"]([^'\"]+)['\"]", line.strip())
            if match:
                deps.append(match.group(1))

    elif filename == "go.mod":
        in_require = False
        for line in lines:
            if line.strip().startswith("require (") or line.strip().startswith("require("):
                in_require = True
                continue
            if line.strip() == ")" and in_require:
                in_require = False
                continue
            if in_require:
                parts = line.strip().split()
                if parts and "/" in parts[0]:
                    deps.append(parts[0])
            elif line.strip().startswith("require ") and "(" not in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    deps.append(parts[1])

    elif filename in ("pom.xml", "build.gradle"):
        # Simple extraction — find artifact/group IDs
        if filename == "pom.xml":
            matches = re.findall(r"<artifactId>([^<]+)</artifactId>", raw_text)
            deps = [m for m in matches if m not in ("maven-compiler-plugin", "maven-surefire-plugin")]
        else:
            matches = re.findall(r"['\"]([a-zA-Z0-9_.]+:[a-zA-Z0-9_.-]+)['\"]", raw_text)
            deps = list(set(matches))

    elif filename == "pyproject.toml":
        in_deps = False
        for line in lines:
            if re.match(r"^\s*dependencies\s*=", line) or re.match(r"^\[.*dependencies.*]", line):
                in_deps = True
                continue
            if line.startswith("[") and in_deps:
                in_deps = False
                continue
            if in_deps:
                match = re.match(r"[\s'\"]*([a-zA-Z0-9_-]+)", line)
                if match and match.group(1) not in ("", "]"):
                    dep_name = re.split(r"[=<>!~;\[]", match.group(1))[0].strip()
                    if dep_name:
                        deps.append(dep_name)

    return deps

def convert_html_to_markdown(html_content):
    """Converts raw HTML from a GitHub README into clean, formatted Markdown."""
    # Convert HTML to Markdown, preserving headings, code blocks, tables, and links
    markdown_text = md(
        html_content,
        heading_style="ATX",
        code_language_callback=lambda el: el.get("class", [""])[0].replace("language-", "") if el.get("class") else "",
    )
    
    # Clean up excessive blank lines (more than 2 in a row)
    markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text)
    
    return markdown_text.strip()


def save_to_markdown(data, output_dir="output"):
    """Saves the extracted data to a well-formatted Markdown file."""
    if not data["name"] or data["name"] == "Unknown Repository":
        filename = "scraped_repo_summary.md"
    else:
        # Sanitize filename
        safe_name = data["name"].replace("/", "_")
        filename = f"{safe_name}_summary.md"
        
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        # Title
        f.write(f"# {data['name']}\n\n")
        
        # Metadata table
        f.write("## Repository overview\n\n")
        f.write("| Field | Details |\n")
        f.write("|-------|--------|\n")
        f.write(f"| **Source** | {data['url']} |\n")
        f.write(f"| **Description** | {data['about']} |\n")
        
        if data['tags']:
            tags_str = ", ".join(f"`{tag}`" for tag in data['tags'])
            f.write(f"| **Topics** | {tags_str} |\n")
        else:
            f.write("| **Topics** | None listed |\n")
        
        f.write("\n---\n\n")

        # Repository health section
        health = data.get("health", {})
        f.write("## Repository health\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| **Stars** | {health.get('stars', 'N/A')} |\n")
        f.write(f"| **Forks** | {health.get('forks', 'N/A')} |\n")
        f.write(f"| **Open issues** | {health.get('open_issues', 'N/A')} |\n")
        f.write(f"| **License** | {health.get('license', 'N/A')} |\n")
        f.write(f"| **Last commit** | {health.get('last_commit', 'N/A')} |\n")
        f.write("\n---\n\n")

        # Language breakdown section
        languages = data.get("languages", [])
        f.write("## Language breakdown\n\n")
        if languages:
            f.write("| Language | Percentage |\n")
            f.write("|----------|-----------|\n")
            for lang in languages:
                f.write(f"| {lang['name']} | {lang['percentage']} |\n")
        else:
            f.write("No language data available.\n")
        f.write("\n---\n\n")

        # Dependencies section
        dependencies = data.get("dependencies", {})
        f.write("## Dependencies\n\n")
        if dependencies:
            for ecosystem, deps in dependencies.items():
                f.write(f"### {ecosystem}\n\n")
                for dep in deps:
                    f.write(f"- `{dep}`\n")
                f.write("\n")
        else:
            f.write("No recognized dependency files were found in this repository.\n\n")
        f.write("---\n\n")
        
        # README content (already converted from HTML to Markdown)
        f.write("## README contents\n\n")
        f.write("> The following content was extracted from the repository's README file.\n\n")
        f.write(data['readme'] + "\n\n")
        
        # Footer
        f.write("---\n\n")
        f.write(f"*This summary was auto-generated by [GitHub Repository Scraper](https://github.com/) from `{data['url']}`.*\n")
        
    print(f"\nSuccessfully saved repository summary to: {filepath}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python github_scraper.py <github_repository_url> [output_directory]")
        print("Example: python github_scraper.py https://github.com/SeleniumHQ/selenium ./my_output")
        sys.exit(1)
        
    repo_url = sys.argv[1]
    
    # Default to 'output' directory unless specified
    output_directory = "output"
    if len(sys.argv) >= 3:
        output_directory = sys.argv[2]
    
    # Basic validation
    if not repo_url.startswith("https://github.com/"):
        print("Error: URL must start with https://github.com/")
        sys.exit(1)
        
    repo_data = extract_repo_info(repo_url)
    save_to_markdown(repo_data, output_dir=output_directory)
