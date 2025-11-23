"""
Henter artikler fra CUE og lage kort i Trello.
"""

# pylint: disable=E1101
# pylint: disable=import-error

import json
import logging

from dotenv import load_dotenv

from config import Config
from utility import GetArticleDetails, Helpers, RequestsManager, TrelloManager

load_dotenv()


class Engine:
    """
    Class for å hente artikler fra CUE og lage kort i Trello.

    Funksjoner:
        check_for_new: Sjekker om det er nye artikler i CUE som ikke er i Trello.
        check_for_changes: Sjekker om det er endringer i Trello-kort i forhold til CUE.
        create_card: Oppretter Trello-kort for nye artikler.
        extract_info: Oppdaterer Trello-kort med ny informasjon fra CUE.
    """

    logging.info("Starter app..")

    def __init__(self):
        self.reqs = RequestsManager()
        self.gets = GetArticleDetails()
        self.trello = TrelloManager()
        self.help = Helpers()
        self.config = Config()

        self.NETT_BOARD = self.config.NETT_BOARD
        self.PAPIR_BOARD = self.config.PAPIR_BOARD
        self.AVIS = self.config.AVIS
        self.SUBMITTED_LABEL = self.config.SUBMITTED_LABEL
        self.APPROVED_LABEL = self.config.APPROVED_LABEL
        self.PUBLISHED_LABEL = self.config.PUBLISHED_LABEL
        self.PAPIR_INNBOKS = self.config.PAPIR_INNBOKS
        self.NETT_IARBEID = self.config.NETT_IARBEID
        self.IARBEID_URL = self.config.IARBEID_URL
        self.LEVERT_URL = self.config.LEVERT_URL
        self.GODKJENT_URL = self.config.GODKJENT_URL
        self.PUBLISERT_URL = self.config.PUBLISERT_URL
        self.CUSTOM_NETT = self.config.CUSTOM_NETT
        self.CUSTOM_PAPIR = self.config.CUSTOM_PAPIR
        self.CUSTOM_LAST_NETT = self.config.CUSTOM_LAST_NETT
        self.CUSTOM_PUB_NETT = self.config.CUSTOM_PUB_NETT
        self.CUSTOM_PUB_PAPIR = self.config.CUSTOM_PUB_PAPIR
        self.CUSTOM_OPEN_NETT = self.config.CUSTOM_OPEN_NETT
        self.INCLUDE_CHANGE = self.config.INCLUDE_CHANGE
        self.INCLUDE_GODKJENT_URL = self.config.INCLUDE_GODKJENT_URL
        self.INCLUDE_PUBLISERT_URL = self.config.INCLUDE_PUBLISERT_URL
        self.INCLUDE_LEVERT_URL_PAPIR = self.config.INCLUDE_LEVERT_URL_PAPIR
        self.INCLUDE_GODKJENT_URL_PAPIR = self.config.INCLUDE_GODKJENT_URL_PAPIR
        self.INCLUDE_PUBLISERT_URL_PAPIR = self.config.INCLUDE_PUBLISERT_URL_PAPIR

        self.MODES = self.config.MODES
        self.FIELD_MAP = self.config.FIELD_MAP
        self.NETT = self.config.NETT
        self.PAPIR = self.config.PAPIR

    async def check_for_new(self, mode: str = "nett") -> None:
        """
        Sjekker om det er nye artikler i CUE som ikke er i nettplan.
        Henter artikler fra CUE som har status: kladd, levert og godkjent.
        """

        if mode not in self.MODES:
            logging.error("Ugyldig mode: %s", mode)
            return

        logging.info("%s: Ser etter nye artikler", mode.upper())

        try:
            cfg = self.MODES[mode]
            board = cfg["board"]
            innboks = cfg["innboks"]
            lists = []

            if mode == "nett":
                if not self.INCLUDE_GODKJENT_URL and not self.INCLUDE_PUBLISERT_URL:
                    for url in cfg.get("get_lists", {}).values():
                        legacy_list = self.help.get_legacy_list(url)
                        if legacy_list:
                            lists.extend(legacy_list)
                else:
                    lists = self.help.get_lists(cfg.get("get_lists", {}).values())

                if lists is None:
                    logging.error(
                        "%s Error: Klarte ikke å hente artikler fra Cue.", mode.upper()
                    )
                    return

            elif mode == "papir":
                lists = self.help.get_lists(cfg.get("get_lists", {}).values())

                if lists is None:
                    logging.error(
                        "%s Error: Klarte ikke å hente artikler fra Cue.", mode.upper()
                    )
                    return

            plan = self.trello.get_cards(
                board,
                sort=True,
                fields="fields=id",
                customFieldItems="customFieldItems=true",
            )

            if not plan or not isinstance(plan, list):
                logging.error(
                    "%s Error: Failed to fetch Trello board order.",
                    mode.upper(),
                )
                return

            logging.debug(
                "%s: Hentet %d kort fra Trello-brett: %s",
                mode.upper(),
                len(plan),
                board,
            )

            new_articles = self.help.compare_lists(lists, plan)

            logging.info(
                "%s: Antall nye artikler funnet: %d", mode.upper(), len(new_articles)
            )

            await self.create_card(new_articles, innboks)

        except (KeyError, AttributeError, TypeError, ValueError) as e:
            logging.error(
                "Unexpected error in check_for_new: %s", str(e), exc_info=True
            )
            return

    async def create_card(self, cards, innboks):
        """
        Oppretter Trello-kort for nye artikler.
        Args:
            cards: Liste over artikler som mangler i Trello.
            innboks: Trello List ID.
        """

        try:
            new_articles = await self.gets.get_articles(articles=cards, avis=self.AVIS)

            logging.debug(
                "Antall nye artikler funnet: %d",
                len(new_articles) if isinstance(cards, list) else 0,
            )

            articles = new_articles if isinstance(cards, list) else []
        except (TypeError, ValueError) as e:
            logging.error(
                "Error: Failed to process articles due to type or value issue: %s",
                str(e),
            )
            articles = []

        for article in articles:
            try:
                if not isinstance(article, dict):
                    logging.warning(
                        "Skipping article: expected dict, got %s", type(article)
                    )
                    continue

                info = Helpers.extract_article_info(article)

                create_card = self.trello.create_card(
                    innboks,
                    name=info.overskrift,
                    desc=info.card_id,
                    idlabels=[info.is_form],
                )

                if not create_card:
                    logging.error("Error: Failed to create Trello card for article ")
            except (TypeError, ValueError) as e:
                logging.error(
                    "Error creating Trello card for article: %s", str(e), exc_info=True
                )
                return None

    async def check_for_changes(self, argument):
        """
        Ser etter endringer i Trello-kort i forhold til CUE.
        Args:
            argument: "nett" eller "papir" for å spesifisere hvilken type kort som skal sjekkes.
        """

        if argument not in ("nett", "papir"):
            logging.error(
                "Invalid argument: '%s' (expected 'nett' or 'papir')", argument
            )
            return

        logging.info("%s: Ser etter endringer", argument.upper())

        try:
            dispatch = {
                "nett": lambda: self.trello.get_cards(
                    self.NETT_BOARD,
                    sort=False,
                    fields="fields=name,desc,labels",
                    customFieldItems="customFieldItems=true",
                ),
                "papir": lambda: self.trello.get_cards(
                    self.PAPIR_BOARD,
                    sort=False,
                    fields="fields=name,desc,labels&filter=all",
                    customFieldItems="customFieldItems=true",
                ),
            }
            trello_data = dispatch[argument]()

            if not trello_data:
                logging.error("Error: Failed to retrieve Trello data.")
                return

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logging.error("Error: Failed to fetch Cue data: %s", e)
            return
        await self.extract_info(trello_data, argument)

    async def extract_info(self, trello_data, argument):
        """
        Oppdaterer Trello-kort med informasjon fra Cue.
        Args:
            trello_data: Data fra Trello-kort.
            cue_data: Data fra CUE.
            argument: "nett" eller "papir"
        """

        cfg = self.FIELD_MAP.get(argument)
        if cfg is None:
            logging.error("Invalid argument for field mapping: %s", argument)
            return

        if not self.INCLUDE_GODKJENT_URL and not self.INCLUDE_PUBLISERT_URL:
            cue_data = []
            for url in [self.NETT["get_lists"]["LEVERT"]]:
                legacy_list = self.help.get_legacy_list(url)
                if legacy_list:
                    cue_data.extend(legacy_list)
        else:
            cue_data = self.help.get_lists([self.NETT["get_lists"]["LEVERT"]])

        logging.debug("Argument: %s", argument)

        for card in trello_data:
            try:
                custom_fields = self.help.get_custom_fields(card)
                cue_id = custom_fields.get(cfg["cue-id"], {}).get("text")
                if not cue_id or len(cue_id) != 7:
                    continue

                ##

                card_id = card["id"]
                original_name = card["name"]
                labels = [lbl["id"] for lbl in card.get("labels", [])]
                result = await self.gets.get_articles(articles=cue_id, avis=self.AVIS)
                if not isinstance(result, list) or not result or not result[0]:
                    continue

                info = Helpers.extract_article_info(result[0])

                if info.publish_time and not info.publish_time.strip():
                    continue

                new_name = getattr(info, cfg["name_attr"])
                name_changed = new_name != original_name

                if argument == "nett":
                    logging.info("NETT: Oppdaterer kort: %s", card_id)
                    await self.handle_nett(
                        card_id,
                        cue_data,
                        info,
                        custom_fields,
                        labels,
                        name_changed,
                        cue_id,
                    )
                elif argument == "papir":
                    logging.info("PAPIR: Oppdaterer kort: %s", card_id)
                    self.handle_papir(
                        card_id, info, custom_fields, labels, name_changed
                    )
            except (TypeError, ValueError) as e:
                logging.error(
                    "Error updating card %s: %s", card.get("id"), e, exc_info=True
                )
                continue

    async def handle_nett(
        self, card_id, cue_data, info, custom_fields, labels, name_changed, cue_id
    ):
        """
        Oppdaterer Trello-kort for nettartikler.
        Args:
            card_id: ID for Trello-kortet.
            info: Informasjon om artikkelen.
            custom_fields: Tilpassede felt for kortet.
            labels: Etiketter på kortet.
            name_changed (Bool): Om navnet på kortet er endret.
            cue_id: CUE-ID for artikkelen.
            cue_data: Data fra CUE for sammenligning.
        """

        sist_endret = custom_fields.get(self.CUSTOM_LAST_NETT, {}).get("date")
        checked = custom_fields.get(self.CUSTOM_OPEN_NETT, {}).get("checked")
        publisert = custom_fields.get(self.CUSTOM_PUB_NETT, {}).get("date")
        is_open = "false" if checked == "true" else "true"

        label_tags = (info.is_form, info.is_state)
        label_changed = self.trello.collect_labels(labels, label_tags)
        is_published = self.APPROVED_LABEL in labels or self.PUBLISHED_LABEL in labels

        if (
            cue_id in cue_data
            and self.SUBMITTED_LABEL not in labels
            and not is_published
        ):
            labels.append(self.SUBMITTED_LABEL)
            label_changed = True

        if name_changed or label_changed:
            self.trello.update_card(
                card_id, name=info.overskrift, desc=info.oppsummering, idLabels=labels
            )

        if info.publish_time not in (publisert, ""):
            self.trello.update_custom_card(
                card_id, self.CUSTOM_PUB_NETT, date=info.publish_time
            )
        if self.INCLUDE_CHANGE == "True" and info.sist_endret not in (sist_endret, ""):
            self.trello.update_custom_card(
                card_id, self.CUSTOM_LAST_NETT, date=info.sist_endret
            )
        if info.pluss != is_open:
            self.trello.update_custom_card(
                card_id, self.CUSTOM_OPEN_NETT, is_open=info.pluss
            )

    def handle_papir(self, card_id, info, custom_fields, labels, name_changed):
        """
        Oppdaterer Trello-kort for papirartikler.
        Args:
            card_id: ID for Trello-kortet.
            info: Informasjon om artikkelen.
            custom_fields: Tilpassede felt for kortet.
            labels: Etiketter på kortet.
            name_changed (Bool): Om navnet på kortet er endret.
        """

        publisert = custom_fields.get(self.CUSTOM_PUB_PAPIR, {}).get("date")
        label_tags = (info.is_form_papir, info.is_state_papir)
        label_changed = self.trello.collect_labels(labels, label_tags)

        if name_changed or label_changed:
            self.trello.update_card(
                card_id,
                name=info.overskrift_lang,
                desc=info.oppsummering,
                idLabels=labels,
            )

        if info.publish_time not in (publisert, ""):
            self.trello.update_custom_card(
                card_id, self.CUSTOM_PUB_PAPIR, date=info.publish_time
            )
