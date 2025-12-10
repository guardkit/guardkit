---
id: TASK-048
title: Implement subagents.cc scraper for agent discovery
status: backlog
created: 2025-11-01T15:40:00Z
priority: high
complexity: 6
estimated_hours: 6
tags: [agent-discovery, web-scraping, subagents-cc]
epic: EPIC-001
feature: agent-discovery
dependencies: []
blocks: [TASK-050]
---

# TASK-048: Implement Subagents.cc Scraper

## Objective

Create a web scraper that discovers and extracts agent metadata from subagents.cc marketplace:
- Agent name, description, category
- Download count, ratings, favorites
- Tool requirements
- Source code/specification URL
- Last updated date

## Context

This is Phase 2.1 of agent discovery for `/template-create`. Subagents.cc is the first of three agent sources we'll integrate. It's a community marketplace with ~100+ agents and provides valuable metadata like download statistics.

## Scope

### In Scope
- Web scraping of subagents.cc
- Agent metadata extraction
- Local caching mechanism
- Error handling and rate limiting
- JSON output format

### Out of Scope
- Agent matching algorithm (TASK-050)
- GitHub agent parsing (TASK-049)
- Interactive selection UI (TASK-051)
- Agent download (TASK-052)

## Requirements

### Functional Requirements

**REQ-1**: Scrape agent listings
```
When accessing subagents.cc, the system shall:
- Fetch agent listing pages
- Extract agent cards/entries
- Parse agent metadata (name, description, category)
- Handle pagination if present
```

**REQ-2**: Extract agent metadata
```
For each agent, the system shall extract:
- Name (string)
- Description (string, 1-2 sentences)
- Category (string: "Testing", "Development", "DevOps", etc.)
- Download count (integer)
- Favorites/Stars (integer)
- Tools required (list of strings)
- Source URL (string)
- Last updated (datetime)
```

**REQ-3**: Implement caching
```
When scraping agents, the system shall:
- Cache results locally (JSON file)
- Respect cache TTL (15 minutes default)
- Allow force refresh
- Store timestamp of last scrape
```

**REQ-4**: Handle errors gracefully
```
When errors occur, the system shall:
- Retry failed requests (max 3 attempts)
- Log errors with context
- Continue with partial results if possible
- Return empty list on total failure (don't crash)
```

**REQ-5**: Respect rate limits
```
When scraping, the system shall:
- Add delay between requests (1-2 seconds)
- Respect robots.txt if available
- Include user agent header
- Implement exponential backoff on 429 errors
```

## Acceptance Criteria

### AC1: Agent Discovery
- [ ] Successfully scrapes subagents.cc homepage
- [ ] Extracts agent listings (>50 agents)
- [ ] Handles pagination if present
- [ ] Execution time <30 seconds for full scrape

### AC2: Metadata Extraction
- [ ] Extracts agent name correctly
- [ ] Extracts agent description
- [ ] Extracts category/tags
- [ ] Extracts download count (if available)
- [ ] Extracts tool requirements
- [ ] Extracts source URL

### AC3: Caching System
- [ ] Creates cache directory if not exists
- [ ] Saves results as JSON
- [ ] Reads from cache if fresh (<15 min)
- [ ] Force refresh flag works
- [ ] Cache includes timestamp

### AC4: Error Handling
- [ ] Handles network errors gracefully
- [ ] Retries failed requests (max 3)
- [ ] Logs errors with context
- [ ] Returns partial results on partial failure
- [ ] Doesn't crash on malformed HTML

### AC5: Rate Limiting
- [ ] Adds 1-2 second delay between requests
- [ ] Respects 429 (Too Many Requests) errors
- [ ] Implements exponential backoff
- [ ] Includes proper user agent

### AC6: Data Quality
- [ ] JSON output validates against schema
- [ ] No duplicate agents in results
- [ ] All required fields present
- [ ] URLs are valid format

## Implementation Plan

### Step 1: Create Scraper Module

```python
# installer/core/commands/lib/agent_discovery/subagents_cc_scraper.py

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
import logging

@dataclass
class AgentMetadata:
    name: str
    description: str
    category: str
    downloads: int
    favorites: int
    tools: List[str]
    source_url: str
    last_updated: str
    source: str = "subagents.cc"

class SubagentsCcScraper:
    BASE_URL = "https://subagents.cc"
    CACHE_DIR = Path.home() / ".agentecflow" / "cache" / "agents"
    CACHE_TTL = timedelta(minutes=15)

    def __init__(self, force_refresh: bool = False):
        self.force_refresh = force_refresh
        self.cache_file = self.CACHE_DIR / "subagents_cc.json"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Taskwright Template Creator (github.com/taskwright)'
        })
        self.logger = logging.getLogger(__name__)

    def discover_agents(self) -> List[AgentMetadata]:
        """Main discovery method with caching"""

        # Check cache first
        if not self.force_refresh and self._is_cache_fresh():
            self.logger.info("Loading agents from cache")
            return self._load_from_cache()

        self.logger.info("Scraping subagents.cc for agents")

        agents = []

        try:
            # Scrape main page
            agents = self._scrape_agent_listings()

            # Save to cache
            self._save_to_cache(agents)

            return agents

        except Exception as e:
            self.logger.error(f"Failed to scrape subagents.cc: {e}")

            # Try to return stale cache if available
            if self.cache_file.exists():
                self.logger.warning("Returning stale cache due to error")
                return self._load_from_cache()

            return []

    def _scrape_agent_listings(self) -> List[AgentMetadata]:
        """Scrape agent listings from subagents.cc"""

        agents = []

        try:
            response = self._fetch_with_retry(self.BASE_URL)

            if response.status_code != 200:
                self.logger.error(f"Failed to fetch subagents.cc: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find agent cards (adjust selectors based on actual site structure)
            agent_cards = soup.find_all('div', class_=['agent-card', 'subagent-item'])

            for card in agent_cards:
                try:
                    agent = self._parse_agent_card(card)
                    if agent:
                        agents.append(agent)
                        time.sleep(0.5)  # Rate limiting between agent detail fetches
                except Exception as e:
                    self.logger.warning(f"Failed to parse agent card: {e}")
                    continue

            self.logger.info(f"Scraped {len(agents)} agents from subagents.cc")

        except Exception as e:
            self.logger.error(f"Error scraping agent listings: {e}")

        return agents

    def _parse_agent_card(self, card) -> Optional[AgentMetadata]:
        """Parse individual agent card to extract metadata"""

        try:
            # Extract agent name
            name_elem = card.find(['h2', 'h3', 'a'], class_='agent-name')
            name = name_elem.text.strip() if name_elem else None

            # Extract description
            desc_elem = card.find('p', class_=['description', 'agent-description'])
            description = desc_elem.text.strip() if desc_elem else ""

            # Extract category/tag
            category_elem = card.find('span', class_=['category', 'tag'])
            category = category_elem.text.strip() if category_elem else "General"

            # Extract download count
            downloads_elem = card.find('span', class_='downloads')
            downloads = self._parse_number(downloads_elem.text) if downloads_elem else 0

            # Extract favorites
            fav_elem = card.find('span', class_='favorites')
            favorites = self._parse_number(fav_elem.text) if fav_elem else 0

            # Extract source URL
            link_elem = card.find('a', href=True)
            source_url = link_elem['href'] if link_elem else ""

            # Extract tools (if listed)
            tools = []
            tool_elems = card.find_all('span', class_='tool')
            for tool in tool_elems:
                tools.append(tool.text.strip())

            if not name:
                return None

            return AgentMetadata(
                name=name,
                description=description,
                category=category,
                downloads=downloads,
                favorites=favorites,
                tools=tools,
                source_url=source_url,
                last_updated=datetime.now().isoformat(),
                source="subagents.cc"
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse agent card: {e}")
            return None

    def _fetch_with_retry(self, url: str, max_retries: int = 3) -> requests.Response:
        """Fetch URL with retry logic and exponential backoff"""

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)

                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = (2 ** attempt) * 2  # Exponential backoff
                    self.logger.warning(f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue

                return response

            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

        raise Exception("Max retries exceeded")

    def _parse_number(self, text: str) -> int:
        """Parse number from text (handles '1.2k', '500', etc.)"""

        if not text:
            return 0

        text = text.strip().lower().replace(',', '')

        if 'k' in text:
            return int(float(text.replace('k', '')) * 1000)
        elif 'm' in text:
            return int(float(text.replace('m', '')) * 1000000)

        try:
            return int(text)
        except ValueError:
            return 0

    def _is_cache_fresh(self) -> bool:
        """Check if cache exists and is fresh"""

        if not self.cache_file.exists():
            return False

        cache_age = datetime.now() - datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        return cache_age < self.CACHE_TTL

    def _load_from_cache(self) -> List[AgentMetadata]:
        """Load agents from cache file"""

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                return [AgentMetadata(**agent) for agent in data]
        except Exception as e:
            self.logger.error(f"Failed to load cache: {e}")
            return []

    def _save_to_cache(self, agents: List[AgentMetadata]):
        """Save agents to cache file"""

        try:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, 'w') as f:
                json.dump([asdict(agent) for agent in agents], f, indent=2)

            self.logger.info(f"Cached {len(agents)} agents")

        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
```

### Step 2: Create CLI Interface

```python
# Usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape agents from subagents.cc")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh cache")
    parser.add_argument("--output", help="Output JSON file path")

    args = parser.parse_args()

    scraper = SubagentsCcScraper(force_refresh=args.force_refresh)
    agents = scraper.discover_agents()

    print(f"Discovered {len(agents)} agents from subagents.cc")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump([asdict(agent) for agent in agents], f, indent=2)
        print(f"Saved to {args.output}")
    else:
        for agent in agents[:10]:  # Show first 10
            print(f"- {agent.name} ({agent.category}) - {agent.downloads} downloads")
```

## Testing Strategy

### Unit Tests

```python
def test_parse_agent_card():
    """Should parse agent card HTML correctly"""
    html = """
    <div class="agent-card">
        <h3 class="agent-name">React State Specialist</h3>
        <p class="description">Expert in React state management</p>
        <span class="category">Development</span>
        <span class="downloads">248</span>
    </div>
    """
    soup = BeautifulSoup(html, 'html.parser')
    card = soup.find('div', class_='agent-card')

    scraper = SubagentsCcScraper()
    agent = scraper._parse_agent_card(card)

    assert agent.name == "React State Specialist"
    assert agent.downloads == 248

def test_parse_number_formats():
    """Should parse various number formats"""
    scraper = SubagentsCcScraper()

    assert scraper._parse_number("1.2k") == 1200
    assert scraper._parse_number("500") == 500
    assert scraper._parse_number("1.5m") == 1500000

def test_cache_freshness():
    """Should check cache freshness correctly"""
    scraper = SubagentsCcScraper()

    # Mock cache file with recent timestamp
    assert scraper._is_cache_fresh() == False  # No cache yet
```

### Integration Tests

```bash
# Test actual scraping (with rate limiting)
python installer/core/commands/lib/agent_discovery/subagents_cc_scraper.py --force-refresh

# Test cache usage
python installer/core/commands/lib/agent_discovery/subagents_cc_scraper.py
# Should use cache on second run
```

## Files to Create

1. `installer/core/commands/lib/agent_discovery/subagents_cc_scraper.py` - Main scraper (~400 lines)
2. `installer/core/commands/lib/agent_discovery/agent_metadata.py` - Data models (~100 lines)
3. `installer/core/commands/lib/agent_discovery/cache_manager.py` - Cache utilities (~150 lines)
4. `tests/unit/test_subagents_cc_scraper.py` - Unit tests (~300 lines)
5. `tests/integration/test_subagents_cc_live.py` - Live integration test (~100 lines)
6. `tests/fixtures/subagents_cc_sample.html` - Mock HTML for testing

## Definition of Done

- [ ] SubagentsCcScraper class implemented
- [ ] Agent metadata extraction working
- [ ] Caching system functional
- [ ] Rate limiting implemented
- [ ] Error handling comprehensive
- [ ] Retry logic with exponential backoff
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration test with live site successful
- [ ] Documentation and usage examples

## Success Metrics

- Scrapes >50 agents successfully
- Cache hit rate: >90% in normal usage
- Error recovery rate: >95% (partial results on failure)
- Execution time: <30 seconds for full scrape
- Zero crashes on malformed HTML

## Related Tasks

- **Blocks**: TASK-050 (Agent Matching Algorithm)
- **Parallel**: TASK-049 (GitHub Agent Parsers)
- **Epic**: EPIC-001 (Template Creation Automation)

---

**Estimated Time**: 6 hours
**Complexity**: 6/10 (Medium-High - web scraping complexity)
**Priority**: HIGH (First agent source)
