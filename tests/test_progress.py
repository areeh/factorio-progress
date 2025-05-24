from progress import PBarConfig
from progress import generate_pbar_conditions
import pytest
from typing import Any
from pytest import CaptureFixture


import re

import math


def sample_evenly_interpolated(
    data: list[dict[str, Any]], num_samples: int
) -> list[dict[str, Any]]:
    """
    Samples a specific number of items from a list at roughly even intervals,
    including the first and last elements if num_samples > 1.

    Args:
        data: The list of items to sample from.
        num_samples: The desired number of samples.

    Returns:
        A new list containing the sampled items.
    """
    n = len(data)

    if not isinstance(data, list):
        raise TypeError("Input 'data' must be a list.")
    if not isinstance(num_samples, int):
        raise TypeError("'num_samples' must be an integer.")
    if num_samples < 0:
        raise ValueError("'num_samples' cannot be negative.")

    if num_samples == 0:
        return []
    if n == 0:  # Empty input list
        return []
    if num_samples == 1:
        # For a single sample, pick the middle element
        return [data[n // 2]]
    if num_samples >= n:
        # If asking for more or equal samples than available, return all
        return data[:]

    # For num_samples > 1 and num_samples < n:
    # We want num_samples points, spread across n-1 intervals of indices.
    # The step between ideal sample points is (n - 1) / (num_samples - 1).
    # Indices will be: 0 * step, 1 * step, ..., (num_samples - 1) * step
    sampled_items = []
    for i in range(num_samples):
        # Calculate the ideal floating-point index
        float_idx = i * (n - 1) / (num_samples - 1)
        # Round to the nearest integer index
        idx = int(round(float_idx))
        # Ensure idx is within bounds (should be due to calculation but good for safety)
        # idx = min(n - 1, max(0, idx)) # This line is actually not strictly needed
        # as rounding i * (n-1)/(k-1) for i in [0, k-1]
        # will produce indices in [0, n-1].
        sampled_items.append(data[idx])

    return sampled_items


# --- Start of the pretty_print_markup logic ---

# Pre-compile regexes for efficiency
# 1. Regex for [font=...] opening tags
FONT_OPEN_RE = re.compile(r"\[font=[^\]]+\]")

# 2. Regex for an "innermost" color tag.
# An innermost tag is one whose content does not contain another opening [color=...] tag.
# - (?P<hex>#[0-9A-Fa-f]{6,8}) captures 6 or 8 digit hex codes.
# - (?P<text>(?:(?!\[color=).)*?) captures the text inside.
#   - (?:(?!\[color=).)*? : Matches any character (.) as long as it's not the start
#                             of an opening color tag ([color=), repeated non-greedily.
# - \[/color\] matches the closing tag.
# re.DOTALL allows '.' to match newlines, in case tags/content span lines,
# though problem implies single line.
INNERMOST_COLOR_RE = re.compile(
    r"\[color=(?P<hex>#[0-9A-Fa-f]{6,8})\]"
    r"(?P<text>(?:(?!\[color=).)*?)"
    r"\[/color\]",
    re.DOTALL,  # In case content spans newlines, though problem implies single line
)


def _render_all_colors_iteratively(text_segment: str) -> str:
    """
    Iteratively finds and replaces the innermost color tags first.
    This correctly handles nested [color] tags.
    """
    current_text = text_segment
    while True:
        # Find the first (leftmost) innermost color tag
        match = INNERMOST_COLOR_RE.search(current_text)
        if not match:
            break  # No more innermost color tags found, processing is done.

        hex_code = match.group("hex")
        # The 'text' group contains content already processed by any deeper recursive calls
        # or, if it's truly an innermost tag, plain text (or text with other non-color tags).
        inner_text = match.group("text")

        # Extract RRGGBB from the hex code (last 6 characters)
        rgb_hex = hex_code[-6:]
        r = int(rgb_hex[0:2], 16)
        g = int(rgb_hex[2:4], 16)
        b = int(rgb_hex[4:6], 16)

        # ANSI escape sequence for 24-bit (truecolor) foreground
        ansi_colored_text = f"\033[38;2;{r};{g};{b}m{inner_text}\033[0m"

        # Replace only this one matched innermost tag
        # We use string slicing to replace exactly the matched segment,
        # preserving parts of the string before and after the match.
        # Using re.sub(..., count=1) would also work here.
        start, end = match.span()
        current_text = current_text[:start] + ansi_colored_text + current_text[end:]

    return current_text


def pretty_print_markup(markup: str) -> None:
    """
    Renders a markup string with [font] and [color] tags into a terminal-friendly format.

    - All [font=...]...[/font] wrappers are removed.
    - [color=#RRGGBB]text[/color] or [color=#AARRGGBB]text[/color] becomes ANSI truecolor text.
      The alpha component of 8-digit hex codes is ignored.
    - Nested color tags are handled correctly by processing innermost first.
    - Output is printed on a single line (followed by a newline from print()).
    """

    # --- Step 1: Remove font tags ---
    processed_markup = FONT_OPEN_RE.sub("", markup)
    processed_markup = processed_markup.replace("[/font]", "")

    # --- Step 2: Apply color tags iteratively (innermost first) ---
    rendered_markup = _render_all_colors_iteratively(processed_markup)

    # --- Step 3: Print the result ---
    print(rendered_markup)


# --- End of the pretty_print_markup logic ---


# --- Pytest Test Class ---


class TestPrettyPrintMarkup:
    @pytest.mark.parametrize(
        "markup_input, expected_content",
        [
            (
                # Test case 1: Original example
                "[font=technology-slot-level-font]████▍[color=#00000000]█████0[/color][/font]  43.8%",
                "████▍\033[38;2;0;0;0m█████0\033[0m  43.8%",
            ),
            (
                # Test case 2: Nested colors and multiple tags
                "[font=Arial]Plain [color=#FF0000]Red [color=#00FF00]Green Text[/color] Red Again[/color] Plain Again[/font] And text outside all tags.",
                "Plain \033[38;2;255;0;0mRed \033[38;2;0;255;0mGreen Text\033[0m Red Again\033[0m Plain Again And text outside all tags.",
            ),
            (
                # Test case 3: Multiple font tags and color tags, 6-digit hex
                "[font=Impact][color=#0000FF]Blue Text[/color][/font] then [font=Courier]Monospace Text[/font] and [color=#FFA500]Orange[/color].",
                "\033[38;2;0;0;255mBlue Text\033[0m then Monospace Text and \033[38;2;255;165;0mOrange\033[0m.",
            ),
            (
                # Test case 4: Color tag wrapping a font tag (font tag should be stripped)
                "[color=#FF0000]This is Red [font=ComicSansMS]Font Stripped[/font] still Red[/color]",
                "\033[38;2;255;0;0mThis is Red Font Stripped still Red\033[0m",
            ),
            (
                # Test case 5: Malformed/unclosed tags
                # Unclosed [color] tag isn't processed by INNERMOST_COLOR_RE, [font] opening tag is stripped.
                "[font=UnclosedFont]Text [color=#00FFFF]Cyan text",
                "Text [color=#00FFFF]Cyan text",
            ),
            (
                # Test case 6: Empty color tag
                "[font=Test]Before [color=#123456][/color] After[/font]",
                "Before \033[38;2;18;52;86m\033[0m After",  # Empty text between color and reset
            ),
            (
                # Test case 7: No tags
                "Just plain text.",
                "Just plain text.",
            ),
            (
                # Test case 8: Only font tags
                "[font=Test]Text inside font[/font]",
                "Text inside font",
            ),
            (
                # Test case 9: Only color tags
                "Leading [color=#ABCDEF]Colored[/color] Trailing",
                "Leading \033[38;2;171;205;239mColored\033[0m Trailing",  # #ABCDEF -> R:171 G:205 B:239
            ),
            (
                # Test case 10: Deeply nested colors
                "[color=#FF0000]R [color=#00FF00]G [color=#0000FF]B[/color] G[/color] R[/color]",
                "\033[38;2;255;0;0mR \033[38;2;0;255;0mG \033[38;2;0;0;255mB\033[0m G\033[0m R\033[0m",
            ),
            (
                # Test case 11: Font tags inside color tags (font should still be stripped)
                "[color=#112233]Colored [font=Impact]Stripped Font[/font] still colored[/color]",
                "\033[38;2;17;34;51mColored Stripped Font still colored\033[0m",  # #112233 -> R:17 G:34 B:51
            ),
            (
                # Test case 12: Malformed nesting - stray closing tag
                "[color=#FF0000]Red text with a stray [/color] inside[/color]",
                # The innermost regex will match `[color=#FF0000]Red text with a stray [/color]`.
                # The content `Red text with a stray ` will be colored.
                # The ` inside[/color]` part will be left as is.
                "\033[38;2;255;0;0mRed text with a stray \033[0m inside[/color]",
            ),
            (
                # Test case 13: Malformed - unclosed inner tag
                "[color=#FF0000]Outer [color=#00FF00]Inner unclosed GTAG RTAG",
                # After font removal: "[color=#FF0000]Outer [color=#00FF00]Inner unclosed GTAG RTAG"
                # INNERMOST_COLOR_RE will not find any match because no [/color] exists.
                "[color=#FF0000]Outer [color=#00FF00]Inner unclosed GTAG RTAG",
            ),
        ],
    )
    def test_various_markup_scenarios(
        self, capsys: CaptureFixture[str], markup_input: str, expected_content: str
    ) -> None:
        pretty_print_markup(markup_input)
        captured = capsys.readouterr()
        assert captured.out == expected_content + "\n"

    def test_empty_input(self, capsys: CaptureFixture[str]) -> None:
        pretty_print_markup("")
        captured = capsys.readouterr()
        assert captured.out == "\n"


class TestGeneratePbarConditions:
    def test(self) -> None:
        config = PBarConfig(position=(0, 0), prefix="", length=10)
        conditions = generate_pbar_conditions(config=config)
        sample_conditions = sample_evenly_interpolated(conditions, num_samples=5)
        for sample in sample_conditions:
            pretty_print_markup(sample["text"])
