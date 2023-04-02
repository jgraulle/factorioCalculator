#!/bin/python3

import argparse
import string
import json
import os
import lupa
import shutil
from PIL import Image
import yattag
from typing import NamedTuple
import math


class Recipe(NamedTuple):
    ingredients: dict[str, int]
    time: float
    results: dict[str, int]
    category: str
Recipes = dict[str, Recipe]


def getVersion(factoriopath:string) -> string:
    # Read info.json file
    with open(os.path.join(factoriopath, "data", "base", "info.json")) as infoFile:
        infoData = infoFile.read()
    # info.json json parse
    infoJson = json.loads(infoData)
    return infoJson["version"]


def getRecipes(factoriopath:string, recipesToRemove:set) -> Recipes:
    # read recipe.lua
    with open(os.path.join(factoriopath, "data", "base", "prototypes", "recipe.lua")) as recipeFile:
        recipeData = recipeFile.read()
    # recipe.lua lua parse
    lua = lupa.LuaRuntime()
    luaDataBegin = """
        local data = {}
        data.__index = data
        function data:extend(a)
            return a
        end
    """
    recipeLua = lua.execute(luaDataBegin+"return "+recipeData)
    recipes = {}
    for index in range(1, len(recipeLua)+1):
        # Get recipe name
        recipeName = recipeLua[index]["name"]
        if recipeName == None:
            raise ValueError("No name found for recipe")
        if recipeName in recipesToRemove:
            continue
        # Check recipe type
        if recipeLua[index]["type"] != "recipe":
            raise ValueError("Invalid recipe type for \"{}\"".format(recipeName))
        # Get category
        recipeCategory = "basic-crafting"
        if recipeLua[index]["category"] != None:
            recipeCategory = recipeLua[index]["category"]
        # Get lua recipe ingrediants
        ingredients = {}
        if recipeLua[index]["ingredients"] != None:
            ingredientsLua = recipeLua[index]["ingredients"]
        elif recipeLua[index]["normal"]["ingredients"] != None:
            ingredientsLua = recipeLua[index]["normal"]["ingredients"]
        else:
            raise ValueError("No ingredients found for \"{}\"".format(recipeName))
        # Convert lua recipe ingrediants into python
        for indexIngredient in range(1, len(ingredientsLua)+1):

            if ingredientsLua[indexIngredient][1] != None:
                ingredientName = ingredientsLua[indexIngredient][1]
            elif ingredientsLua[indexIngredient]["name"] != None:
                ingredientName = ingredientsLua[indexIngredient]["name"]
            else:
                raise ValueError("No ingredient name found for \"{}\" at {}".format(recipeName, indexIngredient))
            if ingredientsLua[indexIngredient][2] != None:
                ingredientAmount = ingredientsLua[indexIngredient][2]
            elif ingredientsLua[indexIngredient]["amount"] != None:
                ingredientAmount = ingredientsLua[indexIngredient]["amount"]
            else:
                raise ValueError("No ingredient amount found for \"{}\" at {}".format(recipeName, indexIngredient))
            ingredients[ingredientName] = ingredientAmount
        # Get optional recipe energy required
        time = recipeLua[index]["energy_required"]
        if time == None:
            time = 0.5
        # Get recipe result
        results = {}
        if recipeLua[index]["result"] != None:
            resultCount = 1
            if recipeLua[index]["result_count"] != None:
                resultCount = recipeLua[index]["result_count"]
            results[recipeLua[index]["result"]] = resultCount
        elif recipeLua[index]["results"] != None:
            for indexResult in range(1, len(recipeLua[index]["results"])+1):
                if recipeLua[index]["results"][indexResult]["name"] != None:
                    resultName = recipeLua[index]["results"][indexResult]["name"]
                elif recipeLua[index]["results"][indexResult][1] != None:
                    resultName = recipeLua[index]["results"][indexResult][1]
                else:
                    raise ValueError("No result name found for \"{}\" at {}".format(recipeName, indexResult))
                resultAmount = recipeLua[index]["results"][indexResult]["amount"]
                if recipeLua[index]["results"][indexResult]["amount"] != None:
                    resultAmount = recipeLua[index]["results"][indexResult]["amount"]
                elif recipeLua[index]["results"][indexResult][2] != None:
                    resultAmount = recipeLua[index]["results"][indexResult][2]
                else:
                    raise ValueError("No result amount found for \"{}\" at {}".format(recipeName, indexResult))
                results[resultName] = resultAmount
        elif recipeLua[index]["normal"]["result"] != None:
            resultCount = 1
            if recipeLua[index]["normal"]["result_count"] != None:
                resultCount = recipeLua[index]["normal"]["result_count"]
            results[recipeLua[index]["normal"]["result"]] = resultCount
        else:
            raise ValueError("No result found for \"{}\"".format(recipeName))
        recipes[recipeName] = Recipe(ingredients, time, results, recipeCategory)
    # return recipes dict
    return recipes


def loadRecipes(jsonFilePath: string) -> Recipes:
    with open(jsonFilePath, 'r') as jsonFile:
        jsonRecipes = json.load(jsonFile)
    recipes = Recipes()
    for recipeName, jsonRecipe in jsonRecipes.items():
        recipes[recipeName] = Recipe(jsonRecipe["ingredients"], jsonRecipe["time"], jsonRecipe["results"], jsonRecipe["category"])
    return recipes


def recipesRemoveItem(recipes: Recipes, itemsToRemove):
    recipesToDelete = []
    for recipeName, recipe in recipes.items():
        for ingredientName in list(recipe.ingredients.keys()):
            if ingredientName in itemsToRemove:
                del recipe.ingredients[ingredientName]
        for resultName in list(recipe.results.keys()):
            if resultName in itemsToRemove:
                del recipe.results[resultName]
        if len(recipe.ingredients)==0 or len(recipe.results)==0:
            recipesToDelete.append(recipeName)
    for recipeName in recipesToDelete:
        del recipes[recipeName]


def writeRecipesJsonFile(recipes: Recipes, fileName: string):
    jsonData = {}
    for recipeName, recipe in recipes.items():
        jsonData[recipeName] = {"ingredients": recipe.ingredients, "time": recipe.time, "results": recipe.results, "category": recipe.category}
    with open(fileName, 'w') as jsonFile:
        json.dump(jsonData, jsonFile, ensure_ascii=False, indent=3)


def ingredientsByUsage(recipes: Recipes) -> dict:
    usage = {}
    for recipe in recipes.values():
        for ingredientName in recipe.ingredients.keys():
            if ingredientName not in usage:
                usage[ingredientName] = []
            for result in recipe.results.keys():
                usage[ingredientName].append(result)
    return dict(sorted(usage.items(), key=lambda item: len(item[1]), reverse=True))


def removeLeafe(recipes: Recipes):
    itemUsedAsIngredient = set()
    for recipe in recipes.values():
        for ingredientName in recipe.ingredients.keys():
            itemUsedAsIngredient.add(ingredientName)
    for recipeName in list(recipes.keys()):
        for resultName in list(recipes[recipeName].results.keys()):
            if resultName not in itemUsedAsIngredient:
                del recipes[recipeName].results[resultName]
        if len(recipes[recipeName].results) == 0:
            del recipes[recipeName]


def keepOnlyLeafe(recipes: Recipes):
    itemUsedAsIngredient = set()
    for recipe in recipes.values():
        for ingredientName in recipe.ingredients.keys():
            itemUsedAsIngredient.add(ingredientName)
    for recipeName in list(recipes.keys()):
        if len(set(recipes[recipeName].results.keys()).difference(itemUsedAsIngredient))==0:
            del recipes[recipeName]


def itemPngPath(itemName: string, factoriopath: string) -> string:
    itemRenames = {"discharge-defense-remote": "discharge-defense-equipment-controller",
                   "stone-wall": "wall",
                   "defender-capsule": "defender",
                   "distractor-capsule": "distractor",
                   "destroyer-capsule": "destroyer",
                   "raw-fish": "fish",
                   "heat-exchanger":"heat-boiler"}
    if itemName in itemRenames:
        itemName = itemRenames[itemName]
    filePathes = [os.path.join(factoriopath, "data", "base", "graphics", "icons", itemName+".png"),
                  os.path.join(factoriopath, "data", "base", "graphics", "icons", "fluid", itemName+".png"),
                  os.path.join(factoriopath, "data", "base", "graphics", "icons", "fluid", "barreling", itemName+".png")]
    for filePath in filePathes:
        if os.path.exists(filePath):
            return filePath
    raise FileNotFoundError("PNG file for \"{}\" not found in factorio path \"{}\"".format(itemName, factoriopath))


def itemPngCopy(itemName: string, factoriopath:string, dstFolderPath: string):
    imgSrc = Image.open(itemPngPath(itemName, factoriopath))
    imgdst = imgSrc.crop((64, 0, 64+32, 32)) # left, upper, right, and lower 
    imgdst.save(os.path.join(dstFolderPath, itemName+".png"))


def itemsPngCopy(recipes: Recipes, factoriopath:string, dstFolderPath: string):
    itemsName = set()
    for recipe in recipes.values():
        for ingredientName in recipe.ingredients.keys():
            if ingredientName not in itemsName:
                itemPngCopy(ingredientName, factoriopath, dstFolderPath)
                itemsName.add(ingredientName)
        for resultName in recipe.results.keys():
            if resultName not in itemsName:
                itemPngCopy(resultName, factoriopath, dstFolderPath)
                itemsName.add(resultName)


def ingredientsByUsage2Html(ingredientsByUsage: dict, htmlFilePath: string, itemsPngCopyFolderPath: string):
    doc, tag, text = yattag.Doc().tagtext()
    with tag('html'):
        with tag("head"):
            with tag("style"):
                text("table, th, td {border: 1px solid black;border-collapse: collapse;}")
        with tag('body'):
            with tag('table'):
                with tag('tr'):
                    with tag('th'):
                        text("name")
                    with tag('th'):
                        text("icon")
                    with tag('th'):
                        text("count")
                    with tag('th'):
                        text("used by")
                for ingredientName, resultList in ingredientsByUsage.items():
                    with tag('tr'):
                        with tag('td'):
                            text(ingredientName)
                        with tag('td'):
                            doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, ingredientName+".png"), alt=ingredientName, title=ingredientName)
                        with tag('td'):
                            text(len(resultList))
                            with tag('td'):
                                for resultName in resultList:
                                    doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, resultName+".png"), alt=resultName, title=resultName)

    html = doc.getvalue()
    with open(htmlFilePath, "wb") as htmlFile:
        htmlFile.write(bytes(html, "utf8"))


def generateDot(recipes: Recipes, dotFilePath: string, itemsPngCopyFolderPath: string):
    def convertItemName(name:str):
        return name.replace("-", "_").replace(" ", "_ ")
    def generateNode(ingredientName:str) -> str:
        return '   {0} [shape=none, label="", image="{1}.png"];\n'.format(convertItemName(ingredientName), os.path.join(itemsPngCopyFolderPath, ingredientName))
    with open(dotFilePath, "w") as dotFile:
        dotFile.write("digraph {\n")
        itemsName = set()
        # Write Node
        for recipe in recipes.values():
            for ingredientName in recipe.ingredients.keys():
                if ingredientName not in itemsName:
                    dotFile.write(generateNode(ingredientName))
                    itemsName.add(ingredientName)
            for resultName in recipe.results.keys():
                if resultName not in itemsName:
                    dotFile.write(generateNode(resultName))
                    itemsName.add(resultName)
        dotFile.write("\n")
        # Write edge 
        for recipe in recipes.values():
            ingredients = "{"
            for resultName in recipe.results.keys():
                ingredients = ', '.join(convertItemName(ingredientName) for ingredientName in recipe.ingredients.keys())
                dotFile.write("   {{{}}} -> {}\n".format(ingredients, convertItemName(resultName)))
        dotFile.write("}\n")


def generateConso(recipes: Recipes, requesteds: dict, htmlFilePath: string, itemsPngCopyFolderPath: string) -> tuple[dict,dict]:
    conso = {}
    isNewRequested = True
    counter = 0
    while isNewRequested:
        isNewRequested = False
        counter += 1
        for recipeName, recipe in recipes.items():
            factoryCount = 0
            for resultName, resultCount in recipe.results.items():
                if resultName in requesteds:
                    factoryUnitProduction = 1.0/recipe.time*resultCount
                    factoryCount = max(requesteds[resultName] / factoryUnitProduction, factoryCount)
            if factoryCount > 0:
                if recipeName not in conso:
                    conso[recipeName] = {"factoryCount": math.ceil(factoryCount), "results": {}, "ingredients": {}}
                for resultName, resultCount in recipe.results.items():
                    if resultName not in conso[recipeName]["results"]:
                        conso[recipeName]["results"][resultName] = 0.0
                    conso[recipeName]["results"][resultName] += 1.0 / recipe.time * resultCount * factoryCount
                    if resultName in requesteds:
                        del requesteds[resultName]
                for ingredientName, ingredientCount in recipe.ingredients.items():
                    ingredientConso = 1.0 / recipe.time * ingredientCount * factoryCount
                    if conso[recipeName]["results"][resultName] not in conso[recipeName]["ingredients"]:
                        conso[recipeName]["ingredients"][ingredientName] = 0.0
                    conso[recipeName]["ingredients"][ingredientName] += ingredientConso
                    if ingredientName not in requesteds:
                        requesteds[ingredientName] = 0.0
                    requesteds[ingredientName] += 1.0 / recipe.time * ingredientCount * factoryCount
                    isNewRequested = True
    return conso,requesteds


def conso2Html(conso:dict, requesteds:dict, htmlFilePath: string, itemsPngCopyFolderPath: string):
    doc, tag, text = yattag.Doc().tagtext()
    with tag('html'):
        with tag("head"):
            with tag("style"):
                text("table, th, td {border: 1px solid black;border-collapse: collapse;}")
        with tag('body'):
            with tag('table'):
                with tag('tr'):
                    with tag('th'):
                        text("factory count")
                    with tag('th'):
                        text("result")
                    with tag('th'):
                        text("ingredients")
                for production in conso.values():
                    with tag('tr'):
                        with tag('td'):
                            text(production["factoryCount"])
                        with tag('td'):
                            for resultName, resultRate in production["results"].items():
                                text(" + {:.2f}".format(resultRate))
                                doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, resultName+".png"), alt=resultName, title=resultName)
                        with tag('td'):
                            for ingredientName, ingredientRate in production["ingredients"].items():
                                text(" + {:.2f}".format(ingredientRate))
                                doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, ingredientName+".png"), alt=ingredientName, title=ingredientName)
            doc.stag('br')
            with tag('table'):
                with tag('tr'):
                    with tag('th'):
                        text("base")
                for ingredientName, ingredientRate in requesteds.items():
                    with tag('tr'):
                        with tag('td'):
                            text("{:.2f}".format(ingredientRate))
                            doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, ingredientName+".png"), alt=ingredientName, title=ingredientName)

    html = doc.getvalue()
    with open(htmlFilePath, "wb") as htmlFile:
        htmlFile.write(bytes(html, "utf8"))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate SVG recipe dependency graph from factorio game data.')
    parser.add_argument('-f', '--factoriopath', type=str, help="Factorio path to load recipes")
    parser.add_argument('-o', '--open', type=argparse.FileType('r'), help="Load recipes from json file")
    parser.add_argument('-r', '--recipes', type=str, nargs='+', help="To remove recipes list by recipe name")
    parser.add_argument('-i', '--items', type=str, nargs='+', help="To remove items list by ingredients or result name")
    parser.add_argument('-l', '--leafe', action="store_true", help="To remove items at the end of the tree")
    parser.add_argument('-k', '--keep', action="store_true", help="To keep only recipe with at least one result at the end of the tree")
    parser.add_argument('-j', '--json', type=argparse.FileType('w'), help="Generate a recipe json file with the given file name")
    parser.add_argument('-u', '--usage', type=argparse.FileType('w'), help="Generate the given HTML page with for each ingredient the usage")
    parser.add_argument('-d', '--dot', type=argparse.FileType('w'), help="Generate the given graphviz dot file in the folder path")
    parser.add_argument('-c', '--conso', type=argparse.FileType('w'), help="Generate the given HTML page with for each recipes the consume quantity")
    args = parser.parse_args()

    if args.factoriopath:
        factorioVersion = getVersion(args.factoriopath)
        print("Factorio version:", factorioVersion)
        recipesToRemove = set()
        if args.recipes != None:
            recipesToRemove |= set(args.recipes)
        if factorioVersion == "1.1.76":
            recipesToRemove |= {"electric-energy-interface", "loader", "fast-loader", "express-loader"}
        recipes = getRecipes(args.factoriopath, recipesToRemove)

    if args.open:
        recipes = loadRecipes(args.open.name)

    if args.items != None:
        recipesRemoveItem(recipes, set(args.items))
    itemsPngCopyFolderPathes = set()

    if args.leafe:
        removeLeafe(recipes)

    if args.keep:
        keepOnlyLeafe(recipes)

    if args.json:
        writeRecipesJsonFile(recipes, args.json.name)
        print("Recipe jsonfile \"{}\" writen".format(args.json.name))

    if args.usage:
        usage = ingredientsByUsage(recipes)
        itemsPngCopyFolderPath = os.path.join(os.path.dirname(args.usage.name), "img")
        itemsPngCopyFolderPathes.add(itemsPngCopyFolderPath)
        ingredientsByUsage2Html(usage, args.usage.name, "img")

    if args.dot:
        itemsPngCopyFolderPath = os.path.join(os.path.dirname(args.dot.name), "img")
        itemsPngCopyFolderPathes.add(itemsPngCopyFolderPath)
        generateDot(recipes, args.dot.name, "img")

    if args.conso:
        itemsPngCopyFolderPath = os.path.join(os.path.dirname(args.conso.name), "img")
        itemsPngCopyFolderPathes.add(itemsPngCopyFolderPath)
        conso,requesteds = generateConso(recipes, {"production-science-pack": 0.5}, args.conso.name, "img")
        conso2Html(conso, requesteds, args.conso.name, "img")

    if args.factoriopath:
        for folderPath in itemsPngCopyFolderPathes:
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)
            itemsPngCopy(recipes, args.factoriopath, folderPath)
