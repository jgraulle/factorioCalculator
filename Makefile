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
	out/recipesAmmoAll.svg out/recipesAllConso.html \
	out/recipesAll.json

out/%Usage.html: data/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --open $< --usage $@

out/%All.dot: data/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --open $< --dot $@

out/%Wm.dot: data/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --open $< --items $(MAIN) --dot $@

out/%.svg: out/%.dot
	cd out && dot -Tsvg ../$< -o ../$@

out/recipesAll.json: factorioRecipeDependency.py
	./factorioRecipeDependency.py --factoriopath ~/.steam/debian-installation/steamapps/common/Factorio/ --json $@

out/recipesAllUsage.html: out/recipesAll.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --open $< --usage $@

out/recipesAllConso.html: out/recipesAll.json factorioRecipeDependency.py
	./factorioRecipeDependency.py --open $< --conso $@
