from dataclasses import dataclass, field
from typing import Callable, Any, Literal
from functools import partial
from collections import defaultdict
from math import ceil

from model.recipe import Recipe
from model.codex import Codex

# Constants for printing Factory tree structure
ELBOW = "└─"
PIPE = "│ "
TEE = "├─"
BLANK = "  "


@dataclass
class Node:
    recipe: Recipe
    quantity: float = 1.0
    parent: "Node" = None
    children: list["Node"] = field(default_factory=list)

    def __str__(self) -> str:
        return repr(Node(
            recipe=self.recipe,
            quantity=self.quantity,
            parent=self.parent.recipe.name,
            children=[child.recipe.name for child in self.children]
        ))


def simplest_recipe(options: list[Recipe]) -> Recipe:
    return min(options, key=lambda recipe: len(recipe.inputs))

def max_output(options: list[Recipe]) -> Recipe:
    return max(options, key=lambda recipe: recipe.product.quantity)

def preferred_names(options: list[Recipe], names: set[str]) -> Recipe:
    new_options = [recipe for recipe in options if recipe.name in names]
    return max_output(new_options or options)


class Factory:
    def __init__(self, registry: Codex, target: Recipe | Node) -> None:
        self.registry = registry
        if isinstance(target, Recipe):
            self.map = Node(recipe=target)
        elif isinstance(target, Node):
            self.map = target

    def __str__(self) -> str:
        """
        Print out the Factory line by line like:
        {recipe_name}: {machine} x{qty} -> {product} @ {qty}/min

        Plutonium Fuel Unit: Assembler x10 -> Plutonium Fuel Rod @ 5/min
          |- Instant Plutonium Cell: Particle Accelerator x11 -> Encased Plutonium Cell @ 110/min
          |  |- Something else
          |  |-
          |-
        """
        lines = []
        self.print_tree(self.map, lines=lines)
        return "\n".join(lines)

    def print_tree(self, node: Node, lines: list, last=True, header="") -> None:
        recipe = node.recipe
        data = (
            f"{recipe.name}: {recipe.machine} x{node.quantity:.02f} -> " +
            f"{recipe.product.name} @ {node.quantity * recipe.product.quantity:.02f}" +
            (
                f" + {recipe.byproduct.name} @ {node.quantity * recipe.byproduct.quantity:.02f}" 
                if recipe.byproduct else ""
            )
        )
        if not lines:
            lines.append(data)
        else:
            lines.append(header + (ELBOW if last else TEE) + data)

        if not node.children:
            return

        for i, child in enumerate(node.children):
            self.print_tree(
                child,
                lines=lines,
                header=header + (BLANK if last else PIPE),
                last=i == len(node.children) - 1,
            )

    def build(
        self,
        fitness_func: Callable = None,
        exclude_machines: set[str] = None,
        existing_products: set[str] = None,
        max_depth: int = -1,
    ):
        if fitness_func is None:
            fitness_func = simplest_recipe

        if exclude_machines is None:
            exclude_machines = {"Packager"}

        products = existing_products or set()

        # Prune existing factory if it exists
        # Imagine seeing this in C++ 
        self.map.children = []

        self._build_factory(
            self.map,
            fitness_func=fitness_func,
            exclude_machines=exclude_machines,
            products=products,
            depth=max_depth,
        )

    def _build_factory(
        self, node: Node, fitness_func: Callable, exclude_machines: set[str], products: set[str], depth: int
    ) -> None:
        if depth == 0:
            return

        if node.recipe.product.name in products:
            return
        else:
            products.add(node.recipe.product.name)

        for input in node.recipe.inputs:
            options = self.registry.get_recipes_by_part(
                input.name, exclude_machines=exclude_machines
            )
            if not options:
                continue

            new_node = Node(fitness_func(options), parent=node)
            node.children.append(new_node)

            self._build_factory(
                new_node,
                fitness_func=fitness_func,
                exclude_machines=exclude_machines,
                products=products,
                depth=depth - 1,
            )

    def find_node(self, criterion: str, how: Literal["product"] = "product") -> Node:
        if how == "product":
            return self._find_node_by_product(self.map, criterion)

    def _find_node_by_product(self, node: Node, product: str) -> Node:
        if node.recipe.product.name == product:
            return node
        
        for child in node.children:
            result = self._find_node_by_product(child, product)
            if result is not None:
                return result
            
        return None

    def scale(self, part_name: str, target_quantity: float) -> None:
        # Find the node that produces that part
        node = self.find_node(part_name)
        node.quantity = target_quantity / node.recipe.product.quantity

        for child in node.children:
            self._scale_node_by_product(child, node)

        if node.parent is not None:
            self._scale_node_by_ingredient(node.parent, node)

    
    def _scale_node_by_product(self, node: Node, match_node: Node) -> None:
        # Find the right input in match_node
        product = node.recipe.product.name
        for ingredient in match_node.recipe.inputs:
            if ingredient.name == product:
                target_quantity = ingredient.quantity * match_node.quantity
                break
        else:
            raise ValueError("Product not found in recipe tree")
        
        node.quantity = target_quantity / node.recipe.product.quantity

        for child in node.children:
            self._scale_node_by_product(child, node)

    def _scale_node_by_ingredient(self, node: Node, match_node: Node) -> None:
        # Determine which ingredient to scale by
        product = match_node.recipe.product.name
        target_quantity = match_node.recipe.product.quantity * match_node.quantity
        for ingredient in node.recipe.inputs:
            if ingredient.name == product:
                node.quantity = target_quantity / ingredient.quantity
                break
        else:
            raise ValueError("Product not found in recipe tree")
        
        for child in node.children:
            if child is match_node:
                continue
            self._scale_node_by_product(child, node)

        if node.parent is not None:
            self._scale_node_by_ingredient(node.parent, node)

    def tally_machines(self) -> dict:
        machines = defaultdict(int)
        self._tally_machines(self.map, machines)
        return machines

    def _tally_machines(self, node: Node, machines: dict) -> None:
        machines[node.recipe.machine] += ceil(node.quantity)
        for child in node.children:
            self._tally_machines(child, machines)

    def new_factory_from_product(self, product: str) -> "Factory":
        node = self.find_node(product)
        return Factory(self.registry, node)

if __name__ == "__main__":
    codex = Codex("model/all_recipes.json")
    target = codex.get_recipe("Plutonium Fuel Unit")

    recipe_names = (
        "Instant Plutonium Cell",
        "Non-Fissile Uranium",
        "Aluminum Casing",
        "Pure Aluminum Ingot",
        "Instant Scrap",
        "Silica",
        "Nitrogen Gas Well Pure",
        "Water Extractor",
        "Iron Plate",
        "Iron Ingot"
    )

    factory = Factory(target=target, registry=codex)
    # factory.map.children = [Node(recipe) for recipe in codex.get_recipes(names)]
    factory.build(
        max_depth=-1, 
        fitness_func=partial(preferred_names, names=recipe_names),
        existing_products={
            "Pressure Conversion Cube",
            "Uranium Waste",
            "Aluminum Ingot"
        }
    )

    factory.scale("Uranium Waste", 600)
    print(factory)
    al_factory = factory.new_factory_from_product("Aluminum Ingot")
    al_factory.build(fitness_func=partial(preferred_names, names=recipe_names))
    al_factory.scale("Bauxite", 2400)
    print(al_factory)

    

    # for thing in codex.get_recipes_by_part("Pressure Conversion Cube", by="any"):
    #     print(thing)
