# This program is used to manage the database for the Crafting Tree Viewer.
# It is used to populate the database with the data gathered from the scraper.
# It is also used to update the database with new data whenever there is a change to the wiki.
# This uses ArangoDB as the database and PyArango as the driver.
# I will now start to ramble about how I think this should work.

# I am using Django as the web framework, so I will need to figure out how to integrate this with Django.
# I'll probably use bokeh or pyvis to visualize the data.

# Items should come in as a long list of Item objects and associated Recipe objects.
# The Item objects should have the following attributes in the following order:
# name: string, the name of the item (e.g. 'Amazon')
# wiki_link: string, the link to the wiki page for the item (e.g. 'https://terraria.wiki.gg/wiki/Amazon')
# image_link: string, the link to the image for the item (e.g. 'https://terraria.wiki.gg/images/d/db/Amazon.png')
# recipes: list, a list of Recipe objects, the recipes that can be used to craft the item
# obtained_from: list, the non-crafting ways to get the item (e.g. 'Purchased from the Dryad' or 'Dropped by Skeleton')

# The Recipe objects should have the following attributes in the following order:
# item: Item object, the item that is crafted by the recipe
# crafting_station: string, the crafting station that is used to craft the item (e.g. 'Work_Bench')
# ingredients: list, a list of Item objects, the ingredients used to craft the item
# ingredient_quantities: list, a list of integers, the quantities of each ingredient used to craft the item
# url: string, the link to the wiki that the recipe was found on (e.g. 'https://terraria.wiki.gg')

# Each item will be a node in the database.
# Each recipe will be represented by the edges between the item that is crafted and the items that are used to craft it.
# As such, each item will have a list of edges that represent the recipes it is involved in, either as the item being crafted or as an ingredient.
# Each edge will have a list of attributes that represent the recipe that it represents, using directions to represent the crafting process and quantities to represent the number of items used.



import json
import requests
from pyArango.connection import *
from wikiScraper import *

class DatabaseManager:
    def __init__(self, database_name):
        self.database_name = database_name
        self.connection = Connection(username="root", password="root")
        self.db = self.connection[self.database_name]
        self.items = self.db["items"]
        self.recipes = self.db["recipes"]

    def add_item(self, item):
        item_doc = self.items.createDocument()
        item_doc["name"] = item.name
        item_doc["wiki_link"] = item.wiki_link
        item_doc["image_link"] = item.image_link
        item_doc["obtained_from"] = item.obtained_from
        item_doc["recipes"] = []
        item_doc.save()


    def add_recipe(self, recipe):
        recipe_doc = self.recipes.createDocument()
        recipe_doc["item"] = recipe.item.name
        recipe_doc["crafting_station"] = recipe.crafting_station
        recipe_doc["ingredients"] = []
        recipe_doc["ingredient_quantities"] = []
        recipe_doc["url"] = recipe.url
        recipe_doc.save()
        for ingredient in recipe.ingredients:
            recipe_doc["ingredients"].append(ingredient.name)
        for quantity in recipe.ingredient_quantities:
            recipe_doc["ingredient_quantities"].append(quantity)
        recipe_doc.save()
        item_doc = self.items.fetchFirstExample({"name": recipe.item.name})[0]
        item_doc["recipes"].append(recipe_doc["_id"])
        item_doc.save()

    def update_item(self, item):
        item_doc = self.items.fetchFirstExample({"name": item.name})[0]
        item_doc["name"] = item.name
        item_doc["wiki_link"] = item.wiki_link
        item_doc["image_link"] = item.image_link
        item_doc["obtained_from"] = item.obtained_from
        item_doc.save()

    def update_recipe(self, recipe):
        recipe_doc = self.recipes.fetchFirstExample({"item": recipe.item.name})[0]
        recipe_doc["item"] = recipe.item.name
        recipe_doc["crafting_station"] = recipe.crafting_station
        recipe_doc["ingredients"] = []
        recipe_doc["ingredient_quantities"] = []
        recipe_doc["url"] = recipe.url
        recipe_doc.save()
        for ingredient in recipe.ingredients:
            recipe_doc["ingredients"].append(ingredient.name)
        for quantity in recipe.ingredient_quantities:
            recipe_doc["ingredient_quantities"].append(quantity)
        recipe_doc.save()

    def delete_item(self, item):
        item_doc = self.items.fetchFirstExample({"name": item.name})[0]
        item_doc.delete()

    def delete_recipe(self, recipe):
        recipe_doc = self.recipes.fetchFirstExample({"item": recipe.item.name})[0]
        recipe_doc.delete()



