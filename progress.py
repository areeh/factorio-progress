#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyperclip", "matplotlib"]
# ///

from copy import deepcopy
from dataclasses import dataclass
import dataclasses
from typing import Any
from collections.abc import Callable
from pyperclip import copy
from base64 import b64encode
import zlib
import matplotlib as mpl
import json


@dataclass
class PBarConfig:
    position: tuple[int, int]
    signal_name: str = "parameter-0"
    prefix: str = ""
    cmap: Callable[[float], Any] | None = None
    length: int = 10  # Number of blocks
    step_size: int = 1  # Number of steps between blocks


def json_to_blueprint(json: str) -> str:
    json_bytes = json.encode("utf-8")
    compressed = zlib.compress(json_bytes, level=9)
    return "0" + b64encode(compressed).decode("utf-8")


def linspace(start: float, stop: float, num: int = 50) -> list[float]:
    step = (stop - start) / (num - 1)
    return [start + step * i for i in range(num)]


def generate_pbar_conditions(config: PBarConfig) -> list[dict[str, Any]]:
    template: dict[str, Any] = {
        "condition": {
            "first_signal": {"name": config.signal_name},
            "constant": 0,  # To be filled in later
            "comparator": "=",
        },
        "icon": {"name": config.signal_name},
        "text": "",  # To be filled in later
    }

    # Uses the block chars '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█'
    substeps = "\u258f\u258e\u258d\u258c\u258b\u258a\u2589\u2588"
    # Use border chars '╸', '━'
    # substeps = "╸━"
    print(f"Using character set: `{substeps}`")
    divs = len(substeps)
    max_threshold = config.length * divs

    steps = list(range(-1, max_threshold, config.step_size))
    if steps[-1] < max_threshold - 1:
        steps.append(max_threshold - 1)

    conditions: list[dict[str, Any]] = []
    for step in steps:
        num_before = max(step // divs, 0)
        num_cur = step % divs
        num_after = config.length - num_before

        if step == -1:
            bar = ""
        else:
            bar = substeps[-1] * num_before
            num_after -= 1
            bar += substeps[num_cur]

        if config.cmap is not None:
            color = config.cmap(step / (max_threshold - 1))
            color = mpl.colors.rgb2hex(color)
            if bar:
                bar = f"[color={color}]{bar}[/color]"

        step += 1
        postfix = f"{step / (config.length * divs) * 100:>5.1f}%"
        num_postfix_prefix = len(postfix) - len(postfix.strip())
        postfix = postfix.strip()

        end = substeps[-1] * num_after + "0" * num_postfix_prefix
        if end and config.cmap is not None:
            color = config.cmap(step / (max_threshold - 1))
            color = mpl.colors.rgb2hex(color)
            end = f"[color={color}]{end}[/color]"

        pbar = bar + end
        text = f"{config.prefix}[font=technology-slot-level-font]{pbar}[/font]  {postfix}"

        # Fill in the template
        cond: dict[str, Any] = deepcopy(template)
        cond["condition"]["constant"] = step
        cond["text"] = text

        conditions.append(cond)
        # print(f"{step:<3d}: `{text}`")

    # Set the last condition to be >= the max threshold and first to <= 0
    conditions[0]["condition"]["comparator"] = "<="
    conditions[-1]["condition"]["comparator"] = ">="
    return conditions


def generate_pbar_entity(config: PBarConfig, entity_number: int) -> dict[str, Any]:
    conditions = generate_pbar_conditions(config)
    return {
        "entity_number": entity_number,
        "name": "display-panel",
        "position": {
            "x": config.position[0] + 0.5,
            "y": config.position[1] + 0.5,
        },
        "direction": 8,
        "control_behavior": {
            "parameters": conditions,
            "text": "",
            "icon": {"name": config.signal_name},
        },
        "always_show": True,
    }


def generate_bp_string(configs: list[PBarConfig]) -> str:
    entities: list[dict[str, Any]] = []
    parameters: list[dict[str, str]] = []
    for i, config in enumerate(configs, 1):
        entities.append(generate_pbar_entity(config, i))
        if "parameter" in config.signal_name:
            parameters.append({"type": "id", "id": config.signal_name})

    bp_json = {
        "blueprint": {
            "icons": [{"signal": {"name": "display-panel"}, "index": 1}],
            "entities": entities,
            "wires": [],
            "parameters": parameters,
            "item": "blueprint",
            "version": 562949954273281,
        }
    }
    return json_to_blueprint(json.dumps(bp_json))


if __name__ == "__main__":
    mpl_cmap = mpl.colormaps.get_cmap("RdBu")

    def step_cmap(cmap: Any) -> Callable[[float], Any]:
        return lambda x: cmap(round(x * 10) / 10)

    def const_color(hex: str) -> Callable[[float], str]:
        return lambda x: hex

    base_config = PBarConfig(
        position=(0, 0),
        signal_name="parameter-0",
        prefix="",
        cmap=None,
        length=10,
        step_size=1,
    )
    colors: list[tuple[str, str]] = [
        ("#8e1dcc", "production-science-pack"),  # purple
        ("#e82195", "electromagnetic-science-pack"),  # fulgaro pink
        ("#e94040", "automation-science-pack"),  # red science
        ("#ff9a25", "metallurgic-science-pack"),  # vulcanus orange
        ("#f5e45b", "utility-science-pack"),  # yellow science
        ("#a2b90b", "agricultural-science-pack"),  # gleba green
        ("#55f261", "logistic-science-pack"),  # green science
        ("#3ec5e3", "chemical-science-pack"),  # blue science
        ("#2c46c5", "cryogenic-science-pack"),  # aquilo blue
        ("#29274f", "promethium-science-pack"),  # prometheus
        ("#71788f", "military-science-pack"),  # military gray
        ("#f9f9f9", "space-science-pack"),  # space white
    ]

    configs: list[PBarConfig] = []
    for i, (color, signal_name) in enumerate(colors):
        config = dataclasses.replace(
            base_config,
            position=(0, 2 * i),
            signal_name=signal_name,
            cmap=const_color(color),
        )
        configs.append(config)

    bp_string = generate_bp_string(configs)
    copy(bp_string)
