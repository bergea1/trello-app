"""
Inneholder hjelpefunksjoner for engine.py
"""

# pylint: disable=E1101
# pylint: disable=import-error


import asyncio
import json
import logging
import os
import re
import time
from collections import Counter, namedtuple
from datetime import datetime, timedelta, timezone
from typing import Any, List
from urllib.parse import quote

import boto3  # type: ignore
import botocore.exceptions as boto_exceptions  # type: ignore
import requests
import requests.exceptions as req_exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

ArticleInfo = namedtuple(
    "ArticleInfo",
    [
        "card_id",
        "overskrift",
        "overskrift_lang",
        "mal",
        "sist_endret",
        "friflyt",
        "pluss",
        "oppsummering",
        "status",
        "publish_time",
        "is_state",
        "is_form",
        "is_state_papir",
        "is_form_papir",
    ],
)

# Pre-compiled regex patterns for improved performance
# These patterns are used frequently and compiling them once avoids recompilation overhead
RE_LEGACY_ID = re.compile(r"id=(.{7})")
RE_URN_ID = re.compile(r"<id>urn:[^:]+:(\d{7})</id>")
RE_SLUG_ID = re.compile(r"(\d{7})$")
RE_PARAGRAPH = re.compile(r"<p>(.*?)</p>", re.DOTALL)
RE_IMG_SRC = re.compile(r"<img src=")


# pylint: disable=too-few-public-methods
class RequestsManager:
    """
    Wrapper for å sende HTTP requests.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "*/*"})
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def make_request(self, method, url, auth_token=None, **kwargs):
        """
        Sender en HTTP-request.
        """

        timeout = kwargs.pop("timeout", 10)
        if auth_token:
            self.session.headers.update({"Authorization": f"Basic {auth_token}"})
        try:
            return self._attempt_request(method, url, timeout=timeout, **kwargs)
        except (
            req_exceptions.HTTPError,
            req_exceptions.ConnectionError,
            req_exceptions.Timeout,
            req_exceptions.RequestException,
            ValueError,
        ) as e:
            self._handle_exception(e, url)
            return None

    def _attempt_request(self, method, url, timeout, **kwargs):
        """
        Sender en HTTP-request.
        """

        response = self.session.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        time.sleep(0.3)  # Venter 0,3 sekunder for å begrense antall requests.
        if "application/json" in response.headers.get("Content-Type", ""):
            try:
                return response.json()
            except ValueError:
                logging.error("Error parsing JSON from response: %s", response.text)
                return None
        return response

    def _handle_exception(self, exception, url):
        """
        Feilmeldinger.
        """

        if isinstance(exception, req_exceptions.HTTPError):
            logging.error(
                "HTTP Error %s for URL %s: %s",
                exception.response.status_code,
                url,
                exception.response.text,
            )
        elif isinstance(exception, req_exceptions.ConnectionError):
            logging.error("Connection Error: Unable to connect to the server.")
        elif isinstance(exception, req_exceptions.Timeout):
            logging.error("Timeout Error: The request timed out.")
        elif isinstance(exception, req_exceptions.RequestException):
            logging.error(
                "General Request Error during request to %s: %s", url, str(exception)
            )
        elif isinstance(exception, ValueError):
            logging.error("Error parsing JSON from response: %s", str(exception))
        else:
            logging.error(
                "An unexpected error occurred during request to %s: %s",
                url,
                str(exception),
            )


class TrelloManager:
    """
    Alle funksjoner som sender info til Trello.
    """

    def __init__(self):
        self.reqs = RequestsManager()

        self.API_KEY = Config.API_KEY
        self.API_TOKEN = Config.API_TOKEN
        self.BASE_URL = Config.BASE_URL
        self.BASE_URL_CARDS = Config.BASE_URL_CARDS
        self.CUSTOM_PAPIR = Config.CUSTOM_PAPIR
        self.CUSTOM_NETT = Config.CUSTOM_NETT
        self.CUSTOM_PUB_PAPIR = Config.CUSTOM_PUB_PAPIR
        self.CUSTOM_PUB_NETT = Config.CUSTOM_PUB_NETT
        self.CUSTOM_LAST_NETT = Config.CUSTOM_LAST_NETT
        self.CUSTOM_OPEN_NETT = Config.CUSTOM_OPEN_NETT
        self.NETT_BOARD = Config.NETT_BOARD
        self.PAPIR_BOARD = Config.PAPIR_BOARD

        self.auth_params = {
            "key": self.API_KEY,
            "token": self.API_TOKEN,
        }

        self.all_cards_nett = f"{self.BASE_URL}boards/{self.NETT_BOARD}/cards"
        self.all_cards_papir = f"{self.BASE_URL}boards/{self.PAPIR_BOARD}/cards"

    def get_cards(self, board, sort, **kwargs):
        """
        Henter alle kort fra et gitt Trello-brett.
        Hvis `sort` er satt til `True`, sorteres kortene etter custom fields.
        Hvis `fields` og `customFieldItems` er satt i kwargs, brukes disse som parametre.
        Hvis ingen av dem er satt, hentes alle kort uten spesifikke felter.
        Returnerer en liste over kortene.
        Args:
            board (str): Trello-brettets ID.
            sort (bool): Sorterer kortene etter custom fields.
            **kwargs: Trello REST API parametre.
        """
        if kwargs["fields"] and kwargs["customFieldItems"]:
            url = (
                f"{self.BASE_URL}boards/{board}/cards?"
                f"{kwargs['fields']}&{kwargs['customFieldItems']}"
            )
        elif kwargs["fields"] and not kwargs["customFieldsItems"]:
            url = f"{self.BASE_URL}boards/{board}/cards?{kwargs['fields']}"
        else:
            url = f"{self.BASE_URL}boards/{board}/cards"
        result = self.reqs.make_request("GET", url, params=self.auth_params)

        if sort and result and isinstance(result, list):
            allowed_fields = [self.CUSTOM_PAPIR, self.CUSTOM_NETT]
            result = [
                item["value"]["text"]
                for entry in result
                if isinstance(entry, dict) and "customFieldItems" in entry
                for item in entry["customFieldItems"]
                if isinstance(item, dict)
                and item.get("idCustomField") in allowed_fields
            ]
        logging.debug("get_cards: %s", result)
        logging.info("Alle kort er hentet fra %s", board)
        return result

    def collect_labels(self, labels, tag_fields):
        """
        Samler inn labels fra tag_fields og legger til i labels-listen.
        Args:
            labels (list): Liste over eksisterende labels.
            tag_fields (list): Liste over tag-felter som skal legges til.
        Returns:
            bool: True hvis labels ble endret, ellers False.
        """
        label_changed = False
        # Ensure labels is a list (most common case) to avoid repeated checks
        if not isinstance(labels, list):
            labels = list(labels) if labels is not None else []

        for tag in tag_fields:
            if tag and tag not in labels:
                labels.append(tag)
                label_changed = True
        return label_changed

    def create_card(self, card_list, **kwargs):
        """
        Funksjon for å lage et nytt Trello-kort.
        Args:
            card_list (str): listen kortet skal legges i. (idList).
            **kwargs: Valgfrie parametre for kortet, som navn, beskrivelse og labels.
            Mulige parametre finner du i Trello REST API dokumentasjonen.
        Returns:
            dict: Det opprettede kortet, eller None hvis det oppstod en feil.
        """

        try:
            params = {**self.auth_params, "idList": card_list}
            match kwargs:
                case {"name": name}:
                    params["name"] = name
                case {"desc": desc}:
                    params["desc"] = desc
                case {"idLabels": idlabels}:
                    params["idLabels"] = idlabels
            params.update(kwargs)
            card = self.reqs.make_request("POST", self.BASE_URL_CARDS, params=params)
            if card and isinstance(card, dict):
                logging.info("Kort %s er opprettet i Trello.", card["desc"])
            return card
        except (req_exceptions.RequestException, ValueError, KeyError) as e:
            logging.error(
                "Failed to create Trello card in list %s: %s",
                card_list,
                str(e),
                exc_info=True,
            )
            return None

    def update_card(self, card_id, **kwargs):
        """
        Oppdaterer et Trello-kort med angitte parametre.
        Args:
            card_id (str): ID-en til kortet som skal oppdateres.
            **kwargs: Valgfrie parametre for oppdatering, som navn, beskrivelse og labels.
            Mulige parametre finner du i Trello REST API dokumentasjonen.
        Returns:
            dict: Det oppdaterte kortet, eller None hvis det oppstod en feil.
        """

        try:
            url = f"{self.BASE_URL}cards/{card_id}"
            # Merge auth params with kwargs directly - kwargs already contains
            # all the needed parameters (idLabels, name, desc, etc.)
            params = {**self.auth_params, "id": card_id, **kwargs}

            response = self.reqs.make_request("PUT", url, params=params)
            if response:
                logging.info("Trello card %s updated.", card_id)
            else:
                logging.error("Failed to update Trello card %s.", card_id)
        except (req_exceptions.RequestException, ValueError, KeyError) as e:
            logging.error(
                "Failed to update Trello card %s: %s",
                card_id,
                getattr(e, "message", str(e)),
                exc_info=True,
            )
            return None
        return response

    def update_custom_card(self, card_id, custom_id, **kwargs):
        """
        Oppdaterer et spesifikt custom field på et Trello-kort.
        Args:
            card_id (str): ID-en til kortet som skal oppdateres.
            custom_id (str): ID-en til custom field som skal oppdateres. (idCustomField).
            **kwargs: Valgfrie parametre for oppdatering, som 'is_open' eller 'date'.
            Mulige parametre finner du i Trello REST API dokumentasjonen.
        """

        try:
            url = f"{self.BASE_URL}cards/{card_id}/customField/{custom_id}/item"
            params = self.auth_params

            if "is_open" in kwargs:
                checked = "false" if kwargs["is_open"] == "true" else "true"
                payload = {"value": {"checked": checked}}

            elif "date" in kwargs:
                payload = {"value": {"date": kwargs["date"]}}

            else:
                raise ValueError(
                    "Invalid custom field type. Expected 'is_open' or 'date'."
                )

            response = self.reqs.make_request("PUT", url, params=params, json=payload)

            if response:
                logging.info(
                    "Custom field on card %s updated to %s.",
                    card_id,
                    payload,
                )
            else:
                logging.error(
                    "Failed to update custom field '%s' on card %s with: %s.",
                    custom_id,
                    card_id,
                    payload,
                )
        except (KeyError, TypeError, ValueError) as e:
            logging.error(
                "Error updating custom field '%s' on card %s: %s",
                custom_id,
                card_id,
                str(e),
                exc_info=True,
            )


# pylint: disable=too-few-public-methods
class Helpers:
    """
    Hjelpe-funksjoner for å håndtere S3 og lister.
    """

    # Class-level cache for token to avoid repeated S3 calls
    _token_cache = None
    _token_cache_time = None
    _TOKEN_CACHE_TTL = 300  # Cache token for 5 minutes

    def __init__(self):
        self.session = boto3.session.Session()
        self.reqs = RequestsManager()
        self.client = self.session.client(
            "s3",
            region_name=Config.SPACE_REGION,
            endpoint_url=Config.SPACE_ENDPOINT,
            aws_access_key_id=Config.SPACE_KEY,
            aws_secret_access_key=Config.SPACE_SECRET,
        )

    def get_s3_file(self, space_bucket, space_key):
        """Retrieves a file from an S3 bucket."""
        try:
            response = self.client.get_object(Bucket=space_bucket, Key=space_key)
            content = response["Body"].read()
            return content
        except boto_exceptions.UnknownKeyError:
            return {"body": ""}
        except boto_exceptions.ClientError as e:
            return {"error": str(e)}

    def build_url(self, url: str) -> str:
        """
        Bygger en URL som inkluderer en dato for de siste X dagene.

        Args:
            url (str): URL-en som skal få dato.
        """

        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        last = today - timedelta(days=7)
        start = last.strftime("%Y-%m-%dT00:00:00Z")
        end = (today + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        date_range = f"{start}  TO  {end}"
        encoded_date_range = quote(date_range, safe="")

        return re.sub(r"%5B%5D", f"%5B{encoded_date_range}%5D", url, count=1)

    def get_legacy_list(self, url):
        """Retrieves a list of articles from the CUE lists of a group."""
        auth = self.get_token()
        headers = {"Authorization": f"{auth}"}
        response = self.reqs.make_request("GET", url, headers=headers, timeout=10)
        if response is None:
            logging.error("Failed to fetch data from %s", url)
            return []
        # Check if response is a Response object (not already parsed)
        if hasattr(response, "text"):
            response_text = response.text
        else:
            response_text = str(response)
        # Use pre-compiled regex for better performance
        matches = list(
            set(match.group(1) for match in RE_LEGACY_ID.finditer(response_text))
        )
        logging.debug("GET_LIST: From %s List: %s", url, matches)
        return matches

    def get_lists(self, lists):
        """
        Henter ut en liste med Cue-ID fra en gitt URL.
        Args:
            lists (str): URL-ene som det skal hentes fra.
        """

        try:
            auth = self.get_token()
            headers = {"Authorization": f"{auth}"}

            matches = []
            for url in lists:
                try:
                    _url = self.build_url(url)
                    response = self.reqs.make_request(
                        "GET", _url, headers=headers, timeout=10
                    )

                    if response is None:
                        logging.error("Failed to fetch data from %s", _url)
                        continue

                    # Handle both Response objects and parsed JSON data
                    if hasattr(response, "status_code"):
                        # It's a Response object
                        if response.status_code != 200:
                            logging.error(
                                "Request to %s failed with status code %s: %s",
                                _url,
                                response.status_code,
                                response.text,
                            )
                            continue
                        response_text = response.text
                    else:
                        # It's already parsed data (dict), convert back to text for regex
                        response_text = str(response)

                    # Use pre-compiled regex for better performance
                    matched = list(
                        set(
                            match.group(1)
                            for match in RE_URN_ID.finditer(response_text)
                        )
                    )
                    logging.debug("GET_LIST: From %s List: %s", url, matched)
                    matches.extend(matched)

                except (
                    req_exceptions.RequestException,
                    re.error,
                    KeyError,
                    TypeError,
                ) as e:
                    logging.error("Request to %s failed: %s", url, e)

            counts = Counter(matches)
            unique = [item for item, count in counts.items() if count == 1]
            logging.debug("FETCHED: %s", unique)
            return unique
        except (boto_exceptions.BotoCoreError, boto_exceptions.ClientError) as e:
            logging.error(
                "GET_LISTS: An error occurred while fetching lists: %s", str(e)
            )
            return []

    async def searcher(self):
        """Søker etter publiserte saker."""

        url = Config.PUBLISHED_OPEN
        print(url)

        if url is None:
            logging.error("PUBLISHED_OPEN URL is not set.")
            return

        response = self.reqs.make_request("GET", url)

        if not response:
            logging.error("Klarte ikke å hente artikler.")
            return

        data = {}

        if hasattr(response, "json"):
            try:
                data = response.json()
            except ValueError:
                logging.error("Failed to parse JSON response")
                return
        elif isinstance(response, dict):
            data = response
        else:
            logging.error("Invalid response type:")
            return

        slugs = [
            item["metadata"]["slug"]
            for item in data.get("results", [])
            if "metadata" in item and "slug" in item["metadata"]
        ]

        # Use pre-compiled regex for better performance
        ids = [
            match.group(1) for slug in slugs if (match := RE_SLUG_ID.search(slug))
        ]
        logging.debug("SEARCHER: Fant %s", ids)
        return ids

    def get_token(self):
        """
        Henter ut en fil fra S3-bucket.
        Bruker get_s3_file for å hente filen.
        Uses caching to avoid repeated S3 calls within the TTL period.
        """
        # Check if we have a valid cached token
        current_time = time.time()
        if (
            Helpers._token_cache is not None
            and Helpers._token_cache_time is not None
            and (current_time - Helpers._token_cache_time) < Helpers._TOKEN_CACHE_TTL
        ):
            logging.debug("GET_TOKEN: Using cached token")
            return Helpers._token_cache

        response = Helpers.get_s3_file(self, Config.SPACE_BUCKET, Config.SPACE_PATH)
        if isinstance(response, dict):
            if "error" in response:
                logging.error("Error fetching token: %s", response["error"])
                return None
            if "body" in response:
                content_str = response["body"]
            else:
                logging.error("Unexpected response format: %s", response)
                return None
        else:
            content_str = response.decode("utf-8")

        try:
            data = json.loads(content_str)
            token = data.get("cf.escenic.credentials", None)
            # Cache the token
            Helpers._token_cache = token
            Helpers._token_cache_time = current_time
            logging.debug("GET_TOKEN: Token fetched and cached: %s", token)
            return token
        except json.JSONDecodeError as e:
            logging.error("Error parsing token JSON: %s", e)
            return None

    @staticmethod
    def get_custom_fields(card):
        """
        Henter ut custom fields fra et Trello-kort.
        Args:
            card (dict): Trello-kortets ID.
        """

        return {
            f.get("idCustomField"): f.get("value", {})
            for f in card.get("customFieldItems", [])
        }

    @staticmethod
    def compare_lists(x: List[Any], y: List[Any]) -> List[Any]:
        """
        Sammenligner lister og returnerer elementer i
        den første listen som ikke finnes i den andre.
        Args:
            x (List[Any]): Første liste.
            y (List[Any]): Andre liste.
        Returns:
            List[Any]: Elementer i den første listen som ikke finnes i den andre.
        """

        if x is None or y is None:
            raise ValueError("Both input lists must be provided and cannot be None")

        try:
            set1, set2 = set(x), set(y)
        except TypeError as e:
            raise TypeError(
                f"Elements must be hashable to use set comparison: {e}"
            ) from e
        result = list(set1 - set2)
        logging.debug("COMPARE_LISTS: %s", result)
        return result

    @staticmethod
    def extract_article_info(article: dict) -> ArticleInfo:
        """
        Mottar artikkelen og henter ut informasjon.
        """

        card_id = article.get("article", "")
        title = article.get("title", "Ukjent tittel")
        author = article.get("forfatter", "Ukjent forfatter")
        character_count = article.get("character_count", "")
        image_count = article.get("image_count", "")
        overskrift = f"{title} ({author})"
        overskrift_lang = f"{overskrift} [TEGN: {character_count} IMG: {image_count}]"
        mal = article.get("model_last_word", "")
        sist_endret = article.get("lastModified", "").replace("+0000", "Z")
        friflyt = article.get("friflyt", "")
        pluss = article.get("is_open", "")
        oppsummering = article.get("oppsummering", "")
        status = article.get("status", "")
        publish_time = article.get("publish_time", "")

        is_state = Config.STATES.get(status, None)
        is_form = Config.CARD_FORM.get(mal, None)

        is_state_papir = Config.STATES_PAPIR.get(status, None)
        is_form_papir = Config.CARD_FORM_PAPIR.get(mal, None)

        return ArticleInfo(
            card_id,
            overskrift,
            overskrift_lang,
            mal,
            sist_endret,
            friflyt,
            pluss,
            oppsummering,
            status,
            publish_time,
            is_state,
            is_form,
            is_state_papir,
            is_form_papir,
        )


class GetArticleDetails:
    """
    Henter ut informasjon om den enkelte artikkelen.
    """

    def __init__(self):
        self.reqs = RequestsManager()

    async def get_article(
        self, article: str, cue_open_search: str, avis: str, results: list
    ):
        """Henter artiklene fra CUE"""
        url = f"{cue_open_search}{avis}{article}"
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None, self.reqs.make_request, "GET", url
            )

            if response is None:
                results.append({"article": article, "error": "Request failed"})
                return

            if isinstance(response, requests.Response):
                data = response.text
            elif isinstance(response, str):
                data = response
            else:
                results.append(
                    {
                        "article": article,
                        "error": f"Unexpected response type: {type(response)}",
                    }
                )
                return

            def find_value(tag_name: str) -> str:
                """Finds a value in the XML data."""
                match = re.search(
                    rf'<vdf:field name="{tag_name}">'
                    rf"<vdf:value>(.*?)</vdf:value>"
                    rf"</vdf:field>",
                    data,
                )
                return match.group(1) if match else ""

            def ext_regex(pattern: str) -> str:
                """Extracts a value using a regular expression pattern."""
                match = re.search(pattern, data)
                return match.group(1) if match else ""

            def count_chars() -> int:
                """Counts the number of characters in the article."""
                # Use pre-compiled regex for better performance
                paragraphs = RE_PARAGRAPH.findall(data)
                return sum(len(p) for p in paragraphs)

            extracted_data = {
                "article": article,
                "title": find_value("title"),
                "forfatter": ext_regex(r"<author>\s*<name>(.*?)</name>"),
                "model_last_word": ext_regex(r'<vdf:payload[^>]+model="[^"]+/(\w+)"'),
                "lastModified": find_value("lastModifiedDate"),
                "friflyt": find_value("noFreeFlow"),
                "is_open": find_value("isPremium"),
                "oppsummering": ext_regex(r'<summary type="text">(.*?)</summary>'),
                "status": ext_regex(r'<vaext:state name="(.*?)"/>'),
                "publish_time": ext_regex(r"<published>(.*?)</published>"),
                "character_count": count_chars(),
                # Use pre-compiled regex for better performance
                "image_count": len(RE_IMG_SRC.findall(data)),
            }
            logging.debug("GETARTICLE: Fetched: %s", extracted_data)
            return extracted_data
        except (
            req_exceptions.RequestException,
            req_exceptions.Timeout,
            req_exceptions.ConnectionError,
            req_exceptions.HTTPError,
        ) as e:
            logging.error("Request error: %s", str(e))
        except re.error as e:
            logging.error("Regex error: %s", str(e))
        except (TypeError, AttributeError) as e:
            logging.error("Unexpected error: %s", str(e))

    async def get_articles(self, articles, avis):
        """Main function to fetch article details."""
        cue_open_search = os.getenv("CUE_OPEN_SEARCH")

        if isinstance(articles, str):
            articles = [articles]

        if not cue_open_search or not avis:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json; charset=utf-8"},
                "body": json.dumps(
                    {"error": "Missing required parameter"}, ensure_ascii=False
                ),
            }

        results = []
        results = await asyncio.gather(
            *(
                self.get_article(article, cue_open_search, avis, results)
                for article in articles
            )
        )
        return results
