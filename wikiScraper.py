# This file contains the Scraper class, which is used to scrape a game's wiki for crafting recipes.
# It is used in the CraftingTreeViewer app, which is a Django web app that displays crafting recipes in a node tree.
# Each node represents an item and its children represent the items needed to craft it.
# Each item is gathered from the wiki, made into an object, and stored in a database to be turned into a node.
# The data will be stored as json
# Each item will find its own ingredients and store them in a list

from bs4 import BeautifulSoup
import requests
import re
import json


def underscore_to_space(string):
    """
    :type string: str
    :param string:
    :return:
    """
    return re.sub('_', ' ', string)


def space_to_underscore(string):
    """
    :type string: str
    :param string:
    :return:
    """
    return re.sub('\s', '_', string)


def soupify(url):
    item_page = requests.get(url)
    # Check if the page exists
    if item_page.status_code != 200:
        print(f'Error: Page {url} has a problem, don\'t ask me what it is')
        return
    # Parse the page
    soup = BeautifulSoup(item_page.content, 'html.parser')
    return soup


class Item:
    def __init__(self, name, wikiLink, imageLink=None, source='Vanilla'):
        """
        :type name: str
        :type recipes: list
        :type wikiLink: str
        :type imageLink: str
        :param self:
        :param recipes: A list of recipes that can be used to craft the item
        :param name: The name of the item
        :param wikiLink: The link to the item's wiki page
        :param imageLink: The link to the item's image
        """

        self.name = name
        self.wikiLink = wikiLink
        self.imageLink = imageLink
        self.recipes = []
        self.obtainedFrom = []
        self.source = source
        if imageLink is None:
            self.retrieve_image_link(self.wikiLink)
        self.retrieve_recipes()
        self.retrieve_obtained_from()

    def retrieve_recipes(self):
        """
        :type self:
        :return self.recipes:
        """
        soup = soupify(self.wikiLink)
        # Find the table containing the crafting recipe
        table = soup.find('table', class_='background-1')
        # Check if the table exists, if empty there are no recipes
        if table is None:
            self.recipes = []
            return
        # Find all the rows in the table
        table_rows = table.find_all('tr')
        # Iterate through the rows
        for row in table_rows:
            cells = row.find_all('td')
            if '<th>' in str(cells):
                continue
            # Make a recipe object from the row
            recipe = Recipe(cells)
            # Add the recipe to the list of recipes
            self.recipes.append(recipe)

    def __retrieve_obtained_from_vanilla(self):
        # This one will be a bit more complicated
        # The wiki has a table that sometimes has the item's source in it
        # The table only exists if the item is in a drop table
        soup = soupify(self.wikiLink)
        # Search to see if the drops table exists
        # The drops table has multiple tabs that change out the HTML
        drops_table = soup.find('table', class_='drop-noncustom sortable')
        if drops_table is None:
            self.obtainedFrom = []
            print('Error: Drops table does not exist')
            return
        # Find all the rows in the table
        table_rows = drops_table.find_all('tr')
        # Iterate through the rows
        for row in table_rows:
            cells = row.find_all('td')
            if '<th>' in str(cells):
                continue
            elif len(cells) == 0:
                continue
            # if 'i3' or 'i5' are in the row and there is only one percentage, skip it
            if 'i3' in str(cells) or 'i5' in str(cells):
                if 'i1' not in str(cells):
                    continue
            e_name = cells[0].find('a')['title']
            quantity = cells[1].text
            # The drop rate is a bit more complicated as there are sometimes 2 drop rates for different versions of the game
            # Exclude 3DS drop rates as they are not relevant
            # Find the span that has the drop rate for desktop at least
            if cells[2].find('span', class_='eico s i1') is None:
                drop_rate = cells[2].text
            else:
                drop_rate = cells[2].find('span', class_='m-normal')
                drop_rate_expert = cells[2].find('span', class_='m-expert')

    def __retrieve_obtained_from_calamity(self):
        # The calamity wiki has drop tables that makes more sense in some ways
        soup = soupify(self.wikiLink)
        # The drops table on the calamity wiki is just an infobox with a table in it
        drops_table = soup.find('table', class_='infobox')
        if drops_table is None:
            self.obtainedFrom = []
            return
        # Find all the rows in the table
        table_rows = drops_table.find_all('tr')
        # Iterate through the rows
        for row in table_rows:
            cells = row.find_all('td')
            if '<th>' in str(cells):
                continue

            # The first cell has the name of the entity that drops the item
            # The second cell has the drop quantity
            quantity = cells[1].text
            # The third cell has the drop rate, separate the drop rate from the drop rate for expert mode
            drop_rate = cells[2].text.strip('/')
            # If the first cell has multiple links, all of them are used
            if len(cells[0].find_all('a')) > 1:
                for link in cells[0].find_all('a'):
                    self.obtainedFrom.append(link['title'] + ' ' + quantity + ' ' + drop_rate)
            else:
                self.obtainedFrom.append(cells[0].find('a')['title'] + ' ' + quantity + ' ' + drop_rate)

    def retrieve_obtained_from(self):
        # This one will be a bit more complicated
        # The wiki has a table that sometimes has the item's source in it
        # The table only exists if the item is in a drop table
        item_page = requests.get(self.wikiLink)
        # Check if the page exists
        if item_page.status_code != 200:
            print('Error: Page has a problem, don\'t ask me what it is')
            return
        elif 'terraria.wiki.gg' in item_page.url:
            self.__retrieve_obtained_from_vanilla()
            return
        elif 'calamitymod.wiki.gg' in item_page.url:
            self.__retrieve_obtained_from_calamity()
            return
        else:
            print('Error: Page is not from the vanilla or calamity wiki')
            return

    def get_obtained_from(self):
        return self.obtainedFrom


    def get_json(self):
        return json.dumps(self.__dict__)

    def get_name(self):
        return self.name

    def get_recipes(self):
        return self.recipes

    def get_wiki_link(self):
        return self.wikiLink

    def get_image_link(self):
        return self.imageLink

    def set_name(self, name):
        self.name = name

    def set_wiki_link(self, wikiLink):
        self.wikiLink = wikiLink

    def set_image_link(self, imageLink):
        self.imageLink = imageLink

    def add_recipe(self, recipe):
        self.recipes.append(recipe)

    def get_recipe(self, index):
        return self.recipes[index]

    def retrieve_image_link(self, url):
        """
        :type self:
        :param url:
        :return:
        """
        soup = soupify(url)
        # Find the image on the page, it is the first image with the alt text '<item name> item sprite'
        image = soup.find('img', alt=self.name + ' item sprite')
        # Check if the image exists
        if image is None:
            print('Error: Image does not exist')
            return
        # Get the image link and append it to the wiki url, which is the first part of the wiki link
        self.imageLink = url.split('/wiki/')[0] + image['src']


class Recipe:
    def __init__(self, item: Item, crafting_station: str = '', ingredients: list = None,
                 ingredient_quantities: list = None, initial: bool = True):
        """
        :type self: Recipe
        :param item: The item that the recipe is for
        :param crafting_station: The crafting station that the recipe is crafted at
        :param ingredients: A list of items that are used to craft the item
        :param ingredient_quantities: A list of quantities of the ingredients
        :param initial: Determines whether the recipe is retrieved from the wiki or not when the object is created
        """
        if ingredients is None:
            ingredients = []
        if ingredient_quantities is None:
            ingredient_quantities = []
        self.item = item
        self.crafting_station = crafting_station
        self.ingredients = ingredients
        self.ingredientQuantities = ingredient_quantities
        self.url = 'https://terraria.wiki.gg'
        if initial:
            self.retrieve_ingredients(item)
        if not initial and (ingredients is None or ingredient_quantities is None):
            print('Error: Cannot create recipe without ingredients')
            self.retrieve_ingredients(item)

    def get_item(self):
        return self.item

    def get_crafting_location(self):
        return self.crafting_station

    def get_ingredients(self):
        return self.ingredients

    def get_ingredient_quantities(self):
        return self.ingredientQuantities

    def get_json(self):
        return json.dumps(self.__dict__)

    def retrieve_ingredients(self, item):
        """
        :type self:
        :param item:
        :return:
        """
        # Get the wiki page for the item
        soup = soupify(item)
        # Find the table containing the crafting recipe
        table = soup.find('table', class_='terraria cellborder recipes sortable jquery-tablesorter')
        # Check if the table exists
        if table is None:
            print('Warning: Table does not exist')
            return
        # Find all the rows in the table

        if int(table['data-totalrows']) == 1:
            cells = table.find_all('td')
            for item in cells[1].find_all('a'):
                self.ingredients.append(Item(item['title'], self.url + item['href']))
        # If the table has more than one row, it has more than one recipe
        elif int(table['data-totalrows']) > 1:
            table_rows = table.find_all('tr')
            table_rows[0][1]


class CalamityRecipe(Recipe):
    def __init__(self, item: Item, crafting_station: str = '', ingredients: list = None,
                 ingredient_quantities: list = None, initial: bool = True):
        """
        :type self: Recipe
        :param item: The item that the recipe is for
        :param initial: Determines whether the recipe is retrieved from the wiki or not when the object is created
        """
        super().__init__(item, crafting_station, ingredients, ingredient_quantities, initial)
        self.url = 'https://calamitymod.wiki.gg'

    def retrieve_ingredients(self, item):
        """
        :type self:
        :param item:
        :return:
        """

        # Get the wiki page for the item
        soup = soupify(item)
        # Find the table containing the crafting recipe
        table = soup.find('table', class_='background-1')
        # Check if the table exists
        if table is None:
            print('Error: Table does not exist')
            return
        # Find all the rows in the table
        table_rows = table.find_all('tr')
        self.crafting_station = space_to_underscore(table_rows[1][0].find('a')['title'])
        # Iterate through the rows
        for row in table_rows:
            cells = row.find_all('td')
            # The second row has the crafting station
            # The fourth row and beyond have the images, names and quantities of the ingredients in that order in each cell
            # The second to last row is another header
            # The last row has the image, name and quantity of the item crafted, the name is the same as the item name, get the quantity
            # Skip the table headers
            if '<th>' in str(cells):
                continue
            elif len(cells) == 0:
                continue
            # Iterate through the cells
            image_link = self.url + cells[0].find('img')['src']
            name = cells[1].find('a')['title']
            quantity = cells[2].text
            self.ingredients.append(Item(name, self.url + name, image_link))
            self.ingredientQuantities.append(quantity)


class Scraper:
    def __init__(self, url):
        """
            :type url: str
            :param self:
            :param url: format: 'https://terraria.wiki.gg'
            """
        self.url = url
        self.recipes_page = requests.get(url + '/wiki/Recipes')
        self.data = []


    def get_data(self):
        return self.data

    def get_json(self):
        return json.dumps(self.data)

    def find_crafting_stations(self, url: str) -> list:
        """
        :type self:
        :param url:
        :return crafting_stations:
        """
        craft_page = requests.get(url + '/wiki/Crafting_stations')  # Get the crafting stations page
        soup = BeautifulSoup(craft_page.content, 'html.parser')  # Parse the page
        tables = soup.find_all('table')  # Find all the tables
        crafting_stations = []  # Create a list to store the crafting stations
        if self.recipes_page.status_code != 200:  # Check if the page exists
            print('Error: Page does not exist')
            return crafting_stations

        for table in tables:
            # Iterate through the tables
            rows = table.find_all('tr')  # Find all the rows in the table
            # Check if the table is for moon phases, skip it if it is
            if 'Moon phase' in str(table):
                continue
            for row in rows:  # Iterate through the rows
                # There are a few edge cases where the name of the crafting station is not the name of the first link in the row
                # If the row has 2 links in one cell, the name of the crafting station is a more general version of the name
                # The more general version can be found by what the links have in common, usually with 'Hardmode' prepended
                # The exceptions to this are the 'Altars' and 'Furnace'/'Hellforge' crafting stations
                # Only the string 'Altars' is used for the 'Altars' crafting station
                # The 'Furnace' and 'Hellforge' crafting stations are both added to the list
                # All crafting stations have an image in the first cell except for 'By Hand'
                # Find all the cells in the row
                cell = row.find('td')
                # Check if the cell is null, skip the row if it is
                if cell is None:
                    continue
                # Check if the cell has any images in it, if it doesn't, skip it unless it's the 'By Hand' crafting station
                if len(cell.find_all('img')) == 0:
                    if cell.text == 'By Hand':
                        crafting_stations.append('By_Hand')
                    continue
                elif len(cell.find_all('img')) == 1:  # Check if the cell has 1 image in it
                    link = cell.find('a')['title']  # Find all the links in the cell
                    regex_link = space_to_underscore(link)
                    if link is None:  # Skip the row if it doesn't have any links
                        continue
                    crafting_stations.append(regex_link)  # Add the link to the list
                elif len(cell.find_all('img')) == 2:  # Check if the cell has 2 images in it
                    links = cell.find_all('a')  # Find all the links in the cell
                    # If the name is 'Demon Altar' or 'Crimson Altar', the name is 'Altars'
                    if links[0]['title'] == 'Demon Altar' and links[3]['title'] == 'Crimson Altar':
                        crafting_stations.append('Altars')
                        continue
                    elif links[0]['title'] == 'Furnace' and links[3]['title'] == 'Hellforge':
                        crafting_stations.append('Furnace')
                        crafting_stations.append('Hellforge')
                        continue
                    elif links[0]['title'] == 'Placed Bottle' and links[3]['title'] == 'Alchemy Table':
                        crafting_stations.append('Alchemy_Table')
                        continue
                    elif links[0]['title'] == 'Cooking Pot' and links[3]['title'] == 'Cauldron':
                        crafting_stations.append('Cooking_Pot')
                        continue
                    elif links[0]['title'] == 'Iron Anvil' and links[3]['title'] == 'Lead Anvil':
                        crafting_stations.append('Pre-Hardmode_Anvils')
                        continue
                    elif 'chair' in links[0]['title'].lower():
                        crafting_stations.append(re.sub(r'\s', '_', links[0]['title']))
                        continue
                    else:
                        crafting_stations.append('Hardmode_' + links[0]['title'].split(' ')[1])
                        continue
                else:
                    print('Error: Value of table is probably null')
        return crafting_stations


class VanillaScraper(Scraper):
    def __init__(self):
        """
        :type url: str
        :param self:
        :param url: format: 'https://terraria.wiki.gg'
        """
        super().__init__('https://terraria.wiki.gg')

    def scrape_items(self):
        """
        Scrapes the wiki for items and returns them as a list of item objects
        :type self:

        """
        soup = soupify(self.url + '/wiki/Item_IDs')
        table = soup.find('table', class_='terraria lined sortable jquery-tablesorter')
        rows = table.find_all('tr')
        item_list = []
        for row in rows:
            item = Item(row[1].find('a')['title'], self.url + row[1].find('a')['href'])
            item_list.append(item)
        return item_list

    def scrape_recipes(self):
        """
        Scrapes the wiki for item recipes and returns them as a list of recipe objects
        :type self:
        :return:
        """
        # The vanilla wiki has a different format to the calamity wiki, so it needs to be scraped differently
        # The both wikis have a table for each crafting station, which is the caption of the table
        # The both wikis also have a page for each crafting station, which has a table containing the recipes for that station
        # Each page is in the format: url + '/wiki/Recipes/' + crafting station

        crafting_stations = self.find_crafting_stations()
        for station in crafting_stations:
            soup = BeautifulSoup(self.url + '/wiki/Recipes/' + station, 'html.parser')
            table = soup.find('table')
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                # cells[0] has the image and name of the item crafted, cells[1] has the ingredients and quantities
                # Make an item object from cells[0]
                found_item = cells[0].find('a')
                item = Item(found_item['title'], found_item['href'], self.url + cells[0].find('img')['src'])
                # Find the recipes for the item
                item.retrieve_recipes()
                # Add the item to the list of items
                self.data.append(item)
        return self.data

    def get_data(self):
        """
        :type self:
        :return:
        """
        return self.data

    def get_json(self):
        """
        :type self:
        :return:
        """
        return json.dumps(self.data)

    def find_crafting_stations(self, url='https://terraria.wiki.gg'):
        """
        :param url:
        :type self:
        :return:
        """
        super().find_crafting_stations(url)


class CalamityScraper(Scraper):
    def __init__(self):
        super().__init__('https://calamitymod.wiki.gg')

    def scrape_items(self):
        """
        Scrapes the wiki for items and returns them as a list of item objects
        :type self:

        """
        soup = soupify(self.url + '/wiki/List_of_Items')
        # TODO: sift through the ajax links to get the items
        tables = soup.find_all('table', class_='terraria ajax')
        urls = []
        for table in tables:
            urls.append(table.find['data-ajax-source-page'])
        item_list = []
        for link in urls:
            soupy = soupify(f'{self.url}/wiki/{link}')
            table = soupy.find('table', class_='terraria lined sortable jquery-tablesorter')
            rows = table.find_all('tr')
            for row in rows:
                item = Item(row[1].find('a')['title'], self.url + row[1].find('a')['href'])
                item_list.append(item)


    def get_data(self):
        """
        :type self:
        :return:
        """
        return self.data
