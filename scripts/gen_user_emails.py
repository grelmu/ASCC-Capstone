import pyjson5
import argh

TEMPLATE = """
Hi - we've granted you access to the ARP data warehouse at {warehouse_url}.  To login, use the following username/password:

{username}/{password}

Note that currently the warehouse at {warehouse_url} uses a self-signed certificate - this will lead to a browser warning when first accessing the website via https.  On Chrome, click "Advanced" and then click the "Proceed to..." link.

Please be mindful before modifying any information in the warehouse as it is a work-in-progress - Thanks!
"""


def main(
    users_filename: str, warehouse_url: str = "https://storinator-2.aewc.umaine.edu"
):

    users = None
    with open(users_filename, "r") as f:
        users = pyjson5.load(f)

    for user in users:

        username = user["username"]
        password = user["password"]

        user_filename = f"./{username}.txt"

        content = str.format(
            TEMPLATE, warehouse_url=warehouse_url, username=username, password=password
        )

        with open(user_filename, "w") as f:
            f.write(content)


if __name__ == "__main__":
    argh.dispatch_command(main)
