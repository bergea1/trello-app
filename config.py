"""
Logging og variabler.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv  # pylint: disable=import-error

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """
    Config.
    """

    @staticmethod
    def str_to_bool(value):
        """Convert string to boolean."""
        return value.lower() in {"true", "1", "yes", "on"}

    ## GENERAL VARIABLES
    APP_NAME = os.getenv("APP_NAME", "")
    APP_VERSION = os.getenv("APP_VERSION", "")
    RUN_NETT = str_to_bool(os.getenv("RUN_NETT", "True"))
    RUN_PAPIR = str_to_bool(os.getenv("RUN_PAPIR", "False"))
    MODE = os.getenv("MODE", "dev")

    ## BUCKET VARIABLES
    SPACE_BUCKET = os.getenv("SPACE_BUCKET")
    SPACE_REGION = os.getenv("SPACE_REGION")
    SPACE_KEY = os.getenv("SPACE_KEY")
    SPACE_SECRET = os.getenv("SPACE_SECRET")
    SPACE_PATH = os.getenv("SPACE_PATH")
    SPACE_ENDPOINT = os.getenv("SPACE_ENDPOINT")

    ## TRELLO API VARIABLES
    BASE_URL = os.getenv("BASE_URL")
    BASE_URL_CARDS = os.getenv("BASE_URL_CARDS")
    IS_ONLINE = os.getenv("IS_ONLINE")
    API_KEY = os.getenv("API_KEY")
    API_TOKEN = os.getenv("API_TOKEN")

    ## TRELLO ID VARIABLES
    NETT_BOARD = os.getenv("NETT_BOARD")
    PAPIR_BOARD = os.getenv("PAPIR_BOARD")
    NETT_IARBEID = os.getenv("NETT_IARBEID")
    PAPIR_INNBOKS = os.getenv("PAPIR_INNBOKS")

    ## CUE URL VARIABLES
    CUE_OPEN_SEARCH = os.getenv("CUE_OPEN_SEARCH")
    IARBEID_URL = os.getenv("IARBEID_URL")
    LEVERT_URL = os.getenv("LEVERT_URL")
    GODKJENT_URL = os.getenv("GODKJENT_URL")
    PUBLISERT_URL = os.getenv("PUBLISERT_URL")
    PUBLISHED_OPEN = os.getenv("PUBLISHED_OPEN")
    AVIS = os.getenv("AVIS")

    ### TRELLO NETT STATE LABELS
    PUBLISHED_LABEL = os.getenv("PUBLISHED_LABEL")
    SUBMITTED_LABEL = os.getenv("SUBMITTED_LABEL")
    APPROVED_LABEL = os.getenv("APPROVED_LABEL")
    SCHEDULED_LABEL = os.getenv("SCHEDULED_LABEL")
    DRAFT_LABEL = os.getenv("DRAFT_LABEL")

    ### TRELLO NETT TYPE LABELS
    ANMELDELSE_LABEL = os.getenv("ANMELDELSE_LABEL")
    FEATURE_LABEL = os.getenv("FEATURE_LABEL")
    DEBATT_LABEL = os.getenv("DEBATT_LABEL")
    BILDESERIE_LABEL = os.getenv("BILDESERIE_LABEL")
    NYHET_LABEL = os.getenv("NYHET_LABEL")
    VIDEO_LABEL = os.getenv("VIDEO_LABEL")

    ### TRELLO PAPIR STATE LABELS
    APPROVED_LABEL_PAPIR = os.getenv("APPROVED_LABEL_PAPIR")
    PUBLISHED_LABEL_PAPIR = os.getenv("PUBLISHED_LABEL_PAPIR")
    SUBMITTED_LABEL_PAPIR = os.getenv("SUBMITTED_LABEL_PAPIR")
    DRAFT_LABEL_PAPIR = os.getenv("DRAFT_LABEL_PAPIR")

    ### TRELLO PAPIR TYPE LABELS
    ANMELDELSE_LABEL_PAPIR = os.getenv("ANMELDELSE_LABEL_PAPIR")
    FEATURE_LABEL_PAPIR = os.getenv("FEATURE_LABEL_PAPIR")
    DEBATT_LABEL_PAPIR = os.getenv("DEBATT_LABEL_PAPIR")
    BILDESERIE_LABEL_PAPIR = os.getenv("BILDESERIE_LABEL_PAPIR")
    NYHET_LABEL_PAPIR = os.getenv("NYHET_LABEL_PAPIR")

    ### TRELLO CUSTOM LABELS
    CUSTOM_PAPIR = os.getenv("CUSTOM_PAPIR")
    CUSTOM_NETT = os.getenv("CUSTOM_NETT")
    CUSTOM_LAST_NETT = os.getenv("CUSTOM_LAST_NETT")
    CUSTOM_PUB_NETT = os.getenv("CUSTOM_PUB_NETT")
    CUSTOM_PUB_PAPIR = os.getenv("CUSTOM_PUB_PAPIR")
    CUSTOM_OPEN_NETT = os.getenv("CUSTOM_OPEN_NETT")

    ### MAPPINGS

    INIT_CONF = {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
        "MODE": MODE,
        "RUN_NETT": RUN_NETT,
        "RUN_PAPIR": RUN_PAPIR,
    }
    NETT = {
        "get_lists": {
            "IARBEID": IARBEID_URL,
            "LEVERT": LEVERT_URL,
            "GODKJENT": GODKJENT_URL,
            "PUBLISERT": PUBLISERT_URL,
        },
        "board": NETT_BOARD,
        "innboks": NETT_IARBEID,
    }

    PAPIR = {
        "get_lists": {
            "LEVERT": LEVERT_URL,
            "GODKJENT": GODKJENT_URL,
            "PUBLISERT": PUBLISERT_URL,
        },
        "board": PAPIR_BOARD,
        "innboks": PAPIR_INNBOKS,
    }

    MODES = {
        "nett": NETT,
        "papir": PAPIR,
    }

    FIELD_MAP = {
        "nett": {
            "name_attr": "overskrift",
            "cue-id": CUSTOM_NETT,
        },
        "papir": {
            "name_attr": "overskrift_lang",
            "cue-id": CUSTOM_PAPIR,
        },
    }

    STATES = {
        "published": PUBLISHED_LABEL,
        "draft-published": PUBLISHED_LABEL,
        "draft-submitted": SUBMITTED_LABEL,
        "draft-approved": APPROVED_LABEL,
        "submitted": SUBMITTED_LABEL,
        "approved": APPROVED_LABEL,
        "scheduled": SCHEDULED_LABEL,
        "draft": DRAFT_LABEL,
    }

    CARD_FORM = {
        "review": ANMELDELSE_LABEL,
        "story": NYHET_LABEL,
        "opinion": DEBATT_LABEL,
        "feature": FEATURE_LABEL,
        "gallery": BILDESERIE_LABEL,
        "video": VIDEO_LABEL,
    }

    STATES_PAPIR = {
        "published": PUBLISHED_LABEL_PAPIR,
        "draft-published": PUBLISHED_LABEL_PAPIR,
        "draft-submitted": APPROVED_LABEL_PAPIR,
        "draft-approved": APPROVED_LABEL_PAPIR,
        "submitted": SUBMITTED_LABEL_PAPIR,
        "approved": APPROVED_LABEL_PAPIR,
        "scheduled": PUBLISHED_LABEL_PAPIR,
        "draft": DRAFT_LABEL_PAPIR,
    }

    CARD_FORM_PAPIR = {
        "review": ANMELDELSE_LABEL_PAPIR,
        "story": NYHET_LABEL_PAPIR,
        "opinion": DEBATT_LABEL_PAPIR,
        "feature": FEATURE_LABEL_PAPIR,
        "gallery": BILDESERIE_LABEL_PAPIR,
    }

    ### LOGGING CONFIGURATION
    LOG_FILE = "./logs/app.log"
    LOG_LEVEL_LOG = logging.DEBUG
    LOG_LEVEL_STDOUT = logging.INFO
    MAX_LOG_SIZE = 5 * 1024 * 1024
    BACKUP_COUNT = 5

    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL_LOG)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(LOG_LEVEL_STDOUT)
    stdout_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT
    )
    file_handler.setLevel(LOG_LEVEL_LOG)
    file_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)
