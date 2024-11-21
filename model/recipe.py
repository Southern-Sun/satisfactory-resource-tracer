from typing import Literal

from pydantic import BaseModel

from model.part import Part

class Ingredient(BaseModel):
    name: str
    quantity: float
    raw_quantity: float

class Recipe(BaseModel):
    name: str
    machine: str
    time: float
    energy: int
    inputs: list[Ingredient]
    outputs: list[Ingredient]

    @property
    def product(self) -> Ingredient:
        return self.outputs[0]
    
    @property
    def byproduct(self) -> Ingredient:
        if len(self.outputs) < 2:
            return None
        return self.outputs[1]

    def scale_to_input(self, part_name: str, amount: float) -> float:
        return self.scale_to("input", part_name=part_name, amount=amount)

    def scale_to_output(self, part_name: str, amount: float) -> float:
        return self.scale_to("output", part_name=part_name, amount=amount)

    def scale_to(
        self, direction: Literal["input", "output"], part_name: str, amount: float
    ) -> float:
        if direction == "input":
            ingredients = self.inputs
        else:
            ingredients = self.outputs

        for ingredient in ingredients:
            if part_name == ingredient.name:
                part = ingredient
                break
        else:
            raise KeyError(f"No part name {part_name} in recipe {self.name}")
        
        return amount / part.quantity


if __name__ == '__main__':
    with open("model/all_recipes.json", "r") as f:
        import json
        recipes = json.load(f)

    print(Recipe(**recipes[0]))
