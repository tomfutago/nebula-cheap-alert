import os
import re
import sys
import json
import requests
import pandas as pd
from time import sleep
from dotenv import load_dotenv
from datetime import datetime
from pandas.core.frame import DataFrame
from iconsdk.icon_service import IconService
from iconsdk.providers.http_provider import HTTPProvider
from iconsdk.builder.call_builder import CallBuilder
from discord_webhook import DiscordWebhook, DiscordEmbed

import pn_token

# load env variables
is_heroku = os.getenv("IS_HEROKU", None)
if not is_heroku:
    load_dotenv()

discord_webhook_income = os.getenv("DISCORD_WEBHOOK_INCOME")
discord_webhook_slots = os.getenv("DISCORD_WEBHOOK_SLOTS")
discord_webhook_collectibles = os.getenv("DISCORD_WEBHOOK_COLLECTIBLES")
discord_webhook_rarity = os.getenv("DISCORD_WEBHOOK_RARITY")
discord_webhook_specials = os.getenv("DISCORD_WEBHOOK_SPECIALS")
discord_webhook_bargains = os.getenv("DISCORD_WEBHOOK_BARGAINS")
discord_webhook_ship_type = os.getenv("DISCORD_WEBHOOK_SHIP_TYPE")
discord_webhook_log = os.getenv("DISCORD_LOG_WEBHOOK")

# Project Nebula contracts
NebulaPlanetTokenCx = "cx57d7acf8b5114b787ecdd99ca460c2272e4d9135"
NebulaSpaceshipTokenCx = "cx943cf4a4e4e281d82b15ae0564bbdcbf8114b3ec"

# connect to ICON main-net
icon_service = IconService(HTTPProvider("https://ctz.solidwallet.io", 3))

# function for making a call
def call(to, method, params):
    call = CallBuilder().to(to).method(method).params(params).build()
    result = icon_service.call(call)
    return result

def get_marketplace_info(contract: str, indexId: int) -> dict:
    # for given indexId - retrieve corresponding tokenId
    tokenId = int(call(contract, "get_listed_token_by_index", {"_index": indexId}), 16)

    # get token price
    set_price = int(call(contract, "get_token_price", {"_tokenId": tokenId}), 16)
    
    # get set_price/auction listings
    if set_price != -1:
        buy_type = "set price"
        status = "active"
        price = set_price / 10 ** 18
        duration = ""
    else:
        buy_type = "auction"
        auction_info = call(contract, "get_auction_info", {"_token_id": tokenId})
        
        if "Token is not on auction" not in auction_info:
            status = str(auction_info["status"]).lower()
            price = int(auction_info["current_bid"], 16) / 10 ** 18
            if price == 0:
                price = int(auction_info["starting_price"], 16) / 10 ** 18
            end_time_timestamp = int(auction_info["end_time"], 16) / 1000000
            end_time = datetime.fromtimestamp(end_time_timestamp) #.strftime('%Y-%m-%d %H:%M:%S')
            now_time = datetime.now()
            
            diff = end_time - now_time
            hours = divmod(diff.total_seconds(), 3600)
            minutes = divmod(hours[1], 60)
            #seconds = divmod(minutes[1], 1)
            duration = "%dh %dm left" % (hours[0], minutes[0])

    return {
        "status": status,
        "tokenId": tokenId,
        "buy_type": buy_type,
        "price": price,
        "duration": duration
    }

def token_drill_info_loop(df: DataFrame, key_column: str, discord_webhook: str, isAll: bool=False) -> None:
    for key in sorted(df[key_column].unique()):
        # list of buy types with corresponding colors
        buy_types = [
            ["auction", "F4D03F"],  #yellow
            ["set price", "FDFEFE"] #white
        ]

        for buy_type, color in buy_types:
            # filter to given value in key column and buy type..
            df_filtered = df.query(key_column + " == '" + key + "' and buy_type == '" + buy_type + "'")
            # .. and then find top 3 cheapest options
            if isAll == False:
                df_filtered = df_filtered.sort_values(by=["price"], ascending=True).head(3)
            # .. or show all of them
            else:
                df_filtered = df_filtered.sort_values(by=[key_column, "price"], ascending=True)
            
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
                # key column mihgt contain either 'range[1-5]' string to enforce required sorting above
                # this additional string needs removing from final output
                dtitle = re.sub("range[1-9]", "", key) + " - *" + buy_type + "*"
                webhook = DiscordWebhook(url=discord_webhook)
                embed = DiscordEmbed(title=dtitle, description=info, color=color)
                webhook.add_embed(embed)
                response = webhook.execute()
            
            # wait before sending next one to avoid blocking by discord / over-flooding users with too many alerts all at once
            sleep(20)

# function for sending error msg to discord webhook
def send_log_to_webhook(error: str):
    err_msg = "Project Nebula - Cheap Alert log"
    err_msg += "\nERROR: " + error
    err_msg += "\n"
    webhook = DiscordWebhook(url=discord_webhook_log, rate_limit_retry=True, content=err_msg)
    response = webhook.execute()
    return response


# main loop
while True:
    tokenListShipType = []
    tokenListIncome = []
    tokenListSlots = []
    tokenListCollectibles = []
    tokenListRarity = []
    tokenListSpecials = []
    tokenListBargains = []

    try:
        ###########################################################################
        # how many ships currently listed on the marketplace
        total_listed_token_count = int(call(NebulaSpaceshipTokenCx, "total_listed_token_count", {}), 16)
        
        # loop through each token on the marketplace
        for indexId in range(1, total_listed_token_count + 1):
            try:
                tokenDict = get_marketplace_info(NebulaSpaceshipTokenCx, indexId)

                # if token not active (unsold) - skip and move on
                if tokenDict["status"] != "active":
                    continue

                # pull token details
                tokenInfo = requests.get(call(NebulaSpaceshipTokenCx, "tokenURI", {"_tokenId": tokenDict["tokenId"]})).json()
                
                # initialise token info
                token = pn_token.Spaceship(tokenInfo)
                price = tokenDict["price"]
                duration = tokenDict["duration"]
                buy_type = tokenDict["buy_type"]
                
                # build description line for each token
                ship_model = token.name.lower()
                ship_type = token.get_ship_type()
                description = token.get_description(price, duration)
                
                # ship type
                tokenListShipType.append([ship_type, description, buy_type, price])

                # ship bargains
                if ("roc" in ship_model and int(price) <= 150) \
                    or ("gargoyle" in ship_model and int(price) <= 250) \
                    or ("stormbird" in ship_model and int(price) <= 700):
                    tokenListBargains.append(["range1Ships", description, buy_type, price])
            except:
                err_msg = "{}. {}, line: {}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2].tb_lineno)
                response = send_log_to_webhook(err_msg)
                continue

        df_ship_type = pd.DataFrame(tokenListShipType).drop_duplicates()
        df_ship_type.columns = ["type", "description", "buy_type", "price"]

        # loop through each given key column currently available on the marketplace
        token_drill_info_loop(df=df_ship_type, key_column="type", discord_webhook=discord_webhook_ship_type)
        
        ###########################################################################
        # how many planets currently listed on the marketplace
        total_listed_token_count = int(call(NebulaPlanetTokenCx, "total_listed_token_count", {}), 16)

        # loop through each token on the marketplace
        for indexId in range(1, total_listed_token_count + 1):
            try:
                tokenDict = get_marketplace_info(NebulaPlanetTokenCx, indexId)

                # if token not active (unsold) - skip and move on
                if tokenDict["status"] != "active":
                    continue

                # pull token details
                tokenInfo = requests.get(call(NebulaPlanetTokenCx, "tokenURI", {"_tokenId": tokenDict["tokenId"]})).json()
                
                # initialise token info
                token = pn_token.Planet(tokenInfo)
                price = tokenDict["price"]
                duration = tokenDict["duration"]
                buy_type = tokenDict["buy_type"]
                
                # build description line for each token
                description = token.get_description(price, duration)
                
                # credit range
                income = token.get_income_range("Credits")
                tokenListIncome.append([income, description, buy_type, price])

                # industry range
                income = token.get_income_range("Industry")
                tokenListIncome.append([income, description, buy_type, price])

                # research range
                income = token.get_income_range("Research")
                tokenListIncome.append([income, description, buy_type, price])

                # upgrade slots range
                slots = token.get_slots_range()
                tokenListSlots.append([slots, description, buy_type, price])

                # collectibles
                if token.isArtwork > 0:
                    description_with_artwork = token.get_description(price, duration, token.artwork)
                    tokenListCollectibles.append(["Artwork", description_with_artwork, buy_type, price])

                if token.isMusic > 0:
                    description_with_music = token.get_description(price, duration, token.music)
                    tokenListCollectibles.append(["Music", description_with_music, buy_type, price])
                
                if token.isLore > 0:
                    description_with_lore = token.get_description(price, duration, token.lore)
                    tokenListCollectibles.append(["Lore", description_with_lore, buy_type, price])
                
                # rarity
                rarity = token.get_rarity()
                tokenListRarity.append([rarity, description, buy_type, price])

                # rarity bargains
                if ("Common" in rarity and int(price) <= 15) \
                    or ("Uncommon" in rarity and int(price) <= 40) \
                    or ("Rare" in rarity and int(price) <= 120) \
                    or ("Legendary" in rarity and int(price) <= 300):
                    tokenListBargains.append(["range2Rarity", description, buy_type, price])
                
                # loop to check special resources
                for special in token.specials:
                    tokenListSpecials.append([special, description, buy_type, price])
                    
                    # special bargains
                    if int(tokenDict["price"]) <= 90:
                        description_with_special = token.get_description(price, duration, special)
                        tokenListBargains.append(["range3Specials", description_with_special, buy_type, price])
            except:
                err_msg = "{}. {}, line: {}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2].tb_lineno)
                response = send_log_to_webhook(err_msg)
                continue

        # convert list to dataframe
        df_income = pd.DataFrame(tokenListIncome).drop_duplicates()
        df_income.columns = ["income", "description", "buy_type", "price"]

        df_slots = pd.DataFrame(tokenListSlots).drop_duplicates()
        df_slots.columns = ["slots", "description", "buy_type", "price"]

        df_collectibles = pd.DataFrame(tokenListCollectibles).drop_duplicates()
        df_collectibles.columns = ["collectible", "description", "buy_type", "price"]

        df_rarity = pd.DataFrame(tokenListRarity).drop_duplicates()
        df_rarity.columns = ["rarity", "description", "buy_type", "price"]

        df_specials = pd.DataFrame(tokenListSpecials).drop_duplicates()
        df_specials.columns = ["special", "description", "buy_type", "price"]

        df_bargains = pd.DataFrame(tokenListBargains).drop_duplicates()
        df_bargains.columns = ["bargain", "description", "buy_type", "price"]

        # for debugging to run pull-push separately
        #df.to_csv("planets.csv", header=True, index=False)
        #df = pd.read_csv("planets.csv")

        # loop through each given key column currently available on the marketplace
        token_drill_info_loop(df=df_income, key_column="income", discord_webhook=discord_webhook_income)
        token_drill_info_loop(df=df_slots, key_column="slots", discord_webhook=discord_webhook_slots)
        token_drill_info_loop(df=df_collectibles, key_column="collectible", discord_webhook=discord_webhook_collectibles)
        token_drill_info_loop(df=df_rarity, key_column="rarity", discord_webhook=discord_webhook_rarity)
        token_drill_info_loop(df=df_specials, key_column="special", discord_webhook=discord_webhook_specials)
        token_drill_info_loop(df=df_bargains, key_column="bargain", discord_webhook=discord_webhook_bargains, isAll=True)

    except:
        err_msg = "{}. {}, line: {}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2].tb_lineno)
        response = send_log_to_webhook(err_msg)
        continue
    
    # wait for an 45 minutes before starting again
    sleep(2700)
