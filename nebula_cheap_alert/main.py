import os
import sys
import json
import datetime
import requests
import pandas as pd
from time import sleep
from dotenv import load_dotenv
from iconsdk.icon_service import IconService
from iconsdk.providers.http_provider import HTTPProvider
from iconsdk.builder.call_builder import CallBuilder
from discord_webhook import DiscordWebhook, DiscordEmbed

# load env variables
is_heroku = os.getenv("IS_HEROKU", None)
if not is_heroku:
    load_dotenv()

discord_webhook = os.getenv("DISCORD_SPECIALS_WEBHOOK")

# Project Nebula contract
NebulaPlanetTokenCx = "cx57d7acf8b5114b787ecdd99ca460c2272e4d9135"

# connect to ICON main-net
icon_service = IconService(HTTPProvider("https://ctz.solidwallet.io", 3))

# function for making a call
def call(to, method, params):
    call = CallBuilder().to(to).method(method).params(params).build()
    result = icon_service.call(call)
    return result


# main loop
while True:
    tokenList = []

    try:
        # how many planets currently listed on the marketplace
        try:
            total_listed_token_count = int(call(NebulaPlanetTokenCx, "total_listed_token_count", {}), 16)
        except:
            print("total_listed_token_count cannot be retrieved..")
            continue

        # loop through each planet on the marketplace
        for indexId in range(1, total_listed_token_count + 1):
            # for given indexId - retrieve corresponding tokenId
            try:
                tokenId = int(call(NebulaPlanetTokenCx, "get_listed_token_by_index", {"_index": indexId}), 16)
            except:
                print("tokenId for given indexId cannot be retrieved..")
                continue

            # pull planet details
            response_content = requests.get(call(NebulaPlanetTokenCx, "tokenURI", {"_tokenId": tokenId})).text
            planetInfo = json.loads(response_content)
            name = str(planetInfo["name"])
            generation = str(planetInfo["generation"])
            rarity = str(planetInfo["rarity"])
            external_link = planetInfo["external_link"]
            
            # loop to check special resources
            for special in planetInfo["specials"]: 
                planet_special = str(special["name"])

                try:
                    set_price = int(call(NebulaPlanetTokenCx, "get_token_price", {"_tokenId": tokenId}), 16)
                except:
                    print("set_price cannot be retrieved..")
                    continue
                
                # get set price/auction listings
                if set_price != -1:
                    buy_type = "set price"
                    price = set_price / 10 ** 18
                    end_time_timestamp = ""
                else:
                    buy_type = "auction"

                    try:
                        auction_info = call(NebulaPlanetTokenCx, "get_auction_info", {"_token_id": tokenId})
                    except:
                        print("auction_info cannot be retrieved..")
                        continue
                    
                    if "Token is not on auction" not in auction_info:
                        price = int(auction_info["current_bid"], 16) / 10 ** 18
                        if price == 0:
                            price = int(auction_info["starting_price"], 16) / 10 ** 18
                        end_time_timestamp = str(int(auction_info["end_time"], 16) / 1000000) + "hrs"
                        #end_time = datetime.datetime.fromtimestamp(end_time_timestamp).strftime('%Y-%m-%d %H:%M:%S')

                # build description line for each planet/special pair
                description = "[**" + name.upper() + "**](" + external_link + ")"
                description += "  " + rarity.upper() + "/" + generation.upper()
                description += "  __" + str(price) + "__"

                tokenList.append([planet_special, description, buy_type, price, end_time_timestamp])

        # convert list to dataframe
        df = pd.DataFrame(tokenList).drop_duplicates()
        df.columns = ["special", "description", "buy_type", "price", "end_time"]

        # for debugging to run pull-push separately
        #df.to_csv("planets.csv", header=True, index=False)
        #df = pd.read_csv("planets.csv")

        # loop through each special resource currently available
        for special in sorted(df["special"].unique()):
            # list of buy types with corresponding colors
            buy_types = [
                ["auction", "F4D03F"],  #yellow
                ["set price", "FDFEFE"] #white
            ]

            for buy_type, color in buy_types:
                # filter to given special resource and buy type and then find top 3 cheapest options
                df_filtered = df.query("special == '" + special + "' and buy_type == '" + buy_type + "'")
                df_filtered = df_filtered.sort_values(by=["price"], ascending=True).head(3)
                
                # convert dataframe to string and justify it to the left
                info_list = df_filtered.to_string(
                    columns=["description"],
                    formatters={"description":"{{:<{}s}}".format(df_filtered["description"].str.len().max()).format},
                    index=False,
                    header=False
                ).split("\n")

                info = ""
                for l in info_list:
                    info += "\n" + str(l).strip() + " "

                # skip if there's no data
                if "Empty DataFrame" in info:
                    continue

                # generate discord alert
                if len(info) > 0:
                    webhook = DiscordWebhook(url=discord_webhook)
                    embed = DiscordEmbed(title=special + " - *" + buy_type + "*", description=info, color=color)
                    webhook.add_embed(embed)
                    response = webhook.execute()
                
                # wait before sending next one to avoid blocking by discord / over-flooding users with too many alerts all at once
                sleep(20)
    except:
        print("Error: {}. {}, line: {}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2].tb_lineno))
        continue
    
    # wait for an hour before starting again
    sleep(3600)
