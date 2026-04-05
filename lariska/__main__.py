from dotenv import load_dotenv

from trello.client import TrelloClient
from trello.notifications import fetch_member_notifications


def main() -> None:
    load_dotenv()
    with TrelloClient() as client:
        notes = fetch_member_notifications(client, read_filter="unread")
        import pprint
        pprint.pprint(notes)
        print(notes)
    


if __name__ == "__main__":
    main()
