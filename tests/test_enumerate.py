test = "uncommon"
rarity = ["common", "uncommon", "rare", "legendary", "mythic"]
index = [i for i, s in enumerate(rarity) if test in s]
print("range" + str(index[0]+1))
