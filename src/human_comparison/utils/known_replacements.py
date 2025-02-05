from typing import Dict, List


class KnownReplacements:
    """Container for known typos and bots in contest reports"""

    # Known typo errors in reports
    known_typos: Dict[str, Dict[str, str]] = {"2022-11-size": {"_141345_": "__141345__"}}

    # Known bots in reports. Bots are not mention in the Wardens list in the report
    # but are mentioned in the issues if they are only found by the bot
    # Bot entries are in the format "bot-<bot_name>"
    known_bots: Dict[str, List[str]] = {"2023-10-wildcat": ["henry"], "2023-08-dopex": ["IllIllI"]}

    @classmethod
    def get_typos(cls, repo_name: str) -> Dict[str, str]:
        return cls.known_typos.get(repo_name, {})

    @classmethod
    def get_bots(cls, repo_name: str) -> List[str]:
        return cls.known_bots.get(repo_name, [])
