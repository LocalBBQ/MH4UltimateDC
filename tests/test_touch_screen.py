"""port/src/touch_screen.cpp: mh4u.ini's touch_screen, when the touch overlay's corner shows at
all, for playing on one screen: always (shown, as before), only in quests (map), or only when the
game needs the touch screen (hidden); the touch-screen key's peek, and when the key peeks rather
than switching the quest's map view (in a quest with hidden, the round of presses: the map, the
whole touch screen, hidden)."""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "port", "src")

CXX = next((c for c in ("c++", "clang++", "g++") if shutil.which(c)), None)
pytestmark = pytest.mark.skipif(CXX is None, reason="needs a C++ compiler")

DRIVER = r"""
#include <cstdio>
#include <cstdlib>
#include <string>
#include "touch_screen.h"

using namespace Port::TouchScreen;

// parse VALUE: the mode's name as Parse() reads VALUE
// state mode=M in_quest=0|1 touch_ui=0|1 peek=0|1 editing=0|1 whole=0|1 map=0|1: Hidden(), then
//   PressKey(state, whole, map)'s handled, peek and whole (0 or 1 each), then its note on a line
// peek EVENTS: a Peek through EVENTS, one letter each (t toggle, q a frame in a quest, v a frame
//   out of one); after each, On() and whether Follow() dropped the peek (two digits)
int main(int argc, char** argv) {
    const std::string what = argc > 1 ? argv[1] : "";
    if (what == "parse" && argc == 3) {
        std::printf("%s\n", Name(Parse(argv[2])));
        return 0;
    }
    if (what == "state") {
        State s;
        bool whole = false, map = true;
        for (int i = 2; i < argc; ++i) {
            const std::string arg = argv[i];
            const std::string key = arg.substr(0, arg.find('='));
            const std::string value = arg.substr(arg.find('=') + 1);
            if (key == "mode") s.mode = Parse(value);
            else if (key == "in_quest") s.in_quest = value == "1";
            else if (key == "touch_ui") s.touch_ui = value == "1";
            else if (key == "peek") s.peek = value == "1";
            else if (key == "editing") s.editing = value == "1";
            else if (key == "whole") whole = value == "1";
            else if (key == "map") map = value == "1";
            else return 2;
        }
        const KeyPress press = PressKey(s, whole, map);
        std::printf("%d %d %d %d\n%s\n", Hidden(s) ? 1 : 0, press.handled ? 1 : 0, press.peek ? 1 : 0,
                    press.whole ? 1 : 0, press.note.c_str());
        return 0;
    }
    if (what == "peek" && argc == 3) {
        Peek peek;
        for (const char c : std::string(argv[2])) {
            bool dropped = false;
            if (c == 't') peek.Set(!peek.On());
            else if (c == 'q') dropped = peek.Follow(true);
            else if (c == 'v') dropped = peek.Follow(false);
            else return 2;
            std::printf("%d%d ", peek.On() ? 1 : 0, dropped ? 1 : 0);
        }
        std::printf("\n");
        return 0;
    }
    return 2;
}
"""


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    work = tmp_path_factory.mktemp("touch_screen")
    src = work / "driver.cpp"
    src.write_text(DRIVER)
    exe = work / "driver"
    subprocess.run([CXX, "-std=c++17", "-Wall", "-Werror", "-I", SRC, str(src),
                    os.path.join(SRC, "touch_screen.cpp"), "-o", str(exe)], check=True)
    return exe


def call(driver, *args: str) -> str:
    return subprocess.run([str(driver), *args], capture_output=True, text=True, check=True).stdout.strip()


def run_state(driver, mode, **flags):
    out = call(driver, "state", f"mode={mode}", *(f"{k}={int(v)}" for k, v in flags.items())).split("\n")
    hidden_, handled, peek, whole = (x == "1" for x in out[0].split())
    return hidden_, handled, peek, whole, (out[1].strip() if len(out) > 1 else "")


def hidden(driver, mode, **flags) -> bool:
    return run_state(driver, mode, **flags)[0]


def press(driver, mode, **flags):
    """PressKey: (handled, peek after, whole after, note)."""
    return run_state(driver, mode, **flags)[1:]


@pytest.mark.parametrize("value, name", [
    ("shown", "shown"), ("on", "shown"), ("always", "shown"), ("SHOWN", "shown"),
    ("map", "map"), ("quests", "map"), (" Map ", "map"),
    ("hidden", "hidden"), ("off", "hidden"), ("auto", "hidden"), ("HIDDEN", "hidden"),
    # anything else: the touch overlay as it was before the option
    ("", "shown"), ("sometimes", "shown"), ("1", "shown"),
])
def test_parse(driver, value, name):
    assert call(driver, "parse", value) == name


EVERY_MOMENT = [dict(in_quest=q, touch_ui=u, peek=p, editing=e)
                for q in (0, 1) for u in (0, 1) for p in (0, 1) for e in (0, 1)]


@pytest.mark.parametrize("moment", EVERY_MOMENT)
def test_shown_never_hides_and_leaves_the_key_alone(driver, moment):
    """shown: the touch overlay as before this option, whatever happens."""
    assert not hidden(driver, "shown", **moment)
    assert not press(driver, "shown", **moment)[0]


@pytest.mark.parametrize("mode", ["map", "hidden"])
def test_hidden_outside_quests(driver, mode):
    """In the village, the title menus, cutscenes: nothing in the corner."""
    assert hidden(driver, mode)
    # outside quests the quest HUD's states are stale: a menu state left from the last quest
    # doesn't bring the corner back
    assert hidden(driver, mode, touch_ui=1)


def test_map_shows_in_quests(driver):
    """map: in quests the corner is there (the map, or the whole touch screen, as quest_overlay
    and the key say); hidden: not."""
    assert not hidden(driver, "map", in_quest=1)
    assert hidden(driver, "hidden", in_quest=1)


@pytest.mark.parametrize("mode", ["map", "hidden"])
def test_the_game_needs_the_touch_screen(driver, mode):
    """The quest menu (Customize Panels, Panel Schemes, ...) or a big panel such as the full map:
    the corner comes back for as long as it's up."""
    assert not hidden(driver, mode, in_quest=1, touch_ui=1)


@pytest.mark.parametrize("mode", ["map", "hidden"])
@pytest.mark.parametrize("in_quest", [0, 1])
def test_peek_and_the_layout_editor_show_it(driver, mode, in_quest):
    assert not hidden(driver, mode, in_quest=in_quest, peek=1)
    # the HUD layout editor shows the map and the target camera to place them
    assert not hidden(driver, mode, in_quest=in_quest, editing=1)


SHOW = "Touch screen shown (press the key again to hide it)"
HIDE = "Touch screen hidden"
MAP = "Map shown (press again for the whole touch screen)"
WHOLE = "Whole touch screen shown (press again to hide it)"


@pytest.mark.parametrize("mode", ["map", "hidden"])
@pytest.mark.parametrize("whole", [0, 1])
def test_outside_quests_the_key_toggles_the_peek(driver, mode, whole):
    # the map view's switch is kept as it is
    assert press(driver, mode, whole=whole) == (True, True, bool(whole), SHOW)
    assert press(driver, mode, peek=1, whole=whole) == (True, False, bool(whole), HIDE)


def test_map_in_quests_keeps_the_map_views_switch(driver):
    """map: in quests the key switches the map view (map / whole touch screen) as before."""
    assert not press(driver, "map", in_quest=1)[0]
    assert not press(driver, "map", in_quest=1, map=0)[0]


def test_hidden_in_quests_goes_round(driver):
    """hidden, in a quest whose map can show alone: the map, the whole touch screen, hidden."""
    assert press(driver, "hidden", in_quest=1) == (True, True, False, MAP)
    assert press(driver, "hidden", in_quest=1, peek=1) == (True, True, True, WHOLE)
    assert press(driver, "hidden", in_quest=1, peek=1, whole=1) == (True, False, False, HIDE)
    # hidden with the switch left on the whole touch screen: the round starts again from the map
    assert press(driver, "hidden", in_quest=1, whole=1) == (True, True, False, MAP)


def test_hidden_in_a_quest_without_the_map_view_toggles(driver):
    """No map panel, or quest_overlay off: the peek shows the whole touch screen, so the key just
    shows and hides it."""
    assert press(driver, "hidden", in_quest=1, map=0) == (True, True, False, SHOW)
    assert press(driver, "hidden", in_quest=1, map=0, peek=1) == (True, False, False, HIDE)


def test_peek_toggles(driver):
    assert call(driver, "peek", "tvtv") == "10 10 00 00"


def test_peek_dropped_when_a_quest_starts_or_ends(driver):
    # a peek in the village, then the quest starts: gone, so the hunt starts clean
    assert call(driver, "peek", "tvvq") == "10 10 10 01"
    # a peek in the quest, then it ends
    assert call(driver, "peek", "qtqv") == "00 10 10 01"
    # a change of quest with no peek on drops nothing
    assert call(driver, "peek", "qvq") == "00 00 00"
