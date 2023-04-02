MAIN=electronic-circuit iron-plate iron-gear-wheel steel-plate advanced-circuit copper-plate pipe explosives coal plastic-bar

all: out/recipesBeginToRobotUsage.html out/recipesRobotAll.svg \
	out/recipesBeginToRobotWm.svg out/recipesBeltInserterAll.svg \
	out/recipesChestAll.svg out/recipesAssemblingMachineAll.svg \
	out/recipesMainAll.svg out/recipesMall1All.svg \
	out/recipesMall2All.svg out/recipesMilitaryScienceAll.svg \
	out/recipesCopperCableAll.svg out/recipesProductionScienceAll.svg \
	out/recipesOnlyOnceAll.svg out/recipesMall3All.svg \
	out/recipesRocketAll.svg out/recipesMall4All.svg \
	out/recipesModuleAll.svg out/recipesUraniumAll.svg \
	out/recipesNoNeedAll.svg out/recipesSpidertronAll.svg \
	out/recipesAmmoAll.svg out/recipesAllUsage.html

out/%Usage.html: data/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py -o $< -u $@

out/%All.dot: data/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py -o $< -d $@

out/%Wm.dot: data/%.json factorioRecipeDependency.py
	./factorioRecipeDependency.py -o $< -i $(MAIN) -d $@

out/%.svg: out/%.dot
	cd out && dot -Tsvg ../$< -o ../$@

out/recipesAllUsage.html: factorioRecipeDependency.py
	./factorioRecipeDependency.py -f ~/.steam/debian-installation/steamapps/common/Factorio/ -u $@