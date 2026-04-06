import logging

from dotenv import load_dotenv

from lariska.trello.client import TrelloClient
from lariska.workflow import run_iteration

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    load_dotenv()
    with TrelloClient() as client:
        run_iteration(client)


if __name__ == "__main__":
    main()
