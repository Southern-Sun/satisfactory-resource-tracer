from typing import Literal
import json
from dataclasses import dataclass

from model.recipe import Recipe


@dataclass
class Codex:
    def __init__(self, recipe_file: str) -> None:
        with open(recipe_file, "r") as f:
            self.recipes: list[Recipe] = [Recipe(**data) for data in json.load(f)]

    def get_recipe(self, name: str) -> Recipe:
        name = name.lower()
        for recipe in self.recipes:
            if recipe.name.lower() == name:
                return recipe
        raise KeyError(f"No such recipe '{name}'")

    def get_recipes(self, names: list[str]) -> list[Recipe]:
        return [self.get_recipe(name) for name in names]

    def get_recipes_by_part(
        self,
        part: str,
        by: Literal["any", "ingredient", "product"] = "product",
        exclude_machines: set[str] = None,
    ) -> list[Recipe]:
        if exclude_machines is None:
            exclude_machines = {"Packager"}

        results = []
        for recipe in self.recipes:
            if recipe.machine in exclude_machines:
                continue

            components = (recipe.inputs if by in ("any", "ingredient") else []) + (
                [recipe.product] if by in ("any", "product") else []
            )
            if part in {ingredient.name for ingredient in components}:
                results.append(recipe)

        return results
