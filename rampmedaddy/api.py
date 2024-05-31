from decimal import Decimal
from typing import Union
import requests

from django.conf import settings

from ninja import NinjaAPI, Schema
from stellar_sdk import Asset, Keypair, Network, Server, TransactionBuilder
from stellar_sdk.exceptions import NotFoundError, BadResponseError, BadRequestError

api = NinjaAPI()


class MakePaymentSchema(Schema):
    destination: str
    amount: Union[str, Decimal]


@api.post("/payment")
def hello(request, data: MakePaymentSchema):
    server = Server("https://horizon-testnet.stellar.org")
    source_key = Keypair.from_secret("SCJZNG6PS6GN65ZE552HKDTMY2TO3ILFIYFZZY5DBOZENJOIU25JMEZW")
    destination_id = settings.SOURCE_KEY if not data.destination \
        else data.destination

    print(' settings.SOURCE_KEY',  settings.SOURCE_KEY)
    print("destination_id", destination_id)
    print("DESTINATION", data.destination)
    # First, check to make sure that the destination account exists.
    # You could skip this, but if the account does not exist, you will be charged
    # the transaction fee when the transaction fails.
    try:
        server.load_account(destination_id)
    except NotFoundError:
        # If the account is not found, surface an error message for logging.
        raise Exception("The destination account does not exist!")

    # If there was no error, load up-to-date information on your account.
    source_account = server.load_account(source_key.public_key)

    price = Decimal(get_stellar_per_euro())
    print('Price', price)
    quantity = round(Decimal(data.amount) * price, 5)
    print("quantity", quantity)
    print(get_stellar_per_euro())

    # Let's fetch base_fee from network
    base_fee = server.fetch_base_fee()

    # Start building the transaction.
    transaction = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
            base_fee=base_fee,
        )
        # Because Stellar allows transaction in many currencies, you must specify the asset type.
        # Here we are sending Lumens.
        .append_payment_op(destination=destination_id, asset=Asset.native(), amount=quantity)
        # A memo allows you to add your own metadata to a transaction. It's
        # optional and does not affect how Stellar treats the transaction.
        .add_text_memo("Test Transaction")
        # Wait a maximum of three minutes for the transaction
        .set_timeout(300)
        .build()
    )

    # Sign the transaction to prove you are actually the person sending it.
    transaction.sign(source_key)

    response = None
    try:
        # And finally, send it off to Stellar!
        response = server.submit_transaction(transaction)
        print(f"Response: {response}")
    except (BadRequestError, BadResponseError) as err:
        print(f"Something went wrong!\n{err}")
    if response:
        return response
    else:
        '{"success": false}'


def get_stellar_per_euro():
    url = "https://api.coingecko.com/api/v3/simple/price"
    parameters = {
        "ids": "stellar",
        "vs_currencies": "eur",
    }

    response = requests.get(url, params=parameters)

    if response.status_code == 200:
        data = response.json()
        price_eur = data['stellar']['eur']
        stellar_per_eur = 1 / price_eur
        print(f"One euro is equivalent to {stellar_per_eur} XLM.")
        return round(stellar_per_eur, 5)
    else:
        return 9.5
