#include "touch_screen.h"

#include <algorithm>
#include <cctype>

namespace Port::TouchScreen {

Mode Parse(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return std::tolower(c); });
    value.erase(0, value.find_first_not_of(" \t"));
    value.erase(value.find_last_not_of(" \t") + 1);
    if (value == "map" || value == "quests") {
        return Mode::Map;
    }
    if (value == "hidden" || value == "off" || value == "auto") {
        return Mode::Hidden;
    }
    return Mode::Shown;
}

const char* Name(Mode mode) {
    switch (mode) {
    case Mode::Map:
        return "map";
    case Mode::Hidden:
        return "hidden";
    case Mode::Shown:
        break;
    }
    return "shown";
}

bool Hidden(const State& state) {
    if (state.mode == Mode::Shown || state.editing || state.peek) {
        return false;
    }
    if (state.in_quest && state.touch_ui) {
        return false;  // the quest menu or a big panel: the game needs the touch screen
    }
    return !(state.mode == Mode::Map && state.in_quest);
}

bool Peek::Follow(bool in_quest) {
    if (in_quest == in_quest_) {
        return false;
    }
    in_quest_ = in_quest;
    const bool dropped = on_;
    on_ = false;
    return dropped;
}

KeyPress PressKey(const State& state, bool whole, bool map_can_show) {
    KeyPress press;
    if (state.mode == Mode::Shown || (state.mode == Mode::Map && state.in_quest)) {
        return press;
    }
    press.handled = true;
    if (state.mode == Mode::Hidden && state.in_quest && map_can_show) {
        // round: the map, the whole touch screen, hidden
        if (!state.peek) {
            press = {true, true, false, "Map shown (press again for the whole touch screen)"};
        } else if (!whole) {
            press = {true, true, true, "Whole touch screen shown (press again to hide it)"};
        } else {
            press = {true, false, false, "Touch screen hidden"};
        }
        return press;
    }
    press.peek = !state.peek;
    press.whole = whole;
    press.note = press.peek ? "Touch screen shown (press the key again to hide it)" : "Touch screen hidden";
    return press;
}

} // namespace Port::TouchScreen
