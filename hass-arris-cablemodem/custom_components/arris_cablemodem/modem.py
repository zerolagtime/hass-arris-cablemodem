"""ARRIS Surfboard Cable Modem communication."""
from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


class ArrisModem:
    """Represent an ARRIS SB6183 modem."""

    def __init__(self, host: str) -> None:
        """Initialize the modem."""
        self.host = host
        self.url = f"http://{host}"

    def get_status(self) -> dict:
        """Get modem status."""
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Detect model
            model = self._detect_model(soup)
            
            data = {
                "model": model,
                "startup": self._parse_startup(soup),
                "downstream": self._parse_downstream(soup),
                "upstream": self._parse_upstream(soup),
            }
            
            return data
        except Exception as err:
            _LOGGER.error("Error fetching modem status: %s", err)
            raise

    def _detect_model(self, soup: BeautifulSoup) -> str:
        """Detect the modem model from the page."""
        try:
            # Look for model number in binnacle
            binnacle = soup.find("span", id="thisModelNumberIs")
            if binnacle:
                return binnacle.get_text(strip=True)
            
            # Look in page title
            title = soup.find("title")
            if title:
                title_text = title.get_text()
                # Try to extract model from title
                for model in ["SB6183", "SB6190", "TG1682G", "TG3482G"]:
                    if model in title_text:
                        return model
            
            # Look in page content
            text = soup.get_text()
            match = re.search(r'(SB\d{4}|TG\d{4}[A-Z]?)', text)
            if match:
                return match.group(1)
            
            return "ARRIS Unknown"
        except Exception as err:
            _LOGGER.debug("Could not detect model: %s", err)
            return "ARRIS Unknown"

    def _parse_startup(self, soup: BeautifulSoup) -> dict:
        """Parse startup procedure table."""
        startup = {}
        try:
            table = soup.find("table", class_="simpleTable")
            if not table:
                return startup
            
            rows = table.find_all("tr")
            for row in rows[2:]:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    procedure = cols[0].get_text(strip=True)
                    status = cols[1].get_text(strip=True)
                    
                    if "Connectivity State" in procedure:
                        startup["connectivity"] = status
                    elif "Boot State" in procedure:
                        startup["boot"] = status
                    elif "Configuration File" in procedure:
                        startup["config"] = status
                    elif "Security" in procedure:
                        startup["security"] = status
        except Exception as err:
            _LOGGER.error("Error parsing startup: %s", err)
        
        return startup

    def _parse_downstream(self, soup: BeautifulSoup) -> list[dict]:
        """Parse downstream channels."""
        channels = []
        try:
            tables = soup.find_all("table", class_="simpleTable")
            ds_table = None
            
            for table in tables:
                header = table.find("th")
                if header and "Downstream Bonded Channels" in header.get_text():
                    ds_table = table
                    break
            
            if not ds_table:
                return channels
            
            rows = ds_table.find_all("tr")[2:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 9:
                    try:
                        channel = {
                            "channel": int(cols[0].get_text(strip=True)),
                            "lock_status": cols[1].get_text(strip=True),
                            "modulation": cols[2].get_text(strip=True),
                            "channel_id": int(cols[3].get_text(strip=True)),
                            "frequency": int(cols[4].get_text(strip=True).replace(" Hz", "")),
                            "power": float(cols[5].get_text(strip=True).replace(" dBmV", "")),
                            "snr": float(cols[6].get_text(strip=True).replace(" dB", "")),
                            "corrected": int(cols[7].get_text(strip=True)),
                            "uncorrectable": int(cols[8].get_text(strip=True)),
                        }
                        channels.append(channel)
                    except (ValueError, IndexError) as err:
                        _LOGGER.warning("Error parsing downstream channel: %s", err)
        except Exception as err:
            _LOGGER.error("Error parsing downstream channels: %s", err)
        
        return channels

    def _parse_upstream(self, soup: BeautifulSoup) -> list[dict]:
        """Parse upstream channels."""
        channels = []
        try:
            tables = soup.find_all("table", class_="simpleTable")
            us_table = None
            
            for table in tables:
                header = table.find("th")
                if header and "Upstream Bonded Channels" in header.get_text():
                    us_table = table
                    break
            
            if not us_table:
                return channels
            
            rows = us_table.find_all("tr")[2:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 7:
                    try:
                        channel = {
                            "channel": int(cols[0].get_text(strip=True)),
                            "lock_status": cols[1].get_text(strip=True),
                            "channel_type": cols[2].get_text(strip=True),
                            "channel_id": int(cols[3].get_text(strip=True)),
                            "symbol_rate": cols[4].get_text(strip=True),
                            "frequency": int(cols[5].get_text(strip=True).replace(" Hz", "")),
                            "power": float(cols[6].get_text(strip=True).replace(" dBmV", "")),
                        }
                        channels.append(channel)
                    except (ValueError, IndexError) as err:
                        _LOGGER.warning("Error parsing upstream channel: %s", err)
        except Exception as err:
            _LOGGER.error("Error parsing upstream channels: %s", err)
        
        return channels


