# This program is used to manage the database for the Crafting Tree Viewer.
# It is used to populate the database with the data gathered from the scraper.
# It is also used to update the database with new data whenever there is a change to the wiki.
# This uses ArangoDB as the database and PyArango as the driver.
# I will now start to ramble about how I think this should work.

# I am using Django as the web framework, so I will need to figure out how to integrate this with Django.
# I'll probably use bokeh or pyvis to visualize the data.
# It will be a heterogeneous, directed graph, with items linked to recipes and recipes linked to items.

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
# As such, each item will have edges that represent the recipes it is involved in as an ingredient.
# Each edge will have a list of attributes that represent the recipe that it represents, using directions to represent the crafting process and quantities to represent the number of items used.


import json
import requests
import arango
from wikiScraper import *


class DatabaseManager:
    """
    This class is used to manage the database for the Crafting Tree Viewer.
    It is used to populate the database with the data gathered from the scraper.
    It is also used to update the database with new data whenever there is a change to the wiki.
    This uses ArangoDB as the database and arango-python as the driver.
    """
    def __init__(self, database_name, host='http://localhost:8529', username='root', password='toor'):
        """
        Initializes the database manager.
        :param database_name:
        :param host:
        :param username:
        :param password:
        """
        self.database_name = database_name
        self.client = arango.ArangoClient(host)
        system_db = self.client.db('_system', username, password)
        if not system_db.has_database(database_name):
            system_db.create_database(database_name)
        self.db = self.client.db(database_name, username, password)
        # Create collections for the items, recipes and edges.
        if not self.db.has_collection('items'):
            self.db.create_collection('items', key_generator='autoincrement', key_increment=1)
        if not self.db.has_collection('recipes'):
            self.db.create_collection('recipes')
        if not self.db.has_collection('edges'):
            self.db.create_collection('edges', edge=True)
        self.items = self.db.collection('items')
        self.recipes = self.db.collection('recipes')
        self.edges = self.db.collection('edges')
        # Create the graph.
        if not self.db.has_graph('crafting_tree'):
            self.db.create_graph('crafting_tree')
        self.graph = self.db.graph('crafting_tree')
        # Create the vertex collections.
        if not self.graph.has_vertex_collection('items'):
            self.graph.create_vertex_collection('items')
        if not self.graph.has_vertex_collection('recipes'):
            self.graph.create_vertex_collection('recipes')
        # Create the edge collections.
        if not self.graph.has_edge_definition('edges'):
            self.graph.create_edge_definition(
                edge_collection='edges',
                from_vertex_collections=['items'],
                to_vertex_collections=['recipes']
            )
        # Create the indexes.
        self.items.add_hash_index(fields=['name'], unique=True)
        self.recipes.add_hash_index(fields=['item', 'crafting_station'], unique=True)
        self.edges.add_hash_index(fields=['_from', '_to'], unique=True)

    def add_item(self, item):
        """
        Adds an item object to the database.
        :param item:
        :type item: Item
        :return: None
        """
        item_dict = item.__dict__
        # The item's recipes are stored in a separate collection.
        item_dict['recipes'] = [recipe.__dict__ for recipe in item_dict['recipes']]
        # Check if the item is already in the database.
        if self.db.aql.execute('FOR item IN items FILTER item.name == @name RETURN item',
                               bind_vars={'name': item_dict['name']}) is None:
            print('Item already in database.')
            return
        else:
            # Add the item to the database.
            self.items.insert(item_dict)

    def add_items(self, items):
        """
        Adds a list of item objects to the database.
        :param items:
        :type items: list
        :return: None
        """
        for item in items:
            self.add_item(item)

    def add_recipe(self, recipe):
        """
        Adds a recipe object to the database.
        :param recipe:
        :type recipe: Recipe
        :return: None
        """
        recipe_dict = recipe.__dict__
        # The recipe's item is stored in a separate collection, check if it is already in the database.
        item = self.db.aql.execute('FOR item IN items FILTER item.name == @name RETURN item',
                                   bind_vars={'name': recipe_dict['item'].name})
        if item:  # If the item is already in the database, don't add it again.
            recipe_dict['item'] = item[0]
        else:  # If the item is not in the database, add it.
            self.add_item(recipe_dict['item'])

    def add_recipes(self, recipes):
        """
        Adds a list of recipe objects to the database.
        :param recipes:
        :type recipes: list
        :return: None
        """
        for recipe in recipes:
            self.add_recipe(recipe)

    def add_edge(self, item, recipe):
        """
        Adds an edge to the database.
        :param item:
        :type item: Item
        :param recipe:
        :type recipe: Recipe
        :return: None
        """
        # Check if the edge is already in the database.
        if self.edges.has({'_from': 'items/' + item.name, '_to': 'recipes/' + recipe.item.name}):
            return
        # Check if the item is already in the database.
        if self.items.has({'name': item.name}):
            # Get the item from the database.
            item = self.items.get({'name': item.name})
        else:
            # Add the item to the database.
            self.add_item(item)
        # Check if the recipe is already in the database.
        if self.recipes.has({'item': item['_id'], 'crafting_station': recipe.crafting_station}):
            # Get the recipe from the database.
            recipe = self.recipes.get({'item': item['_id'], 'crafting_station': recipe.crafting_station})
        else:
            # Add the recipe to the database.
            self.add_recipe(recipe)

    def get_item(self, name: str) -> Item | None:
        """
        Gets an item object from the database.
        :param name:
        :type name: str
        :return: The item object with the given name.
        :rtype: Item
        """
        query = 'FOR item IN items FILTER item.name == @name LIMIT 1 RETURN item'
        cursor = self.db.aql.execute(query, bind_vars={'name': name})
        # Parse the cursor into an item object.
        item_data = cursor.batch()[0]
        # Check if the batch is there
        if not item_data:
            print('Item not found')
            return
        print(item_data)
        item = Item(item_data['name'], item_data['wikiLink'], item_data['imageLink'])
        return item

    def get_ingredients(self, name):
        """
        Gets the ingredients for an item from the database.
        :param name:
        :type name: str
        :return: The ingredients for the item with the given name.
        :rtype: list
        """
        # The ingredients are the children of the connected recipe nodes.
        query = 'FOR item IN items FILTER item.name == @name FOR recipe IN item.recipes RETURN recipe.ingredients'
        cursor = self.db.aql.execute(query, bind_vars={'name': name})
        return cursor

    def get_recipes(self, name):
        """
        Gets the recipes for an item from the database.
        :param name:
        :type name: str
        :return: The recipes for the item with the given name.
        :rtype: list
        """
        # The recipes are the connected recipe nodes.
        query = 'FOR item IN items FILTER item.name == @name FOR recipe IN item.recipes RETURN recipe'
        cursor = self.db.aql.execute(query, bind_vars={'name': name})
        return cursor


def main():
    # This is just a test to make sure that the database manager works.
    # This is a test item that has a recipe.
    test_item = Item('Cell Phone', 'https://terraria.wiki.gg/wiki/Cell_Phone')
    print(test_item.__dict__)
    # This is a test item that does not have a recipe.
    test_item2 = Item('The Eye of Cthulhu', 'https://terraria.wiki.gg/wiki/The_Eye_of_Cthulhu')
    print(test_item2.__dict__)
    # Add the test items to a list.
    test_items = [test_item, test_item2]
    # Create a database manager.
    db_manager = DatabaseManager('crafting_tree')
    # Truncate the database.
    db_manager.items.truncate()
    # Add the test items to the database.
    db_manager.add_items(test_items)
    # Add recipes to the database.
    db_manager.add_recipes(test_item.recipes)
    db_manager.add_recipes(test_item2.recipes)
    # Add edges to the database.
    db_manager.add_edge(test_item, test_item.recipes)
    # Get the items from the database.
    print(db_manager.get_item('Cell Phone'))
    print(db_manager.get_item('The Eye of Cthulhu'))
    # Get the ingredients for the items from the database.
    print(db_manager.get_ingredients('Cell Phone'))
    print(db_manager.get_ingredients('The Eye of Cthulhu'))
    # Get the recipes for the items from the database.
    print(db_manager.get_recipes('Cell Phone'))
    print(db_manager.get_recipes('The Eye of Cthulhu'))


if __name__ == '__main__':
    main()
