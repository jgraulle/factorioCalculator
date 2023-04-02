#!/bin/python3
# ./factorioRecipeDependency.py ~/.steam/debian-installation/steamapps/common/Factorio/ -r small-electric-pole shotgun combat-shotgun wooden-chest basic-oil-processing coal-liquefaction heavy-oil-cracking light-oil-cracking -i steel-plate electronic-circuit iron-plate iron-gear-wheel advanced-circuit processing-unit copper-plate pipe -d out && (cd out && dot -Tsvg itemDependency.dot -o itemDependency.svg)
# todo:
# - declare named tuple for recipe
# - can set ouput file name for dot and html


import argparse
import string
import json
import os
import lupa
import shutil
from PIL import Image
import yattag

def getVersion(factoriopath:string) -> string:
    # Read info.json file
    with open(os.path.join(factoriopath, "data", "base", "info.json")) as infoFile:
        infoData = infoFile.read()
    # info.json json parse
    infoJson = json.loads(infoData)
    return infoJson["version"]


def getRecipes(factoriopath:string, recipesToRemove:set) -> dict:
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
        recipes[recipeName] = {}
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
        recipes[recipeName]["ingredients"] = ingredients
        # Get optional recipe energy required
        energyRequired = recipeLua[index]["energy_required"]
        if energyRequired != None:
            recipes[recipeName]["energy_required"] = energyRequired
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
        recipes[recipeName]["results"] = results
    # return recipes dict
    return recipes


def recipesRemoveItem(recipes: dict, itemsToRemove):
    recipesToDelete = []
    for recipeName, recipe in recipes.items():
        for ingredientName in list(recipe["ingredients"].keys()):
            if ingredientName in itemsToRemove:
                del recipe["ingredients"][ingredientName]
        for resultName in list(recipe["results"].keys()):
            if resultName in itemsToRemove:
                del recipe["results"][resultName]
        if len(recipe["ingredients"])==0 or len(recipe["results"])==0:
            recipesToDelete.append(recipeName)
    for recipeName in recipesToDelete:
        del recipes[recipeName]

def writeJsonFile(data:dict, fileName:string):
    with open(fileName.name, 'w') as jsonFile:
        json.dump(data, jsonFile, ensure_ascii=False, indent=3)


def ingredientsByUsage(recipes:dict) -> dict:
    usage = {}
    for recipe in recipes.values():
        for ingredientName in recipe["ingredients"].keys():
            if ingredientName not in usage:
                usage[ingredientName] = []
            for result in recipe["results"].keys():
                usage[ingredientName].append(result)
    return dict(sorted(usage.items(), key=lambda item: len(item[1]), reverse=True))


def removeLeafe(recipes:dict):
    itemUsedAsIngredient = set()
    for recipe in recipes.values():
        for ingredientName in recipe["ingredients"].keys():
            itemUsedAsIngredient.add(ingredientName)
    for recipe in recipes.values():
        for resultName in list(recipe["results"].keys()):
            if resultName not in itemUsedAsIngredient:
                del recipe["results"][resultName]


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


def itemsPngCopy(recipes: dict, factoriopath:string, dstFolderPath: string):
    itemsName = set()
    for recipe in recipes.values():
        for ingredientName in recipe["ingredients"].keys():
            if ingredientName not in itemsName:
                itemPngCopy(ingredientName, factoriopath, dstFolderPath)
                itemsName.add(ingredientName)
        for resultName in recipe["results"].keys():
            if resultName not in itemsName:
                itemPngCopy(resultName, factoriopath, dstFolderPath)
                itemsName.add(resultName)


def ingredientsByUsage2Html(ingredientsByUsage:dict, htmlFilePath: string):
    doc, tag, text = yattag.Doc().tagtext()
    with tag('html'):
        with tag("head"):
            with tag("style"):
                text("table, th, td {border: 1px solid black;border-collapse: collapse;}")
        with tag('body'):
            with tag('table'):
                with tag('tr'):
                    with tag('th'):
                        text("ingredient")
                    with tag('th'):
                        text("count")
                    with tag('th'):
                        text("used by")
                for ingredientName, resultList in ingredientsByUsage.items():
                    with tag('tr'):
                        with tag('td'):
                            doc.stag("img", src=ingredientName+".png", alt=ingredientName, title=ingredientName)
                        with tag('td'):
                            text(len(resultList))
                            with tag('td'):
                                for resultName in resultList:
                                    doc.stag("img", src=resultName+".png", alt=resultName, title=resultName)

    html = doc.getvalue()
    with open(htmlFilePath, "wb") as htmlFile:
        htmlFile.write(bytes(html, "utf8"))


def generateDot(ingredientsByUsage:dict, dotFilePath: string):
    def convertItemName(name:str):
        return name.replace("-", "_").replace(" ", "_ ")
    def generateNode(ingredientName:str) -> str:
        return '   {0} [shape=none, label="", image="{1}.png"];\n'.format(convertItemName(ingredientName), ingredientName)
    with open(dotFilePath, "w") as dotFile:
        dotFile.write("digraph {\n")
        itemsName = set()
        # Write Node
        for recipe in recipes.values():
            for ingredientName in recipe["ingredients"].keys():
                if ingredientName not in itemsName:
                    dotFile.write(generateNode(ingredientName))
                    itemsName.add(ingredientName)
            for resultName in recipe["results"].keys():
                if resultName not in itemsName:
                    dotFile.write(generateNode(resultName))
                    itemsName.add(resultName)
        dotFile.write("\n")
        # Write edge 
        for recipe in recipes.values():
            ingredients = "{"
            for resultName in recipe["results"].keys():
                ingredients = ', '.join(convertItemName(ingredientName) for ingredientName in recipe["ingredients"].keys())
                dotFile.write("   {{{}}} -> {}\n".format(ingredients, convertItemName(resultName)))
        dotFile.write("}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate SVG recipe dependency graph from factorio game data.')
    parser.add_argument('factoriopath')
    parser.add_argument('-r', '--recipes', type=str, nargs='+', help="To remove recipes list by recipe name")
    parser.add_argument('-i', '--items', type=str, nargs='+', help="To remove items list by ingredients or result name")
    parser.add_argument('-l', '--leafe', action="store_true", help="To remove items at the end of the tree")
    parser.add_argument('-j', '--json', type=argparse.FileType('w'), help="Generate a recipe json file with the given file name")
    parser.add_argument('-u', '--usage', type=str, help="Generate a HTML page with for each ingredient the usage")
    parser.add_argument('-d', '--dot', type=str, help="Generate a graphviz dot file in the folder path")
    args = parser.parse_args()

    factorioVersion = getVersion(args.factoriopath)
    print("Factorio version:", factorioVersion)

    recipesToRemove = set()
    if args.recipes != None:
        recipesToRemove |= set(args.recipes)
    if factorioVersion == "1.1.76":
        recipesToRemove |= {"electric-energy-interface", "loader", "fast-loader", "express-loader"}

    recipes = getRecipes(args.factoriopath, recipesToRemove)
    if args.items != None:
        recipesRemoveItem(recipes, set(args.items))
    itemsPngCopyFolderPath = set()

    if args.leafe:
        removeLeafe(recipes)

    if args.json:
        writeJsonFile(recipes, args.json)
        print("Recipe jsonfile \"{}\" writen".format(args.json.name))

    if args.usage:
        usage = ingredientsByUsage(recipes)
        itemsPngCopyFolderPath.add(args.usage)
        ingredientsByUsage2Html(usage, os.path.join(args.usage, "ingredientsByUsage.html"))

    if args.dot:
        itemsPngCopyFolderPath.add(args.dot)
        generateDot(recipes, os.path.join(args.dot, "itemDependency.dot"))

    for folderPath in itemsPngCopyFolderPath:
        itemsPngCopy(recipes, args.factoriopath, folderPath)
