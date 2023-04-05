MAIN=electronic-circuit iron-plate iron-gear-wheel steel-plate advanced-circuit copper-plate pipe explosives coal plastic-bar

all: out/recipesRobotAll.svg out/recipesBeltInserterAll.svg \
	out/recipesChestAll.svg out/recipesMall5All.svg \
	out/recipesMainAll.svg out/recipesMall1All.svg \
	out/recipesMall2All.svg out/recipesMilitaryScienceAll.svg \
	out/recipesCopperCableAll.svg out/recipesProductionScienceAll.svg \
	out/recipesOnlyOnceAll.svg out/recipesMall3All.svg \
	out/recipesRocketAll.svg out/recipesMall4All.svg \
	out/recipesModuleAll.svg out/recipesUraniumAll.svg \
	out/recipesNoNeedAll.svg out/recipesSpidertronAll.svg \
	out/recipesAmmoAll.svg out/consumptionAllScience.html \
	out/consumptionProductionScience.html out/consumptionTest.html

/tmp/%All.dot: /tmp/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --input-json $< --output-dot $@

/tmp/%Wm.dot: /tmp/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --input-json $< --items $(MAIN) --output-dot $@

out/%.svg: /tmp/%.dot out/img
	cd out && dot -Tsvg $< -o ../$@

out/recipesAll.json: factorioRecipeDependency.py data/factorio-1.1.76.json
	./factorioRecipeDependency.py --factorio-path ~/.steam/debian-installation/steamapps/common/Factorio/ --input-factorio-data data/factorio-1.1.76.json --output-json $@

out/img: factorioRecipeDependency.py
	./factorioRecipeDependency.py --factorio-path ~/.steam/debian-installation/steamapps/common/Factorio/ --input-factorio-data data/factorio-1.1.76.json --output-png-dir $@

out/recipesAllUsage.html: out/recipesAll.json out/img factorioRecipeDependency.py
	./factorioRecipeDependency.py --input-json $< --output-html-usage $@

out/consumption%.html: data/consumption%.json out/img out/recipesAll.json data/factorio-1.1.76.json factorioRecipeDependency.py data/script.js
	./factorioRecipeDependency.py --input-json out/recipesAll.json --output-html-consumption $@ --input-factorio-data data/factorio-1.1.76.json --input-consumption-data $<

/tmp/recipes%.json: out/recipesAll.json data/recipesGroups.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --input-json $< --output-groups-dir data/recipesGroups.json --input-groups-data /tmp/
