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
import pathlib
from collections import Counter


debug = False
def printDebug(toPrint: str):
    if debug:
        print(toPrint)

class Recipe(NamedTuple):
    name: str
    ingredients: dict[str, int]
    time: float
    results: dict[str, int]
    category: str
RecipesByName = dict[str, Recipe]
RecipesByResult = dict[str, list[tuple[float,Recipe]]]


class CraftingFactory(NamedTuple):
    name: str
    consumptionType: str
    consumptionQuantity: int
    speed: float
    categories: str
CraftingFactoriesByName = dict[str, CraftingFactory]
CraftingFactoriesByCategories = dict[str, CraftingFactory]


def getVersion(factoriopath:string) -> string:
    # Read info.json file
    with open(os.path.join(factoriopath, "data", "base", "info.json")) as infoFile:
        infoData = infoFile.read()
    # info.json json parse
    infoJson = json.loads(infoData)
    return infoJson["version"]


def getRecipes(factoriopath:string, recipesToRemove:set) -> RecipesByName:
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
        if "category" in recipeLua[index]:
            recipeCategory = recipeLua[index]["category"]
        # Get lua recipe ingrediants
        ingredients = {}
        if "ingredients" in recipeLua[index]:
            ingredientsLua = recipeLua[index]["ingredients"]
        elif "ingredients" in recipeLua[index]["normal"]:
            ingredientsLua = recipeLua[index]["normal"]["ingredients"]
        else:
            raise ValueError("No ingredients found for \"{}\"".format(recipeName))
        # Convert lua recipe ingrediants into python
        for indexIngredient in range(1, len(ingredientsLua)+1):

            if 1 in ingredientsLua[indexIngredient]:
                ingredientName = ingredientsLua[indexIngredient][1]
            elif "name" in ingredientsLua[indexIngredient]:
                ingredientName = ingredientsLua[indexIngredient]["name"]
            else:
                raise ValueError("No ingredient name found for \"{}\" at {}".format(recipeName, indexIngredient))
            if 2 in ingredientsLua[indexIngredient]:
                ingredientAmount = ingredientsLua[indexIngredient][2]
            elif "amount" in ingredientsLua[indexIngredient]:
                ingredientAmount = ingredientsLua[indexIngredient]["amount"]
            else:
                raise ValueError("No ingredient amount found for \"{}\" at {}".format(recipeName, indexIngredient))
            ingredients[ingredientName] = ingredientAmount
        # Get optional recipe energy required
        time = 0.5
        if "energy_required" in recipeLua[index]:
            time = recipeLua[index]["energy_required"]
        elif "normal" in recipeLua[index] and "energy_required" in recipeLua[index]["normal"]:
            time = recipeLua[index]["normal"]["energy_required"]
        # Get recipe result
        results = {}
        if "result" in recipeLua[index]:
            resultCount = 1
            if "result_count" in recipeLua[index]:
                resultCount = recipeLua[index]["result_count"]
            results[recipeLua[index]["result"]] = resultCount
        elif "results" in recipeLua[index]:
            for indexResult in range(1, len(recipeLua[index]["results"])+1):
                if "name" in recipeLua[index]["results"][indexResult]:
                    resultName = recipeLua[index]["results"][indexResult]["name"]
                elif recipeLua[index]["results"][indexResult][1] != None:
                    resultName = recipeLua[index]["results"][indexResult][1]
                else:
                    raise ValueError("No result name found for \"{}\" at {}".format(recipeName, indexResult))
                resultAmount = recipeLua[index]["results"][indexResult]["amount"]
                if "amount" in recipeLua[index]["results"][indexResult]:
                    resultAmount = recipeLua[index]["results"][indexResult]["amount"]
                elif recipeLua[index]["results"][indexResult][2] != None:
                    resultAmount = recipeLua[index]["results"][indexResult][2]
                else:
                    raise ValueError("No result amount found for \"{}\" at {}".format(recipeName, indexResult))
                results[resultName] = resultAmount
        elif "result" in recipeLua[index]["normal"]:
            resultCount = 1
            if "result_count" in recipeLua[index]["normal"]:
                resultCount = recipeLua[index]["normal"]["result_count"]
            results[recipeLua[index]["normal"]["result"]] = resultCount
        else:
            raise ValueError("No result found for \"{}\"".format(recipeName))
        recipes[recipeName] = Recipe(recipeName, ingredients, time, results, recipeCategory)
    # return recipes dict
    return recipes


def fromJsonRecipe(recipeName: str, jsonRecipe: dict) -> Recipe:
    return Recipe(recipeName, jsonRecipe["ingredients"], jsonRecipe["time"], jsonRecipe["results"], jsonRecipe["category"])


def loadRecipes(jsonFilePath: string) -> RecipesByName:
    with open(jsonFilePath, 'r') as jsonFile:
        jsonRecipes = json.load(jsonFile)
    recipes = RecipesByName()
    for recipeName, jsonRecipe in jsonRecipes.items():
        recipes[recipeName] = fromJsonRecipe(recipeName, jsonRecipe)
    return recipes


def recipesByName2recipesByResult(recipesByName: RecipesByName, recipesPreferences: dict[str, list[dict[str, float]]]) -> RecipesByResult:
    recipesByResult = RecipesByResult()
    for resultName, recipesNamesRatiosList in recipesPreferences.items():
        ratioTotal = 0.0
        recipesByResult[resultName] = []
        for recipeNameRatio in recipesNamesRatiosList:
            for recipeName, ratio in recipeNameRatio.items():
                if ratio != "overproduction":
                    ratioTotal += ratio
                recipesByResult[resultName].append((ratio, recipesByName[recipeName]))
        if ratioTotal != 1.0:
            raise ValueError("The ratio sum to produce {} is {} and it must be 1.0".format(resultName, ratioTotal))
    for recipe in recipesByName.values():
        for resultName in recipe.results.keys():
            if resultName in recipesPreferences:
                continue
            elif resultName in recipesByResult:
                raise ValueError("There are more than one recipe to produce {} you have to set your preferencies in consumption data file".format(resultName))
            else:
                recipesByResult[resultName] = [(1.0, recipe)]
    return recipesByResult


def recipesRemoveItem(recipes: RecipesByName, itemsToRemove):
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


def writeRecipesJsonFile(recipes: RecipesByName, filePath: string):
    jsonData = {}
    for recipeName, recipe in recipes.items():
        jsonData[recipeName] = {"ingredients": recipe.ingredients, "time": recipe.time, "results": recipe.results, "category": recipe.category}
    with open(filePath, 'w') as jsonFile:
        json.dump(jsonData, jsonFile, ensure_ascii=False, indent=3)


def ingredientsByUsage(recipes: RecipesByName) -> dict:
    usage = {}
    for recipe in recipes.values():
        for ingredientName in recipe.ingredients.keys():
            if ingredientName not in usage:
                usage[ingredientName] = []
            for result in recipe.results.keys():
                usage[ingredientName].append(result)
    return dict(sorted(usage.items(), key=lambda item: len(item[1]), reverse=True))


def removeLeafe(recipes: RecipesByName):
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


def keepOnlyLeafe(recipes: RecipesByName):
    itemUsedAsIngredient = set()
    for recipe in recipes.values():
        for ingredientName in recipe.ingredients.keys():
            itemUsedAsIngredient.add(ingredientName)
    for recipeName in list(recipes.keys()):
        if len(set(recipes[recipeName].results.keys()).difference(itemUsedAsIngredient))==0:
            del recipes[recipeName]


def itemPngPath(itemName: string, factoriopath: string, itemPngRenames: dict[str,str]) -> string:
    if itemName in itemPngRenames:
        itemName = itemPngRenames[itemName]
    filePathes = [os.path.join(factoriopath, "data", "base", "graphics", "icons", itemName+".png"),
                  os.path.join(factoriopath, "data", "base", "graphics", "icons", "fluid", itemName+".png"),
                  os.path.join(factoriopath, "data", "base", "graphics", "icons", "fluid", "barreling", itemName+".png")]
    for filePath in filePathes:
        if os.path.exists(filePath):
            return filePath
    raise FileNotFoundError("PNG file for \"{}\" not found in factorio path \"{}\"".format(itemName, factoriopath))


def itemPngCopy(itemName: string, factoriopath:string, dstFolderPath: string, itemPngRenames: dict[str,str]):
    imgSrc = Image.open(itemPngPath(itemName, factoriopath, itemPngRenames))
    imgdst = imgSrc.crop((64, 0, 64+32, 32)) # left, upper, right, and lower 
    imgdst.save(os.path.join(dstFolderPath, itemName+".png"))


def itemsPngCopy(recipes: RecipesByName, factoriopath:string, dstFolderPath: string, itemPngRenames: dict[str,str]):
    itemsName = set()
    for recipe in recipes.values():
        for ingredientName in recipe.ingredients.keys():
            if ingredientName not in itemsName:
                itemPngCopy(ingredientName, factoriopath, dstFolderPath, itemPngRenames)
                itemsName.add(ingredientName)
        for resultName in recipe.results.keys():
            if resultName not in itemsName:
                itemPngCopy(resultName, factoriopath, dstFolderPath, itemPngRenames)
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


def generateDot(recipes: RecipesByName, dotFilePath: string, itemsPngCopyFolderPath: string):
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


def loadFactorioData(factorioDataJsonFilePath: string) -> tuple[CraftingFactoriesByName, RecipesByName, set[str], dict[str,str]]:
    with open(factorioDataJsonFilePath, 'r') as factorioDataJsonFile:
        factorioDataJson = json.load(factorioDataJsonFile)
    craftingFactories = {}
    for factoryName, jsonFactory in factorioDataJson["factories"].items():
        if "crafting" in jsonFactory:
            craftingFactories[factoryName] = CraftingFactory(factoryName,
                                                             jsonFactory["consumption"]["type"],
                                                             jsonFactory["consumption"]["quantity"],
                                                             jsonFactory["crafting"]["speed"],
                                                             jsonFactory["crafting"]["categories"])
    recipes = {}
    for recipeName, jsonRecipe in factorioDataJson["recipes-to-add"].items():
        recipes[recipeName] = fromJsonRecipe(recipeName, jsonRecipe)
    return craftingFactories, recipes, set(factorioDataJson["recipes-to-remove"]), factorioDataJson["item-png-renames"]


def loadConsumptionData(consumptionDataJsonFilePath) -> tuple[dict, tuple[dict, list[str]], dict[str, str]]:
    with open(consumptionDataJsonFilePath, 'r') as consumptionDataJsonFile:
        consumptionDataJson = json.load(consumptionDataJsonFile)
    overproductionEndOrder = []
    if "overproduction-end-order" in consumptionDataJson["preferencies"]["recipes"]:
        overproductionEndOrder = consumptionDataJson["preferencies"]["recipes"].pop("overproduction-end-order")
    return consumptionDataJson["requested"], (consumptionDataJson["preferencies"]["recipes"], overproductionEndOrder), consumptionDataJson["preferencies"]["factories"]


def computeConsumptionRates(recipesByResult: RecipesByResult, inputRequestedRates: dict, craftingFactoriesByName: CraftingFactoriesByName, factoriesPreferences: dict, overproductionEndOrder: list[str]) -> tuple[dict, dict, dict]:
    craftingFactoriesByCategories = craftingFactoriesByName2CraftingFactoriesByCategories(craftingFactoriesByName, factoriesPreferences)
    consumptionRate = {}
    requestedRates = dict(inputRequestedRates)
    toProduce = set(requestedRates.keys())
    toProduceAtEnd = set()
    noRecipes = set()
    overproduction = set()
    counter = 0
    ZERO_TOLERANCE = 0.0004
    while len(toProduce)>0 or len(toProduceAtEnd)>0:
        if debug:
            consumption2Html(consumptionRate, {itemName: requestedRates[itemName] for itemName in toProduce|toProduceAtEnd|noRecipes},
                             {itemName: requestedRates[itemName] for itemName in overproduction},
                             "out/{}.html".format(counter), "img", "{}.html".format(counter-1), "{}.html".format(counter+1))
        counter += 1
        # Get the next item to produce
        # If still have item at begin
        if len(toProduce)>0:
            # Get item from begin
            requestedName = toProduce.pop()
            # If a recipe for this item is mark "overproduction"
            if requestedName in recipesByResult:
                isOverproduction = False
                for ratio, _ in recipesByResult[requestedName]:
                    if ratio == "overproduction":
                        isOverproduction = True
                        break
                if isOverproduction:
                    # Move it in end
                    printDebug("{}: move {} to end".format(counter, requestedName))
                    toProduceAtEnd.add(requestedName)
                    continue
        else:
            # Get item from end, but try with order in overproductionEndOrder
            requestedName = ""
            while len(overproductionEndOrder)>0:
                requestedNameTmp = overproductionEndOrder.pop(0)
                if requestedNameTmp in toProduceAtEnd:
                    toProduceAtEnd.remove(requestedNameTmp)
                    requestedName = requestedNameTmp
                    break
            # If no item from overproductionEndOrder get first one
            if requestedName == "":
                requestedName = toProduceAtEnd.pop()
        # Produce this item
        printDebug("{}: need to produce {} of {}".format(counter, requestedRates[requestedName], requestedName))
        assert(not math.isclose(requestedRates[requestedName], 0.0, abs_tol=ZERO_TOLERANCE))
        assert(requestedRates[requestedName] > 0.0)
        if requestedName in recipesByResult:
            # We have at least 1 recipe
            # For each recipe to produce this item
            requestedRate = requestedRates[requestedName]
            for ratio, recipe in recipesByResult[requestedName]:
                if ratio == "overproduction":
                    # Try to produce maximum rate from overproduction
                    productionCount = 0.0
                    for ingredientName, ingredientPerProduction in recipe.ingredients.items():
                        if ingredientName in overproduction:
                            productionCountTmp = -requestedRates[ingredientName] / (ingredientPerProduction / recipe.time)
                            printDebug("{}: try to produce {} with overproduction of {} and recipe {} compute {}".format(counter, requestedName, ingredientName, recipe.name, productionCountTmp))
                            productionCount = max(productionCount, productionCountTmp)
                    if productionCount == 0.0:
                        continue
                else:
                    # Compute rate to produce
                    productionCount = requestedRate * ratio / (recipe.results[requestedName] / recipe.time)
                    printDebug("{}: produce {} of {} with {} recipe".format(counter, requestedRate*ratio, requestedName, recipe.name))
                # If new recipe
                if recipe.name not in consumptionRate:
                    # Add empty template
                    consumptionRate[recipe.name] = {"production-count": 0.0, "factories-name": craftingFactoriesByCategories[recipe.category].name, "factories-count": 0.0, "electric-consumption": 0.0, "category": recipe.category, "results": {}, "ingredients": {}}
                # Update production count
                consumptionRate[recipe.name]["production-count"] += productionCount
                # Update factory count
                consumptionRate[recipe.name]["factories-count"] += productionCount / craftingFactoriesByCategories[recipe.category].speed
                # Update electric consumption
                if craftingFactoriesByCategories[recipe.category].consumptionType == "electric":
                    consumptionRate[recipe.name]["electric-consumption"] = consumptionRate[recipe.name]["factories-count"] * craftingFactoriesByCategories[recipe.category].consumptionQuantity
                # Update item produce
                for resultName, resultPerProduction in recipe.results.items():
                    resultRate = resultPerProduction / recipe.time * productionCount
                    if resultName not in consumptionRate[recipe.name]["results"]:
                        consumptionRate[recipe.name]["results"][resultName] = 0.0
                    consumptionRate[recipe.name]["results"][resultName] += resultRate
                    if resultName not in requestedRates:
                        requestedRates[resultName] = 0.0
                        overproduction.add(resultName)
                    requestedRates[resultName] -= resultRate
                    printDebug("\t{}: produce {} -= {} => {}".format(counter, resultName, resultRate, requestedRates[resultName]))
                    # If almost 0.0 remove it from all list
                    if math.isclose(requestedRates[resultName], 0.0, abs_tol=ZERO_TOLERANCE):
                        printDebug("\t{}: {} == 0.0 remove it from all list".format(counter, resultName))
                        if resultName in toProduce:
                            toProduce.remove(resultName)
                        if resultName in toProduceAtEnd:
                            toProduceAtEnd.remove(resultName)
                        if resultName in overproduction:
                            overproduction.remove(resultName)
                        del requestedRates[resultName]
                    # If was to produce and now overproduction
                    elif requestedRates[resultName] < 0.0 and resultName in toProduce:
                        printDebug("\t{}: overproduction of {}".format(counter, resultName))
                        toProduce.remove(resultName)
                        overproduction.add(resultName)
                # Update item requested
                for ingredientName, ingredientPerProduction in recipe.ingredients.items():
                    ingredientRate = ingredientPerProduction / recipe.time * productionCount
                    if ingredientName not in consumptionRate[recipe.name]["ingredients"]:
                        consumptionRate[recipe.name]["ingredients"][ingredientName] = 0.0
                    consumptionRate[recipe.name]["ingredients"][ingredientName] += ingredientRate
                    if ingredientName not in requestedRates:
                        requestedRates[ingredientName] = 0.0
                        toProduce.add(ingredientName)
                    requestedRates[ingredientName] += ingredientRate
                    printDebug("\t{}: consume {} += {} => {}".format(counter, ingredientName, ingredientRate, requestedRates[ingredientName]))
                    # If almost 0.0 remove it from all list
                    if math.isclose(requestedRates[ingredientName], 0.0, abs_tol=ZERO_TOLERANCE):
                        printDebug("\t{}: {} == 0.0 remove it from all list".format(counter, ingredientName))
                        if ingredientName in toProduce:
                            toProduce.remove(ingredientName)
                        if ingredientName in toProduceAtEnd:
                            toProduceAtEnd.remove(ingredientName)
                        if ingredientName in overproduction:
                            overproduction.remove(ingredientName)
                        del requestedRates[ingredientName]
                    # If was overproduction and now to produce
                    elif requestedRates[ingredientName] > 0.0 and ingredientName in overproduction:
                        printDebug("\t{}: remove from overproduction of {}".format(counter, ingredientName))
                        overproduction.remove(ingredientName)
                        toProduce.add(ingredientName)
                # If this recipe was for overproduction
                if ratio == "overproduction":
                    # Use remaining rate for over ratio
                    if requestedName in requestedRates:
                        requestedRate = requestedRates[requestedName]
                    else:
                        break

        else:
            # No recipe to produce this item
            noRecipes.add(requestedName)
            printDebug("{}: no recipe for {}".format(counter, requestedName))
    return consumptionRate, {itemName: requestedRates[itemName] for itemName in noRecipes}, {itemName: requestedRates[itemName] for itemName in overproduction}


def craftingFactoriesByName2CraftingFactoriesByCategories(craftingFactoriesByName: CraftingFactoriesByName, factoriesPreferences: dict) -> CraftingFactoriesByCategories:
    craftingFactoriesByCategories = CraftingFactoriesByCategories()
    for craftingFactory in craftingFactoriesByName.values():
        for category in craftingFactory.categories:
            ratio = 1.0
            if category in factoriesPreferences:
                if craftingFactory.name == factoriesPreferences[category]:
                    craftingFactoriesByCategories[category] = craftingFactory
            elif category in craftingFactoriesByCategories:
                raise ValueError("There are more than one factory to produce with category {} you have to set your preferencies in consumption data file".format(category))
            else:
                craftingFactoriesByCategories[category] = craftingFactory
    return craftingFactoriesByCategories


def toSiSuffix(quantity: float) -> tuple[float, str]:
    if quantity==0.0:
        return quantity, ""
    exponent = int(math.log10(quantity))
    if exponent>=15:
        return quantity/1.0e15, "P"
    if exponent>=12:
        return quantity/1.0e12, "T"
    if exponent>=9:
        return quantity/1.0e9, "G"
    if exponent>=6:
        return quantity/1.0e6, "M"
    if exponent>=3:
        return quantity/1.0e3, "k"
    return quantity, ""


def consumption2Html(requestedRates: dict, consumptionRate: dict, noRecipes: dict, overproduction: dict, htmlFilePath: string, itemsPngCopyFolderPath: string, prev=None, next=None):
    electricTotal = 0.0
    consumptionRate = dict(sorted(consumptionRate.items()))
    noRecipes = dict(sorted(noRecipes.items()))
    overproduction = dict(sorted(overproduction.items()))
    doc, tag, text = yattag.Doc().tagtext()
    with tag('html'):
        with tag("head"):
            with tag("style"):
                text("table, th, td {border: 1px solid black;border-collapse: collapse;}")
                text("td {text-align: right}")
                text("th {text-align: center}")
        with tag('body'):
            if prev != None:
                with tag('a', href=prev):
                    text("Prev")
            if next != None:
                with tag('a', href=next):
                    text("Next")
            with tag('table'):
                with tag('tr'):
                    with tag('th', colspan=str(len(requestedRates))):
                        text("Requested")
                with tag('tr'):
                    for ingredientName, ingredientRate in requestedRates.items():
                        with tag('td'):
                            text("{:.3f}".format(ingredientRate))
                            doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, ingredientName+".png"), alt=ingredientName, title=ingredientName)
            doc.stag('br')
            with tag('table', id="mainTable"):
                with tag('thead'):
                    with tag('tr'):
                        with tag('th', onclick='sortTable("mainTable", 0)'):
                            text("result")
                        with tag('th', onclick='sortTable("mainTable", 1)'):
                            text("factory count")
                        with tag('th', onclick='sortTable("mainTable", 2)'):
                            text("ingredients")
                        with tag('th', onclick='sortTable("mainTable", 3)'):
                            text("electricity")
                with tag('tbody'):
                    for production in consumptionRate.values():
                        with tag('tr'):
                            with tag('td', ("data-sort", str(max(production["results"].values())))):
                                isFirst = True
                                for resultName, resultRate in production["results"].items():
                                    if not isFirst:
                                        text(" + ")
                                    text("{:.3f}".format(resultRate))
                                    isFirst = False
                                    doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, resultName+".png"), alt=resultName, title=resultName)
                            with tag('td', ("data-sort", str(production["factories-count"]))):
                                text("{:.1f}".format(production["factories-count"]))
                                doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, production["factories-name"]+".png"), alt=production["factories-name"], title=production["factories-name"])
                            with tag('td', ("data-sort", str(max(production["ingredients"].values())))):
                                isFirst = True
                                for ingredientName, ingredientRate in production["ingredients"].items():
                                    if not isFirst:
                                        text(" + ")
                                    text("{:.3f}".format(ingredientRate))
                                    isFirst = False
                                    doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, ingredientName+".png"), alt=ingredientName, title=ingredientName)
                            with tag('td', ("data-sort", str(production["electric-consumption"]))):
                                electric, suffix = toSiSuffix(production["electric-consumption"])
                                text("{:.1f}{}W".format(electric, suffix))
                                electricTotal += production["electric-consumption"]
                with tag('tfoot'):
                    with tag('tr'):
                        doc.stag('td')
                        doc.stag('td')
                        doc.stag('td')
                        with tag('td'):
                            electric, suffix = toSiSuffix(electricTotal)
                            text("{:.1f}{}W".format(electric, suffix))
            doc.stag('br')
            with tag('table'):
                with tag('tr'):
                    with tag('th', colspan=str(len(noRecipes))):
                        text("base")
                with tag('tr'):
                    for ingredientName, ingredientRate in noRecipes.items():
                        with tag('td'):
                            text("{:.3f}".format(ingredientRate))
                            doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, ingredientName+".png"), alt=ingredientName, title=ingredientName)
            doc.stag('br')
            with tag('table'):
                with tag('tr'):
                    with tag('th', colspan=str(len(overproduction))):
                        text("overproduction")
                with tag('tr'):
                    for ingredientName, ingredientRate in overproduction.items():
                        with tag('td'):
                            text("{:.3f}".format(ingredientRate))
                            doc.stag("img", src=os.path.join(itemsPngCopyFolderPath, ingredientName+".png"), alt=ingredientName, title=ingredientName)
            with tag('script'):
                with open("data/script.js", 'r') as javaScriptFile:
                    doc.asis("\n")
                    doc.asis(javaScriptFile.read())
    html = yattag.indent(doc.getvalue())
    with open(htmlFilePath, "wb") as htmlFile:
        htmlFile.write(bytes(html, "utf8"))


def loadGroups(jsonFilePath: string) -> dict[str, list[str]]:
    with open(jsonFilePath, 'r') as jsonFile:
        recipesGroups = json.load(jsonFile)
    return recipesGroups


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Generate recipes data from factorio game data.""")
    # Recipes loarders
    recipesLoarderArgs = parser.add_mutually_exclusive_group(required=True)
    recipesLoarderArgs.add_argument("--factorio-path", type=pathlib.Path, help="Load recipes from factorio path")
    recipesLoarderArgs.add_argument("--input-json", type=pathlib.Path, help="Load recipes from json file")
    # Recipes filters
    recipesFilterArgs = parser.add_argument_group("Recipes filters")
    recipesFilterArgs.add_argument("--remove-recipes", type=str, nargs='+', help="To remove recipes list by recipe name")
    recipesFilterArgs.add_argument('--remove-items', type=str, nargs='+', help="To remove items list by ingredients or result name")
    recipesFilterArgs.add_argument("--remove-leafes", action="store_true", help="To remove items at the end of the tree")
    recipesFilterArgs.add_argument("--keep-leafes-only", action="store_true", help="To keep only recipe with at least one result at the end of the tree")
    # Recipes writers
    recipesWritersArgs = parser.add_argument_group("Recipes writers")
    recipesWritersArgs.add_argument("--output-json", type=pathlib.Path, help="Generate the given json file")
    recipesWritersArgs.add_argument("--output-html-usage", type=pathlib.Path, help="Generate the given HTML page with for each ingredient the usage")
    recipesWritersArgs.add_argument("--output-dot", type=pathlib.Path, help="Generate the given graphviz dot file")
    recipesWritersArgs.add_argument("--output-html-consumption", type=pathlib.Path, help="Generate the given HTML page with for each recipes the consume rate")
    recipesWritersArgs.add_argument('--output-groups-dir', type=pathlib.Path, help="Folder path to generate recipe file from group")
    recipesWritersArgs.add_argument('--output-png-dir', type=pathlib.Path, help="Folder path to generate png for each item from factorio path")
    # Additionnal input arguments
    recipesAddInputsArgs = parser.add_argument_group("Additionnal input arguments")
    recipesAddInputsArgs.add_argument('--input-factorio-data', type=pathlib.Path, help="Recipes and factories data used when generate consumption and recipes from factorio path")
    recipesAddInputsArgs.add_argument('--input-consumption-data', type=pathlib.Path, help="Consumption requested and preferencies used when generate consumption")
    recipesAddInputsArgs.add_argument('--input-groups-data', type=pathlib.Path, help="Generate a json recipe file for each group in the given file")
    args = parser.parse_args()

    # Load factorio data
    craftingFactoriesByName = {}
    recipesToAdd = RecipesByName()
    recipesToRemove = set()
    itemPngRenames = {}
    if args.input_factorio_data:
        craftingFactoriesByName, recipesToAdd, recipesToRemove, itemPngRenames = loadFactorioData(args.input_factorio_data)

    # Recipes loarders
    if args.factorio_path:
        factorioVersion = getVersion(args.factorio_path)
        print("Load recipes from factorio version {}".format(factorioVersion))
        recipesByName = getRecipes(args.factorio_path, recipesToRemove)
        recipesByName.update(recipesToAdd)
    if args.input_json:
        print("Load recipes from {}".format(args.input_json))
        recipesByName = loadRecipes(args.input_json)

    # Recipes filters
    if args.remove_recipes:
        print("Filter recipes {}".format(args.remove_recipes))
        for recipeToRemove in args.remove_recipes:
            recipesByName.popitem(recipeToRemove)
    if args.remove_items:
        print("Filter items {}".format(args.remove_items))
        recipesRemoveItem(recipesByName, set(args.remove_items))
    if args.remove_leafes:
        print("Filter leafes")
        removeLeafe(recipesByName)
    if args.keep_leafes_only:
        print("Keep only leafes")
        keepOnlyLeafe(recipesByName)

    # Recipes writers
    if args.output_json:
        writeRecipesJsonFile(recipesByName, args.output_json)
        print("Recipe jsonfile \"{}\" writen".format(args.output_json))
    if args.output_html_usage:
        usage = ingredientsByUsage(recipesByName)
        ingredientsByUsage2Html(usage, args.output_html_usage, "img")
        print("HTML file \"{}\" writen".format(args.output_html_usage))
    if args.output_dot:
        generateDot(recipesByName, args.output_dot, "img")
        print("Graphviz dot file \"{}\" writen".format(args.output_dot))
    if args.output_png_dir:
        if not args.factorio_path:
            raise ValueError("To generate png dir you need to provide factorio path")
        if not os.path.exists(args.output_png_dir):
            os.makedirs(args.output_png_dir)
        itemsPngCopy(recipesByName, args.factorio_path, args.output_png_dir, itemPngRenames)
        print("Item png file in {} writen".format(args.output_png_dir))
    if args.output_html_consumption:
        if not args.input_consumption_data:
            raise ValueError("To generate consumtion you need to provide consumption data file")
        requestedRates, recipesPreferences, factoriesPreferences = loadConsumptionData(args.input_consumption_data)
        recipesByResult = recipesByName2recipesByResult(recipesByName, recipesPreferences[0])
        consumption, noRecipes, overproduction = computeConsumptionRates(recipesByResult, requestedRates, craftingFactoriesByName, factoriesPreferences, recipesPreferences[1])
        consumption2Html(requestedRates, consumption, noRecipes, overproduction, args.output_html_consumption, "img")
        print("HTML consumption file \"{}\" writen".format(args.output_html_consumption))
    if args.output_groups_dir:
        recipesGroups = loadGroups(args.output_groups_dir)
        outFolderPath = "."
        if args.input_groups_data:
            outFolderPath = args.input_groups_data
        for groupName, recipesNames in recipesGroups.items():
            recipesGroup = {}
            for recipeName in recipesNames:
                recipesGroup[recipeName] = recipesByName[recipeName]
            writeRecipesJsonFile(recipesGroup, os.path.join(outFolderPath, "recipes"+groupName[0].upper()+groupName[1:]+".json"))
