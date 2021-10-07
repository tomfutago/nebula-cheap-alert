import json

class PNToken:
    def __init__(self, tokenInfo: json) -> None:
        # get common attributes
        self.generation = str(tokenInfo["generation"])
        self.type = str(tokenInfo["type"]).strip()
        self.image_url = tokenInfo["image"]
        self.external_link = tokenInfo["external_link"]

class Planet(PNToken):
    def __init__(self, tokenInfo: json) -> None:
        super().__init__(tokenInfo)

        # get basic info about the token per token type
        self.name = str(tokenInfo["name"])
        self.rarity = str(tokenInfo["rarity"])
        self.credits = int(tokenInfo["credits"])
        self.industry = int(tokenInfo["industry"])
        self.research = int(tokenInfo["research"])
        
        # any special resources?
        special_resources = []
        for special in tokenInfo["specials"]:
            special_resources.append(str(special["name"]))
        #self.specials = ', '.join(special_resources)
        self.specials = special_resources

        # any collectibles?
        self.isArtwork = 1 if tokenInfo["collectables"]["artwork"] != None else 0
        self.isMusic = 1 if tokenInfo["collectables"]["music"] != None else 0
        self.isLore = 1 if tokenInfo["collectables"]["lore"] != None else 0

        # slots
        self.slotCount = len(tokenInfo["upgrades"])

    def get_description(self, price, duration) -> str:
        description = "[**" + self.name.upper() + "**](" + self.external_link + ")"
        description += "  " + self.generation.lower() + "/" + self.rarity.lower()
        description += "  __" + str(price) + "__"
        if duration != "":
            description += "  - " + duration
        return description
    
    def get_income_range(self, income_label: str) -> str:
        income_range = ""
        
        if income_label == "Credits":
            income_type = self.credits
        elif income_label == "Industry":
            income_type = self.industry
        elif income_label == "Research":
            income_type = self.research

        if income_type <= 5:
            income_range = income_label + "range1" + " 0 to 5"
        elif income_type > 5 and income_type <= 10:
            income_range = income_label + "range2" + " 6 - 10"
        elif income_type > 10 and income_type <= 15:
            income_range = income_label + "range3" + " 11 - 15"
        elif income_type > 15:
            income_range = income_label + "range4" + " 16+"
        return income_range
    
    def get_slots_range(self) -> str:
        slot_range = ""
        if self.slotCount <= 3:
            slot_range = "range1" + "2 - 3 slots"
        elif self.slotCount > 3 and self.slotCount <= 5:
            slot_range = "range2" + "4 - 5 slots"
        elif self.slotCount > 5 and self.slotCount <= 7:
            slot_range = "range3" + "6 - 7 slots"
        elif self.slotCount > 7 and self.slotCount <= 9:
            slot_range = "range4" + "8 - 9 slots"
        elif self.slotCount > 9:
            slot_range = "range5" + "10+ slots"
        return slot_range
    
    def get_rarity(self) -> str:
        rarityList = ["common", "uncommon", "rare", "legendary", "mythic"]
        index = [i for i, s in enumerate(rarityList) if self.rarity in s]
        return "range" + str(index[0]+1) + self.rarity.title()

class Spaceship(PNToken):
    def __init__(self, tokenInfo: json) -> None:
        super().__init__(tokenInfo)

        self.name = str(tokenInfo["model_name"])
        self.rarity = str(tokenInfo["set_type"])
        self.tier = str(tokenInfo["tier"])
        self.exploration = str(tokenInfo["exploration"])
        self.colonization = str(tokenInfo["colonization"])
        self.movement = str(tokenInfo["movement"])
        self.fuel = str(tokenInfo["fuel"])

    def get_description(self, price, duration) -> str:
        description = "[**" + self.name.upper() + "**](" + self.external_link + ")"
        description += "  " + self.generation.lower()
        description += "  __" + str(price) + "__"
        if duration != "":
            description += "  - " + duration
        return description
    
    def get_ship_type(self) -> str:
        ship_type = ""
        if self.type == "scouting vessel":
            ship_type = "range1"
        elif self.type == "exploration vessel":
            ship_type = "range2"
        elif self.type == "colony ship":
            ship_type = "range3"
        ship_type += self.type.lower() + " " + self.tier.upper()
        return ship_type
